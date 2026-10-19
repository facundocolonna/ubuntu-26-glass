import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';
import St from 'gi://St';

const sliders = new WeakMap();

export function moveFocusHighlight(icon, color) {
    const panel = icon.dtpPanel;
    let slider = sliders.get(panel);
    if (!slider) {
        slider = new FocusSlider(panel);
        sliders.set(panel, slider);
    }
    slider.select(icon, color);
}

export function destroyFocusHighlight(panel) {
    const slider = sliders.get(panel);
    if (!slider)
        return;
    sliders.delete(panel);
    slider.destroy();
}

export class FocusSlider {
    constructor(panel, tracker = Shell.WindowTracker.get_default()) {
        this.panel = panel;
        this.target = null;
        this.pending = 0;
        this.ready = false;
        this.actor = new St.Widget({
            name: 'personal-focus-slider',
            reactive: false,
            can_focus: false,
            x_align: Clutter.ActorAlign.START,
            y_align: Clutter.ActorAlign.START,
            opacity: 0,
        });
        this.layer = new Clutter.Actor({
            reactive: false,
            width: Math.max(1, panel.width),
            height: Math.max(1, panel.height),
            x_expand: true,
            y_expand: true,
            layout_manager: new Clutter.FixedLayout(),
        });
        panel._personalFocusLayer = this.layer;
        this.layer.add_child(this.actor);
        panel.insert_child_below(this.layer, panel.panel);
        this.tracker = tracker;
        this.trackerId = this.tracker.connect('notify::focus-app', () => this.queueUpdate());
        this.workspaceId = global.workspace_manager.connect('active-workspace-changed', () => this.queueUpdate());
        this.panelId = panel.connect('notify::allocation', () => {
            this.layer.set_size(Math.max(1, panel.width), Math.max(1, panel.height));
            this.queueUpdate(false);
        });
        this.actor.connect('destroy', () => this.destroy(true));
    }

    select(icon, color) {
        if (this.target !== icon) {
            this.disconnectTarget();
            this.target = icon;
            this.targetActor = icon._dotsContainer;
            this.targetIds = [
                this.targetActor.connect('notify::mapped', () => this.queueUpdate()),
                this.targetActor.connect('destroy', () => {
                    this.disconnectTarget();
                    this.target = null;
                    this.queueUpdate();
                }),
            ];
            this.watchTargetHierarchy();
        }
        this.actor.set_style(`background-color: ${color}; border-radius: 10px;`);
        this.queueUpdate(true);
    }

    watchTargetHierarchy() {
        this.disconnectHierarchy();
        // Closing an app recenters the taskbar and moves the icon's ancestors,
        // often without changing the dots container's own allocation at all.
        for (let actor = this.targetActor; actor && actor !== this.panel; actor = actor.get_parent()) {
            for (const property of ['allocation', 'translation-x', 'translation-y', 'scale-x', 'scale-y']) {
                const id = actor.connect(`notify::${property}`, () => this.queueUpdate(false));
                this.hierarchyIds.push([actor, id]);
            }
            const id = actor.connect('parent-set', () => {
                this.watchTargetHierarchy();
                this.queueUpdate(false);
            });
            this.hierarchyIds.push([actor, id]);
        }
    }

    disconnectHierarchy() {
        for (const [actor, id] of this.hierarchyIds ?? [])
            actor.disconnect(id);
        this.hierarchyIds = [];
    }

    queueUpdate(animate = true) {
        if (this.destroyed)
            return;
        this.animate = animate || this.animate;
        if (this.pending)
            return;
        this.pending = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            this.pending = 0;
            const animateNow = this.animate;
            this.animate = false;
            this.update(animateNow);
            return GLib.SOURCE_REMOVE;
        });
    }

    update(animate) {
        if (!this.target || !this.targetActor?.mapped ||
            this.tracker.focus_app !== this.target.app ||
            !this.target._checkIfMonitorHasFocus()) {
            this.actor.remove_all_transitions();
            this.actor.opacity = 0;
            this.ready = false;
            return;
        }
        if (!this.panel.has_allocation() || !this.layer.has_allocation())
            return;
        const [px, py] = this.layer.get_transformed_position();
        const [pw, ph] = this.panel.get_transformed_size();
        const [tx, ty] = this.targetActor.get_transformed_position();
        const [tw, th] = this.targetActor.get_transformed_size();
        if (![px, py, pw, ph, tx, ty, tw, th].every(Number.isFinite))
            return;
        const sx = pw / this.panel.width;
        const sy = ph / this.panel.height;
        if (!(sx > 0 && sy > 0 && tw > 0 && th > 0))
            return;
        const bounds = {
            translation_x: (tx - px) / sx,
            translation_y: (ty - py) / sy,
            width: tw / sx,
            height: th / sy,
        };
        if (!this.ready) {
            this.actor.remove_all_transitions();
            Object.assign(this.actor, bounds);
            this.actor.opacity = 255;
            this.ready = true;
        } else {
            this.actor.ease({
                ...bounds,
                opacity: 255,
                duration: animate && St.Settings.get().enable_animations ? 180 : 0,
                mode: Clutter.AnimationMode.EASE_OUT_CUBIC,
            });
        }
    }

    disconnectTarget() {
        this.disconnectHierarchy();
        if (this.targetActor)
            this.targetIds?.forEach(id => this.targetActor.disconnect(id));
        this.targetActor = null;
        this.targetIds = [];
    }

    destroy(fromActor = false) {
        if (this.destroyed)
            return;
        this.destroyed = true;
        if (this.pending)
            GLib.source_remove(this.pending);
        this.pending = 0;
        this.disconnectTarget();
        this.tracker.disconnect(this.trackerId);
        global.workspace_manager.disconnect(this.workspaceId);
        this.panel.disconnect(this.panelId);
        if (this.panel._personalFocusLayer === this.layer)
            this.panel._personalFocusLayer = null;
        this.target = null;
        if (!fromActor) {
            this.actor.destroy();
            this.layer.destroy();
        }
    }
}
