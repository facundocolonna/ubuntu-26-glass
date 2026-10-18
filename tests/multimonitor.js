import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Scripting from 'resource:///org/gnome/shell/ui/scripting.js';

export const METRICS = {};

export async function run() {
    Main.overview.hide();
    await Scripting.sleep(5000);
    if (Main.layoutManager.monitors.length !== 3)
        throw new Error(`Expected three real virtual displays, got ${Main.layoutManager.monitors.length}`);
    for (const uuid of ['dash-to-panel@jderose9.github.com', 'system-monitor-panel@naimur', 'screentospace@dilzhan.dev']) {
        const extension = Main.extensionManager.lookup(uuid);
        if (extension?.state !== 1)
            throw new Error(`${uuid}: state=${extension?.state} error=${extension?.error}`);
    }
    const dtp = Main.extensionManager.lookup('dash-to-panel@jderose9.github.com');
    const settings = dtp.stateObj.getSettings('org.gnome.shell.extensions.dash-to-panel');
    const base = `${GLib.get_user_data_dir()}/gnome-shell/extensions`;
    const load = path => import(Gio.File.new_for_path(`${base}/${path}`).get_uri());
    const {getPanelElementPositions} = await load('dash-to-panel@jderose9.github.com/panelSettings.js');
    const {getInterestingWindows} = await load('dash-to-panel@jderose9.github.com/appIcons.js');
    const {WindowFilter} = await load('screentospace@dilzhan.dev/windowFilter.js');

    function checkPanels(expected) {
        const panels = global.dashToPanel.panels;
        if (panels.length !== expected)
            throw new Error(`Expected ${expected} bars, got ${panels.length}`);
        for (const panel of panels) {
            const layout = getPanelElementPositions(settings, panel.monitor.index);
            if (layout.find(e => e.element === 'taskbar')?.position !== 'centerMonitor' ||
                layout.find(e => e.element === 'showAppsButton')?.visible !== false)
                throw new Error(`Wrong inherited layout on monitor ${panel.monitor.index}`);
            const indicator = panel.panel.statusArea['system-monitor-panel@naimur'];
            if (!indicator || panel.panel._leftBox.get_first_child() !== indicator.container)
                throw new Error(`Missing left CPU/RAM on monitor ${panel.monitor.index}`);
            for (const [name, box] of indicator._panelBoxes) {
                if (box.container.visible !== ['cpu', 'memory'].includes(name))
                    throw new Error(`Unexpected metric ${name} on monitor ${panel.monitor.index}`);
            }
            if (!/^\d+(\.\d+)?%$/.test(indicator._cpuBox.label.text) ||
                !/^\d+(\.\d+)?%$/.test(indicator._memBox.label.text))
                throw new Error(`No CPU/RAM readings on monitor ${panel.monitor.index}`);
            const [x] = indicator.container.get_transformed_position();
            if (Math.abs(x - panel.monitor.x) > 90)
                throw new Error(`CPU/RAM offset on monitor ${panel.monitor.index}: ${x}`);
        }
    }
    checkPanels(3);
    print('MULTIMONITOR_PASS centered_apps=true app_grid_button=false cpu_ram=3_panels');

    const normalWindows = () => global.get_window_actors().map(a => a.meta_window).filter(w => w.get_window_type() === 0);
    const before = new Set(normalWindows());
    await Scripting.createTestWindow({width: 400, height: 300});
    await Scripting.waitTestWindows();
    await Scripting.sleep(400);
    const desktop = normalWindows().find(w => !before.has(w));
    if (!desktop)
        throw new Error('Missing regression-test window');
    // DING attaches this marker to its desktop surfaces on Wayland.
    desktop.customJS_ding = {_hideFromWindowList: true, _keepAtBottom: true};
    const sts = Main.extensionManager.lookup('screentospace@dilzhan.dev').stateObj;
    const filter = new WindowFilter(sts.getSettings());
    if (getInterestingWindows(null).includes(desktop) || filter.isManagedWindow(desktop))
        throw new Error('Desktop surface appears as an application or is managed by ScreenToSpace');
    delete desktop.customJS_ding;
    if (!getInterestingWindows(null).includes(desktop) || !filter.isManagedWindow(desktop))
        throw new Error('Normal application is incorrectly hidden');
    desktop.delete(global.get_current_time());
    await Scripting.sleep(600);
    print('DESKTOP_SURFACE_PASS hidden_from_taskbar=true ignored_by_workspace_isolation=true normal_windows_visible=true');

    // Monitor changes rebuild panels through the same manager reset path.
    settings.set_boolean('multi-monitors', false);
    await Scripting.sleep(2500);
    checkPanels(1);
    settings.set_boolean('multi-monitors', true);
    await Scripting.sleep(3500);
    checkPanels(3);
    print('PANEL_REBUILD_PASS 3_to_1_to_3 no_duplicate_indicators=true');
    for (const uuid of [...Main.extensionManager._extensionOrder].reverse())
        await Main.extensionManager._callExtensionDisable(uuid);
    await Scripting.sleep(300);
}
