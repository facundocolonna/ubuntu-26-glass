import St from 'gi://St';

/** Size the fill against its allocated track, including stretched cards. */
export function setBarWidth(actor, percent, logicalWidth) {
    const track = actor.get_parent();
    let binding = actor._smpBarWidth;
    if (!binding || binding.track !== track) {
        binding?.track.disconnectObject(actor);
        binding = {track, percent: 0, width: -1};
        binding.update = () => {
            const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
            let width = logicalWidth * scale;
            if (track.has_allocation()) {
                const content = track.get_theme_node().get_content_box(track.get_allocation_box());
                width = Math.max(0, content.x2 - content.x1);
            }
            const fillWidth = Math.round(width * binding.percent / 100);
            if (binding.width === fillWidth)
                return;
            binding.width = fillWidth;
            actor.set_width(fillWidth);
            // A previous 100% fill must not impose a minimum width that stops
            // its track from shrinking when the menu or monitor changes size.
            actor.min_width = 0;
        };
        track.connectObject('notify::allocation', binding.update, actor);
        actor._smpBarWidth = binding;
    }
    binding.percent = Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
    binding.update();
}
