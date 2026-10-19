// SPDX-License-Identifier: GPL-3.0-or-later
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PointerWatcher from 'resource:///org/gnome/shell/ui/pointerWatcher.js';

const MAX_FRAME = 1024 * 1024;

function connect(client, address, cancel) {
    return new Promise((resolve, reject) => client.connect_async(address, cancel, (o, r) => {
        try { resolve(o.connect_finish(r)); } catch (e) { reject(e); }
    }));
}

function read(stream, cancel) {
    return new Promise((resolve, reject) => stream.read_bytes_async(4096,
        GLib.PRIORITY_DEFAULT, cancel, (o, r) => {
            try { resolve(o.read_bytes_finish(r).get_data()); } catch (e) { reject(e); }
        }));
}

function write(stream, bytes, cancel) {
    return new Promise((resolve, reject) => stream.write_all_async(bytes,
        GLib.PRIORITY_DEFAULT, cancel, (o, r) => {
            try { resolve(o.write_all_finish(r)); } catch (e) { reject(e); }
        }));
}

export default class CursorEdgeFix extends Extension {
    enable() {
        this._enabled = true;
        this._running = false;
        this._inhibited = false;
        this._connecting = false;
        this._tracker = global.backend.get_cursor_tracker();
        this._seat = global.stage.get_context().get_backend().get_default_seat();
        this._clip = new St.Widget({reactive: false, visible: false,
            clip_to_allocation: true, name: 'littlebigmouse-cursor-clip'});
        this._sprite = new Clutter.Actor({reactive: false});
        this._clip.add_child(this._sprite);
        global.stage.add_child(this._clip);
        this._cursorSignal = this._tracker.connect('cursor-changed', () => this._refreshSprite());
        this._prefsSignal = this._tracker.connect('cursor-prefs-changed', () => this._refreshSprite());
        this._sessionSignal = Main.sessionMode.connect('updated', () => this._sync());
        this._monitorsSignal = Main.layoutManager.connect('monitors-changed', () => this._sync());
        this._refreshSprite();
        this._retry = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, () => {
            this._connectDaemon();
            return GLib.SOURCE_CONTINUE;
        });
        this._connectDaemon();
    }

    _refreshSprite() {
        this._texture = this._tracker.get_sprite();
        if (this._texture) {
            this._sprite.content = Clutter.TextureContent.new_from_texture(this._texture, null);
            const scale = this._tracker.get_scale() || 1;
            this._width = this._texture.get_width() / scale;
            this._height = this._texture.get_height() / scale;
            this._sprite.set_size(this._width, this._height);
            [this._hotX, this._hotY] = this._tracker.get_hot();
        }
        this._sync();
    }

    _setRunning(running) {
        if (!this._enabled)
            return;
        this._running = running;
        if (running && !this._watch)
            this._watch = PointerWatcher.getPointerWatcher().addWatch(16, () => this._sync());
        if (!running && this._watch) {
            this._watch.remove();
            this._watch = null;
        }
        this._sync();
    }

    _sync() {
        if (!this._clip)
            return;
        const [x, y] = global.get_pointer();
        const monitor = Main.layoutManager.monitors.find(m =>
            x >= m.x && x < m.x + m.width && y >= m.y && y < m.y + m.height);
        const left = x - (this._hotX || 0);
        const top = y - (this._hotY || 0);
        const spills = monitor && (left < monitor.x || top < monitor.y ||
            left + this._width > monitor.x + monitor.width ||
            top + this._height > monitor.y + monitor.height);
        const magnified = Main.magnifier?.isActive() ?? false;
        if (this._running && this._texture && spills && !Main.sessionMode.isLocked &&
            !Main.sessionMode.isGreeter && !magnified &&
            (this._inhibited || this._tracker.get_pointer_visible())) {
            this._clip.set_position(monitor.x, monitor.y);
            this._clip.set_size(monitor.width, monitor.height);
            this._sprite.set_position(left - monitor.x, top - monitor.y);
            this._clip.show();
            if (!this._inhibited) {
                this._seat.inhibit_unfocus();
                this._tracker.inhibit_cursor_visibility();
                this._inhibited = true;
            }
        } else {
            this._release();
        }
    }

    _release() {
        this._clip?.hide();
        if (this._inhibited) {
            this._tracker.uninhibit_cursor_visibility();
            this._seat.uninhibit_unfocus();
            this._inhibited = false;
        }
    }

    async _connectDaemon() {
        if (!this._enabled || this._connecting)
            return;
        this._connecting = true;
        const cancel = new Gio.Cancellable();
        this._cancel = cancel;
        let connection;
        try {
            const endpoint = GLib.getenv('LBM_HOOK_ENDPOINT') ||
                GLib.build_filenamev([GLib.get_user_runtime_dir(), 'littlebigmouse-v1.sock']);
            const client = new Gio.SocketClient();
            client.timeout = 2;
            connection = await connect(client, new Gio.UnixSocketAddress({path: endpoint}), cancel);
            // Only connect has a timeout; an idle event stream must stay connected.
            connection.get_socket().set_timeout(0);
            this._connection = connection;
            const payload = new TextEncoder().encode('<CommandMessage Command="Listen"/>');
            const frame = new Uint8Array(4 + payload.length);
            new DataView(frame.buffer).setUint32(0, payload.length, true);
            frame.set(payload, 4);
            await write(connection.get_output_stream(), frame, cancel);
            let buffer = new Uint8Array();
            while (this._enabled && !cancel.is_cancelled()) {
                const chunk = await read(connection.get_input_stream(), cancel);
                if (!chunk.length)
                    break;
                const combined = new Uint8Array(buffer.length + chunk.length);
                combined.set(buffer);
                combined.set(chunk, buffer.length);
                buffer = combined;
                while (buffer.length >= 4) {
                    const length = new DataView(buffer.buffer, buffer.byteOffset, 4).getUint32(0, true);
                    if (length > MAX_FRAME)
                        throw new Error('Invalid LittleBigMouse IPC frame');
                    if (buffer.length < length + 4)
                        break;
                    const message = new TextDecoder().decode(buffer.subarray(4, length + 4));
                    const event = /<Event>([^<]+)<\/Event>/.exec(message)?.[1];
                    if (event === 'Running')
                        this._setRunning(true);
                    else if (['Stopped', 'Paused', 'Suspended', 'Dead', 'Rescued'].includes(event))
                        this._setRunning(false);
                    buffer = buffer.slice(length + 4);
                }
            }
        } catch (_) {
            // The daemon may be closed or restarting. Restore the system cursor
            // immediately; the retry timer reconnects without starting the engine.
        } finally {
            try { connection?.close(null); } catch (_) { /* Already closed. */ }
            if (this._cancel === cancel) {
                this._connection = null;
                this._connecting = false;
                this._setRunning(false);
            }
        }
    }

    disable() {
        this._enabled = false;
        if (this._retry)
            GLib.source_remove(this._retry);
        this._retry = null;
        this._cancel?.cancel();
        this._watch?.remove();
        this._watch = null;
        this._release();
        this._tracker.disconnect(this._cursorSignal);
        this._tracker.disconnect(this._prefsSignal);
        Main.sessionMode.disconnect(this._sessionSignal);
        Main.layoutManager.disconnect(this._monitorsSignal);
        this._clip.destroy();
        this._clip = null;
        this._sprite = null;
        this._texture = null;
    }
}
