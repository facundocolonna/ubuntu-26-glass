#!/usr/bin/python3
"""Start the UI (hidden at login), then replay its saved layout to the engine."""
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import time
from xml.sax.saxutils import escape

BASE = Path(__file__).resolve().parent
APP = BASE / 'app/LittleBigMouse.Ui.Avalonia'

def ready():
    if not os.access('/dev/uinput', os.R_OK | os.W_OK):
        return False
    for event in Path('/sys/class/input').glob('event*'):
        try:
            if ((event / 'device/name').read_text().strip() == 'Logitech MX Anywhere 3'
                    and os.access(Path('/dev/input') / event.name, os.R_OK | os.W_OK)):
                return True
        except FileNotFoundError:
            pass  # Device disconnected during enumeration.
    return False

def main():
    if '--show' in sys.argv:
        for proc in Path('/proc').glob('[0-9]*/exe'):
            try:
                if proc.resolve() == APP:
                    return subprocess.call([str(APP)])  # Existing instance receives ShowRequested.
            except (FileNotFoundError, PermissionError, OSError):
                pass
        print('Esperando que se conecte el Logitech y que estén disponibles sus permisos.')
        return 0
    auto = '--autostart' in sys.argv
    if auto:
        print('Esperando mouse/permisos y configuración de pantallas...', flush=True)
        while not ready():
            time.sleep(2)
        time.sleep(5)
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'LittleBigMouse/options.json'
    options = json.loads(config.read_text()) if config.exists() else {}
    options['StartMinimized'] = auto
    config.parent.mkdir(parents=True, exist_ok=True)
    tmp = config.with_suffix('.launch.tmp')
    tmp.write_text(json.dumps(options, indent=2) + '\n')
    tmp.replace(config)
    # Side buttons are remapped only while the GNOME workspace handler is
    # actually active. Without it, ordinary back/forward buttons are preserved.
    active = False
    controller = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share'))) / 'gnome-shell/extensions/workspace-islands@danielbernalo.github.io'
    attempts = 16 if auto and controller.exists() else 1
    for attempt in range(attempts):
        try:
            from gi.repository import Gio, GLib
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            result = bus.call_sync('org.gnome.Shell', '/org/gnome/Shell',
                'org.gnome.Shell.Extensions', 'GetExtensionInfo',
                GLib.Variant('(s)', ('workspace-islands@danielbernalo.github.io',)),
                None, Gio.DBusCallFlags.NONE, 2000, None).unpack()[0]
            active = result.get('state') == 1
        except Exception:
            active = False
        if active:
            break
        if attempt + 1 < attempts:
            time.sleep(1)
    os.environ['LBM_GNOME_WORKSPACE_BUTTONS'] = '1' if active else '0'
    print('Botones laterales: ' + ('escritorios por pantalla' if active else 'atrás/adelante normales'), flush=True)
    ui = subprocess.Popen([str(APP)])
    current = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'LittleBigMouse/Current.xml'
    endpoint = os.environ.get('LBM_HOOK_ENDPOINT', str(Path(os.environ['XDG_RUNTIME_DIR']) / 'littlebigmouse-v1.sock'))
    # Wait for the UI/daemon to settle. Run validates the saved layout against
    # the actual monitor topology; incompatible layouts are refused upstream.
    time.sleep(2)
    if current.exists():
        for _ in range(60):
            if ui.poll() is not None:
                return ui.returncode
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    sock.connect(endpoint)
                    command = ('<Messages><CommandMessage Command="LoadFromFile"><Payload>'
                               + escape(str(current)) + '</Payload></CommandMessage>'
                               '<CommandMessage Command="Run"/></Messages>').encode()
                    sock.sendall(struct.pack('<I', len(command)) + command)
                print('Configuración guardada enviada al motor.', flush=True)
                break
            except (OSError, TimeoutError):
                time.sleep(0.5)
        else:
            print('El motor no respondió; revisar el registro de LittleBigMouse.', flush=True)
    return ui.wait()

if __name__ == '__main__':
    sys.exit(main())
