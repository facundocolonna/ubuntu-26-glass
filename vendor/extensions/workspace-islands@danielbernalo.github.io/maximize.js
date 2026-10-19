// SPDX-License-Identifier: GPL-2.0-or-later
// ScreenToSpace behavior for secondary monitors' virtual workspaces.
import Meta from 'gi://Meta';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { placementIndex } from './placement.js';

const ORIGIN = Symbol.for('gnome-glass.virtual-maximize-origin');

export class VirtualMaximizer {
    constructor(registry, commit) {
        this._registry = registry;
        this._commit = commit;
        this._signals = new Map();
        this._pending = new Map();
        // The compositor's completed size-change path also covers clients
        // whose maximize properties settle before our window adoption hook.
        this._sizeChange = global.window_manager.connect('size-changed', (_wm, actor) => {
            const window = actor.meta_window;
            if (window && this._registry.forWindow(window) && window.get_window_type() === Meta.WindowType.NORMAL) {
                this.track(window);
                this._schedule(window);
            }
        });
    }

    track(window) {
        if (this._signals.has(window) || window.get_window_type() !== Meta.WindowType.NORMAL)
            return;
        this._signals.set(window, [
            window.connect('notify::maximized-horizontally', () => this._schedule(window)),
            window.connect('notify::maximized-vertically', () => this._schedule(window)),
            window.connect('notify::fullscreen', () => this._schedule(window)),
        ]);
    }

    _schedule(window) {
        const pending = this._pending.get(window);
        if (pending)
            GLib.Source.remove(pending);
        this._pending.set(window, GLib.timeout_add(GLib.PRIORITY_DEFAULT, 150, () => {
            this._pending.delete(window);
            this._changed(window);
            return GLib.SOURCE_REMOVE;
        }));
    }

    _changed(window) {
        const state = this._registry.forWindow(window);
        if (!state || window.is_fullscreen())
            return;
        const maximized = window.maximized_horizontally && window.maximized_vertically;
        const origin = window[ORIGIN];
        if (!maximized && origin) {
            delete window[ORIGIN];
            if (origin.connector !== state.connector)
                return;
            const target = this._homeIndex(state, origin);
            this._skipEffect(window);
            state.moveWindowTo(window, target);
            this._commit(state, target);
        } else if (maximized && !origin) {
            const settings = Main.extensionManager.lookup('screentospace@dilzhan.dev')?.stateObj?._settings;
            if (!settings?.get_boolean('trigger-on-maximize'))
                return;
            const from = state.indexOf(window);
            if (from < 0 || from !== state.activeIndex)
                return;
            const peers = state.windowsOn(from).filter(w => w !== window &&
                w.get_window_type() === Meta.WindowType.NORMAL);
            if (!peers.length)
                return;
            const target = Array.from({length: state.size}, (_, i) => i)
                .find(i => i !== from && state.windowsOn(i).length === 0);
            if (target === undefined)
                return;
            window[ORIGIN] = {connector: state.connector, peer: peers[0], index: from};
            this._skipEffect(window);
            state.moveWindowTo(window, target);
            this._commit(state, state.indexOf(window));
        }
    }

    _homeIndex(state, origin) {
        const peerIndex = state.indexOf(origin.peer);
        return peerIndex >= 0 ? peerIndex : Math.min(origin.index, state.size - 1);
    }

    _skipEffect(window) {
        const actor = window.get_compositor_private();
        if (actor)
            Main.wm.skipNextEffect(actor);
    }

    closing(window) {
        const origin = window[ORIGIN];
        // An unmanaged window may already report monitor -1. Its origin note
        // still identifies the secondary monitor whose workspace must return.
        const state = origin ? this._registry.forConnector(origin.connector) :
            this._registry.forWindow(window);
        // window-left-monitor may already have untracked a closing window.
        // Its placement note survives that signal and still identifies its space.
        const lastIndex = state ? Math.max(state.indexOf(window), placementIndex(window, state.connector)) : -1;
        const follow = state && lastIndex === state.activeIndex;
        delete window[ORIGIN];
        if (state && origin && origin.connector === state.connector && follow) {
            state.untrack(window);
            this._commit(state, this._homeIndex(state, origin));
        }
        this._disconnect(window);
    }

    _disconnect(window) {
        const pending = this._pending.get(window);
        if (pending) {
            GLib.Source.remove(pending);
            this._pending.delete(window);
        }
        for (const id of this._signals.get(window) ?? [])
            window.disconnect(id);
        this._signals.delete(window);
    }

    destroy() {
        global.window_manager.disconnect(this._sizeChange);
        for (const window of [...this._signals.keys()])
            this._disconnect(window);
    }
}
