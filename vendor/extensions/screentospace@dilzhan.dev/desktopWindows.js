// Desktop Icons NG uses ordinary Wayland windows to draw each desktop.
import Meta from 'gi://Meta';

export function isDesktopSurface(window) {
    if (window.get_window_type() === Meta.WindowType.DESKTOP ||
        window.customJS_ding?._hideFromWindowList)
        return true;
    const appId = window.get_gtk_application_id?.();
    const title = window.get_title?.() || '';
    return appId === 'com.rastersoft.ding' &&
        (/^@!-?\d+,-?\d+;[BDHFT]+$/i.test(title) || /^Desktop Icons \d+$/.test(title));
}
