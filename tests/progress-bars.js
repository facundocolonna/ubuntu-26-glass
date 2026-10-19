import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Scripting from 'resource:///org/gnome/shell/ui/scripting.js';

export const METRICS = {};
export async function run() {
    Main.overview.hide();
    const path = `${GLib.get_user_data_dir()}/gnome-shell/extensions/system-monitor-panel@naimur/progressBar.js`;
    const {setBarWidth} = await import(Gio.File.new_for_path(path).get_uri());
    const host = new St.Bin({x: 100, y: 150, width: 530, height: 32});
    const track = new St.BoxLayout({style: 'min-width: 220px; height: 7px;',
        x_expand: true, y_align: Clutter.ActorAlign.CENTER});
    const fill = new St.Widget({style: 'height: 7px; background-color: #c061cb;'});
    track.add_child(fill);
    host.child = track;
    Main.uiGroup.add_child(host);
    setBarWidth(fill, 53.9, 220);
    await Scripting.sleep(250);
    function check(percent, name) {
        const box = track.get_theme_node().get_content_box(track.get_allocation_box());
        const width = box.x2 - box.x1;
        const expected = width * percent / 100;
        if (Math.abs(fill.width - expected) > 1)
            throw new Error(`${name}: fill=${fill.width}, track=${width}, expected=${expected}`);
    }
    check(53.9, 'Stretched RAM card');
    setBarWidth(fill, 8, 220);
    await Scripting.sleep(100);
    check(8, 'Swap remains independent');
    for (const percent of [0, 50, 100]) {
        setBarWidth(fill, percent, 220);
        await Scripting.sleep(100);
        check(percent, `Boundary ${percent}%`);
    }
    host.width = 320;
    await Scripting.sleep(200);
    if (track.width > 320)
        throw new Error('A full bar prevents its track from shrinking');
    check(100, 'Resize from a full wide bar');
    host.width = 1060;
    setBarWidth(fill, 53.9, 220);
    await Scripting.sleep(200);
    check(53.9, 'Wide track');
    track.set_style('min-width: 220px; height: 7px; padding: 0 12px; border: 1px solid white;');
    await Scripting.sleep(200);
    check(53.9, 'Content width excludes padding and border');
    host.hide();
    host.width = 430;
    setBarWidth(fill, 75, 220);
    host.show();
    await Scripting.sleep(200);
    check(75, 'Menu reopened after resizing');
    fill.destroy();
    host.width = 600;
    await Scripting.sleep(100);
    host.destroy();
    for (const uuid of [...Main.extensionManager._extensionOrder].reverse())
        await Main.extensionManager._callExtensionDisable(uuid);
    print('PROGRESS_BARS_PASS proportional_ram; independent_swap; boundaries; resize; padding; reopen; cleanup');
}
