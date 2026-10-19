import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Scripting from 'resource:///org/gnome/shell/ui/scripting.js';

export const METRICS = {};

export async function run() {
    Main.overview.hide();
    await Scripting.sleep(2000);
    const base = `${GLib.get_user_data_dir()}/gnome-shell/extensions`;
    const {FocusSlider} = await import(Gio.File.new_for_path(
        `${base}/dash-to-panel@jderose9.github.com/focusSlider.js`).get_uri());
    const app = {};
    const tracker = {focus_app: app, connect: () => 1, disconnect: () => {}};
    const panel = new St.Widget({x: 100, y: 200, width: 600, height: 56,
        layout_manager: new Clutter.FixedLayout()});
    panel.panel = new St.Bin({width: 600, height: 56});
    panel.add_child(panel.panel);
    Main.uiGroup.add_child(panel);
    const row = new St.BoxLayout({x_align: Clutter.ActorAlign.CENTER,
        y_align: Clutter.ActorAlign.CENTER});
    panel.panel.child = row;
    const icons = [0, 1, 2].map(() => {
        const wrapper = new St.Bin({width: 56, height: 44});
        const actor = new St.Widget({width: 44, height: 44,
            x_align: Clutter.ActorAlign.CENTER, y_align: Clutter.ActorAlign.CENTER});
        wrapper.child = actor;
        row.add_child(wrapper);
        return {dtpPanel: panel, _dotsContainer: actor, app,
            _checkIfMonitorHasFocus: () => true, wrapper};
    });
    const slider = new FocusSlider(panel, tracker);
    await Scripting.sleep(250);
    const select = icon => slider.select(icon, 'rgba(238,238,238,0.25)');
    const assert = (condition, message) => {if (!condition) throw new Error(message);};
    const aligned = icon => {
        const [sx, sy] = slider.actor.get_transformed_position();
        const [tx, ty] = icon._dotsContainer.get_transformed_position();
        assert(slider.actor.opacity === 255 && Math.abs(sx - tx) < 0.5 && Math.abs(sy - ty) < 0.5,
            `Highlight detached: selector=${sx},${sy}; target=${tx},${ty}`);
    };
    select(icons[0]);
    await Scripting.sleep(100);
    aligned(icons[0]);
    const start = slider.actor.translation_x;
    select(icons[2]);
    let intermediate = false;
    for (let elapsed = 0; elapsed < 300; elapsed += 15) {
        await Scripting.sleep(15);
        if (slider.actor.translation_x > start && slider.actor.translation_x < start + 112) {
            intermediate = true;
            break;
        }
    }
    assert(intermediate, `Focus transition no longer animates: start=${start}; current=${slider.actor.translation_x}; expected=${icons[2]._dotsContainer.get_transformed_position()[0] - slider.layer.get_transformed_position()[0]}`);
    await Scripting.sleep(250);
    aligned(icons[2]);
    const localBefore = icons[2]._dotsContainer.get_allocation_box();
    const globalBefore = icons[2]._dotsContainer.get_transformed_position()[0];
    icons[0].wrapper.destroy();
    await Scripting.sleep(300);
    const localAfter = icons[2]._dotsContainer.get_allocation_box();
    assert(localBefore.x1 === localAfter.x1 && localBefore.y1 === localAfter.y1,
        'Fixture must leave the focused icon local allocation unchanged');
    assert(globalBefore !== icons[2]._dotsContainer.get_transformed_position()[0],
        'Fixture must recenter the group after a sibling closes');
    aligned(icons[2]);
    row.translation_x = 19;
    await Scripting.sleep(100);
    aligned(icons[2]);
    const replacement = new St.BoxLayout({x_align: Clutter.ActorAlign.CENTER,
        y_align: Clutter.ActorAlign.CENTER});
    row.remove_child(icons[2].wrapper);
    panel.panel.child = replacement;
    replacement.add_child(icons[2].wrapper);
    row.destroy();
    await Scripting.sleep(300);
    aligned(icons[2]);
    replacement.translation_x = -13;
    await Scripting.sleep(100);
    aligned(icons[2]);
    tracker.focus_app = null;
    slider.queueUpdate();
    await Scripting.sleep(100);
    assert(slider.actor.opacity === 0, 'Highlight survives losing application focus');
    assert(!slider.actor.reactive, 'Highlight intercepts mouse clicks');
    tracker.focus_app = app;
    select(icons[2]);
    await Scripting.sleep(100);
    aligned(icons[2]);
    icons[2].wrapper.destroy();
    await Scripting.sleep(100);
    assert(slider.actor.opacity === 0, 'Highlight survives closing the focused icon');
    slider.destroy();
    replacement.translation_x = 7;
    await Scripting.sleep(100);
    assert(slider.pending === 0, 'Destroyed highlight still receives layout updates');
    panel.destroy();
    print('FOCUS_SLIDER_PASS animated_focus; sibling_close_recenter; ancestor_translation; reparent; focus_loss; cleanup');
}
