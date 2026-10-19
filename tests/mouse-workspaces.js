import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Scripting from 'resource:///org/gnome/shell/ui/scripting.js';
export const METRICS = {};
export async function run() {
    await Scripting.sleep(4500);
    Main.overview.hide();
    await Scripting.sleep(500);
    const ext = Main.extensionManager.lookup('workspace-islands@danielbernalo.github.io');
    if (ext.state !== 1) throw new Error(`Islands: ${ext.state} ${ext.error}`);
    const islands = ext.stateObj;
    const monitors = Main.layoutManager.monitors;
    print('MONITORS '+JSON.stringify(monitors));
    const primary = Main.layoutManager.primaryIndex;
    if (monitors.length !== 3) throw new Error('Expected 3 monitors');
    const secondary = monitors.filter(m => m.index !== primary);
    const seat = global.stage.get_context().get_backend().get_default_seat();
    const keyboard = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
    // Supply the OS pointer position in the isolated input-less compositor.
    // Real virtual key events below still exercise Mutter's global shortcuts.
    const getPointer = global.get_pointer.bind(global);
    async function pointer(index) {
        const m = monitors[index];
        global.get_pointer = () => [m.x + m.width/2, m.y + m.height/2, 0];
        await Scripting.sleep(50);
    }
    async function press(key) {
        const keys=[Clutter.KEY_Super_L,Clutter.KEY_Control_L,Clutter.KEY_Alt_L,
            key>0?Clutter.KEY_Page_Down:Clutter.KEY_Page_Up];
        for(const k of keys) keyboard.notify_keyval(GLib.get_monotonic_time(),k,Clutter.KeyState.PRESSED);
        for(const k of [...keys].reverse()) keyboard.notify_keyval(GLib.get_monotonic_time(),k,Clutter.KeyState.RELEASED);
        await Scripting.sleep(900);
        print(`WORKSPACE_DIRECTION delta=${key} primary=${primary} mode=${Main.actionMode}`);
    }
    const processes = new Map();
    async function create(index) {
        const before = new Set(global.get_window_actors().map(a => a.meta_window));
        const code = `import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk,Gio,GLib
import signal
app=Gtk.Application(application_id='org.gnome.GlassMouseTest',flags=Gio.ApplicationFlags.NON_UNIQUE)
def activate(app):
    window=Gtk.ApplicationWindow(application=app,title='Glass Mouse Test',default_width=400,default_height=240)
    window.present()
app.connect('activate',activate)
def quit_app(*args):
    print('APP_QUIT',flush=True)
    app.quit()
    return False
GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGUSR1,quit_app)
app.run(None)`;
        const process = Gio.Subprocess.new(['/usr/bin/python3','-c',code],Gio.SubprocessFlags.NONE);
        let w;
        for (let i=0;i<30;i++) {
            await Scripting.sleep(100);
            w = global.get_window_actors().map(a => a.meta_window).find(w => !before.has(w));
            if(w) break;
        }
        if (!w) throw new Error('GTK test window did not open');
        processes.set(w,process);
        w.move_to_monitor(index);
        const m=monitors[index];
        w.move_resize_frame(false, m.x+150, m.y+150, 400, 240);
        await Scripting.sleep(350);
        return w;
    }
    const a = await create(primary);
    const b = await create(secondary[0].index);
    const c = await create(secondary[1].index);
    a.activate(global.get_current_time());
    await Scripting.sleep(250);
    const native = global.workspace_manager.get_active_workspace();
    const s1 = islands._registry.forMonitorIndex(secondary[0].index);
    const s2 = islands._registry.forMonitorIndex(secondary[1].index);
    if (!s1.allWindows.includes(b) || !s2.allWindows.includes(c))
        throw new Error('Secondary windows not tracked');
    await pointer(secondary[0].index);
    await press(1);
    if (s1.activeIndex !== 1 || s2.activeIndex !== 0 || !b.minimized || c.minimized || a.minimized ||
        global.workspace_manager.get_active_workspace() !== native)
        throw new Error(`Not independent: s1=${s1.activeIndex} s2=${s2.activeIndex} b=${b.minimized} c=${c.minimized}`);
    const d = await create(secondary[0].index);
    if (d.minimized || s1.indexOf(d) !== s1.activeIndex)
        throw new Error('New window did not open on current virtual workspace');
    await pointer(secondary[0].index);
    await press(-1);
    if (s1.activeIndex !== 0 || b.minimized || !d.minimized || c.minimized)
        throw new Error('Previous button failed');
    await pointer(secondary[1].index);
    await press(1);
    if (s2.activeIndex !== 1 || s1.activeIndex !== 0 || !c.minimized || b.minimized)
        throw new Error('Third monitor was not independent');
    await pointer(primary);
    await press(1);
    if (global.workspace_manager.get_active_workspace() === native || s1.activeIndex !== 0 || s2.activeIndex !== 1 || b.minimized || !c.minimized)
        throw new Error('Primary switch disturbed secondary workspaces');
    await press(-1);
    print('MOUSE_WORKSPACES_PASS pointer_target=true three_independent=true native_primary=true new_windows=current');
    const e = await create(secondary[0].index);
    const home = s1.activeIndex;
    if (b.maximized_horizontally || b.maximized_vertically)
        throw new Error('Maximize fixture was already maximized');
    b.maximize();
    await Scripting.sleep(900);
    if (s1.activeIndex === home || s1.indexOf(b) !== s1.activeIndex || !e.minimized || b.minimized)
        throw new Error(`Secondary maximize did not isolate: active=${s1.activeIndex} home=${home} bindex=${s1.indexOf(b)} monitor=${b.get_monitor()} max=${b.maximized_horizontally},${b.maximized_vertically} bmin=${b.minimized} emin=${e.minimized}`);
    b.unmaximize();
    await Scripting.sleep(900);
    if (s1.activeIndex !== s1.indexOf(e) || b.minimized || e.minimized)
        throw new Error('Secondary restore did not return home');
    b.maximize();
    await Scripting.sleep(500);
    print(`CLOSE_TEST windowPid=${b.get_pid()} processPid=${processes.get(b).get_identifier()}`);
    processes.get(b).send_signal(10);
    await new Promise((resolve, reject) => processes.get(b).wait_async(null, (proc, result) => {
        try {proc.wait_finish(result);resolve();} catch(error){reject(error);}
    }));
    await Scripting.sleep(900);
    if (s1.activeIndex !== s1.indexOf(e) || e.minimized)
        throw new Error(`Closing isolated secondary window did not return home: active=${s1.activeIndex} peer=${s1.indexOf(e)} min=${e.minimized}`);
    print('SECONDARY_MAXIMIZE_PASS maximize=isolate restore=return close=return');
    const manual = await create(secondary[0].index);
    manual.minimize();
    await Scripting.sleep(200);
    await pointer(secondary[0].index);
    await press(1);
    await press(-1);
    if (!manual.minimized)
        throw new Error('Switching restored a manually minimized window');
    global.get_pointer = getPointer;
    await Main.extensionManager._callExtensionDisable(ext.uuid);
    if (e.minimized || c.minimized || d.minimized)
        throw new Error('Disabling left hidden windows behind');
    if (!manual.minimized)
        throw new Error('Disable restored a manually minimized window');
    print('WORKSPACE_CLEANUP_PASS hidden_windows_restored=true manual_minimization=preserved');
    for (const w of [a,c,d,e,manual]) processes.get(w).send_signal(10);
    await Scripting.sleep(500);
    for (const uuid of [...Main.extensionManager._extensionOrder].reverse())
        await Main.extensionManager._callExtensionDisable(uuid);
    await Scripting.sleep(200);
}
