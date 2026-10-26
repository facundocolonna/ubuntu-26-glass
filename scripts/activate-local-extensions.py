#!/usr/bin/python3
"""One-time migration after Shell discovers the locally maintained extensions."""
import json
from pathlib import Path
import time
from gi.repository import Gio, GLib

PAIRS = {
    'system-monitor-panel@naimur': 'system-monitor-panel@gnome-glass.local',
    'blur-my-shell@aunetx': 'blur-my-shell@gnome-glass.local',
}


def extension_info(bus, uuid):
    result = bus.call_sync('org.gnome.Shell.Extensions', '/org/gnome/Shell/Extensions',
                          'org.gnome.Shell.Extensions', 'GetExtensionInfo',
                          GLib.Variant('(s)', (uuid,)), None,
                          Gio.DBusCallFlags.NONE, 5000, None)
    return result.unpack()[0]


def main():
    settings = Gio.Settings.new('org.gnome.shell')
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    for attempt in range(30):
        if all(extension_info(bus, uuid) for uuid in PAIRS.values()):
            break
        time.sleep(1)
    else:
        raise RuntimeError('GNOME todavía no descubrió las extensiones locales; volver a iniciar sesión.')
    before_enabled = settings.get_strv('enabled-extensions')
    before_disabled = settings.get_strv('disabled-extensions')
    enabled = []
    for uuid in before_enabled:
        replacement = PAIRS.get(uuid, uuid)
        if replacement not in enabled:
            enabled.append(replacement)
    for uuid in PAIRS.values():
        if uuid not in enabled:
            enabled.append(uuid)
    # Blur starts after Dash to Panel and its secondary bars have been created.
    blur = PAIRS['blur-my-shell@aunetx']
    enabled.remove(blur)
    enabled.append(blur)
    disabled = list(dict.fromkeys([u for u in before_disabled if u not in PAIRS.values()] + list(PAIRS)))
    try:
        settings.delay()
        settings.set_strv('disabled-extensions', disabled)
        settings.set_strv('enabled-extensions', enabled)
        settings.apply()
        Gio.Settings.sync()
        for attempt in range(30):
            infos = {uuid: extension_info(bus, uuid) for uuid in PAIRS.values()}
            if all(info.get('state') == 1 for info in infos.values()):
                break
            if any(info.get('state') == 3 for info in infos.values()):
                raise RuntimeError(f'No se pudieron activar las extensiones locales: {infos}')
            time.sleep(1)
        else:
            raise RuntimeError('La activación de las extensiones locales no terminó.')
    except Exception:
        settings.set_strv('enabled-extensions', before_enabled)
        settings.set_strv('disabled-extensions', before_disabled)
        settings.apply()
        Gio.Settings.sync()
        raise
    autostart = Path(GLib.get_user_config_dir()) / 'autostart/gnome-glass-local-extensions.desktop'
    if autostart.exists() and 'X-GNOME-Glass-Migration=true' in autostart.read_text():
        autostart.unlink()
    print(json.dumps({'local_extensions': list(PAIRS.values()), 'active': True}))


if __name__ == '__main__':
    main()
