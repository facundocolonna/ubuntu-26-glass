import Gio from 'gi://Gio';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Scripting from 'resource:///org/gnome/shell/ui/scripting.js';

export const METRICS = {};

export async function run() {
    Main.overview.hide();
    await Scripting.sleep(5000);
    const uuids = ['dash-to-panel@jderose9.github.com', 'blur-my-shell@aunetx',
        'rounded-window-corners@fxgn', 'system-monitor-panel@naimur'];
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
    // Release actors explicitly before the test compositor shuts down.
    for (const uuid of [...Main.extensionManager._extensionOrder].reverse()) {
        if (uuids.includes(uuid))
            await Main.extensionManager._callExtensionDisable(uuid);
    }
    await Scripting.sleep(300);
}
