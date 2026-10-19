import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Scripting from 'resource:///org/gnome/shell/ui/scripting.js';

export const METRICS = {};

export async function run() {
    Main.overview.hide();
    await Scripting.sleep(5000);
    const uuids = ['dash-to-panel@jderose9.github.com', 'blur-my-shell@aunetx',
        'rounded-window-corners@fxgn', 'system-monitor-panel@naimur',
        'screentospace@dilzhan.dev', 'workspace-islands@danielbernalo.github.io'];
    for (const uuid of uuids) {
        const extension = Main.extensionManager.lookup(uuid);
        if (extension?.state !== 1)
            throw new Error(`${uuid}: state=${extension?.state}, error=${extension?.error}`);
    }
    const monitor = Main.panel.statusArea['system-monitor-panel@naimur'];
    for (const [name, box] of monitor._panelBoxes) {
        const visible = ['cpu', 'memory'].includes(name);
        if (box.container.visible !== visible)
            throw new Error(`Wrong metric visibility: ${name}`);
        if (visible && !/^\d+(\.\d+)?%$/.test(box.label.text))
            throw new Error(`Invalid metric: ${name}=${box.label.text}`);
    }
    if (Main.panel._leftBox.get_first_child() !== monitor.container)
        throw new Error('CPU/RAM is not first on the left');
    const [x, y] = monitor.container.get_transformed_position();
    if (x < 0 || x > 100 || y < 600)
        throw new Error(`CPU/RAM is not in the bottom left: ${x},${y}`);
    const blur = Main.extensionManager.lookup('blur-my-shell@aunetx').stateObj;
    if (!blur.getSettings().get_boolean('rounded-blur-found'))
        throw new Error('Native rounded blur was not detected');
    const activities = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
    if (!activities.get_boolean('enable-hot-corners'))
        throw new Error('Hot corner not enabled');
    print(`GNOME_GLASS_HEADLESS_PASS all_extensions=active native_blur=true cpu=${monitor._cpuBox.label.text} ram=${monitor._memBox.label.text} left=${x},${y}`);
    const source = Gio.File.new_for_path(`${GLib.get_user_data_dir()}/gnome-shell/extensions/dash-to-panel@jderose9.github.com/appIcons.js`);
    const {getInterestingWindows} = await import(source.get_uri());
    const normalWindows = () => global.get_window_actors().map(a => a.meta_window)
        .filter(w => w.get_window_type() === 0);
    async function createWindow() {
        const before = new Set(normalWindows());
        await Scripting.createTestWindow({width: 450, height: 300});
        await Scripting.waitTestWindows();
        await Scripting.sleep(500);
        const window = normalWindows().find(w => !before.has(w));
        if (!window)
            throw new Error('Could not create a test window');
        return window;
    }
    const anchor = await createWindow();
    const window = await createWindow();
    const home = window.get_workspace();
    if (anchor.get_workspace() !== home)
        throw new Error('Test windows do not share their home workspace');
    window.maximize();
    await Scripting.sleep(1400);
    const isolated = window.get_workspace();
    if (isolated === home || anchor.get_workspace() !== home)
        throw new Error('Maximizing did not isolate the window while preserving the home desktop');
    if (global.workspace_manager.get_active_workspace() !== isolated)
        throw new Error('The isolated workspace did not activate');
    if (![anchor, window].every(w => getInterestingWindows(null).includes(w)))
        throw new Error('The taskbar does not include windows from both workspaces');
    window.unmaximize();
    await Scripting.sleep(1400);
    if (window.get_workspace() !== home || global.workspace_manager.get_active_workspace() !== home)
        throw new Error('Unmaximizing did not return to the original workspace');
    window.make_fullscreen();
    await Scripting.sleep(900);
    if (window.get_workspace() !== home)
        throw new Error('Fullscreen triggered isolation despite being disabled');
    window.unmake_fullscreen();
    await Scripting.sleep(900);
    window.maximize();
    await Scripting.sleep(1400);
    if (window.get_workspace() === home)
        throw new Error('Second maximize did not isolate the window');
    window.delete(global.get_current_time());
    await Scripting.sleep(1400);
    if (global.workspace_manager.get_active_workspace() !== home)
        throw new Error('Closing the isolated window did not return to the home workspace');
    print('SCREENTOSPACE_PASS maximize=isolate unmaximize=return close=return fullscreen=unchanged taskbar=all_workspaces');
    anchor.delete(global.get_current_time());
    await Scripting.sleep(900);
    // Release actors explicitly before the test compositor shuts down.
    for (const uuid of [...Main.extensionManager._extensionOrder].reverse()) {
        if (uuids.includes(uuid))
            await Main.extensionManager._callExtensionDisable(uuid);
    }
    await Scripting.sleep(300);
}
