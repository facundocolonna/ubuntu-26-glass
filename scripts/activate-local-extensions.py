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
    def wait_until(predicate, message):
        stable = 0
        for attempt in range(120):
            stable = stable + 1 if predicate() else 0
            if stable >= 2:
                return
            time.sleep(0.25)
        raise RuntimeError(message)

    def settled():
        # Metadata alone is available before Shell finishes enabling extensions.
        return all(extension_info(bus, uuid).get('state') not in (6, 7, 8)
                   for uuid in settings.get_strv('enabled-extensions')
                   if uuid not in settings.get_strv('disabled-extensions'))

    wait_until(lambda: all(extension_info(bus, uuid) for uuid in PAIRS.values()) and settled(),
               'GNOME todavía está cargando las extensiones; esperar a que termine el inicio.')
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
    managed = set(PAIRS) | set(PAIRS.values())
    base = [uuid for uuid in before_enabled if uuid not in managed]

    def write_list(key, value):
        if settings.get_strv(key) != value:
            settings.set_strv(key, value)
            Gio.Settings.sync()

    def stopped():
        return settled() and all(extension_info(bus, uuid).get('state') not in (1, 7, 8)
                                 for uuid in managed)

    try:
        # One settings notification at a time: changing both keys together can
        # start concurrent Shell rebases and call enable twice on the same object.
        write_list('enabled-extensions', base)
        wait_until(stopped, 'GNOME no terminó de desactivar las versiones anteriores.')
        write_list('disabled-extensions', disabled)
        wait_until(settled, 'GNOME no terminó de aplicar las exclusiones.')
        write_list('enabled-extensions', enabled)

        def activated():
            infos = {uuid: extension_info(bus, uuid) for uuid in PAIRS.values()}
            if any(info.get('state') == 3 for info in infos.values()):
                raise RuntimeError(f'No se pudieron activar las extensiones locales: {infos}')
            return settled() and all(info.get('state') == 1 for info in infos.values())

        wait_until(activated, 'La activación de las extensiones locales no terminó.')
    except Exception:
        write_list('enabled-extensions', base)
        wait_until(stopped, 'GNOME no terminó de limpiar la activación fallida.')
        write_list('disabled-extensions', before_disabled)
        wait_until(settled, 'GNOME no terminó de restaurar las exclusiones.')
        write_list('enabled-extensions', before_enabled)
        raise
    autostart = Path(GLib.get_user_config_dir()) / 'autostart/gnome-glass-local-extensions.desktop'
    if autostart.exists() and 'X-GNOME-Glass-Migration=true' in autostart.read_text():
        autostart.unlink()
    print(json.dumps({'local_extensions': list(PAIRS.values()), 'active': True}))


if __name__ == '__main__':
    main()
