#!/usr/bin/python3
"""Scoped Logitech/uinput access, temporary ACLs or persistent seat-based udev rules."""
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys

def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs).stdout

def identity(path):
    st = path.stat()
    if not stat.S_ISCHR(st.st_mode):
        raise RuntimeError(f"Not a character device: {path}")
    return [st.st_dev, st.st_ino, st.st_rdev]

def main():
    if os.geteuid() != 0:
        raise RuntimeError("Ejecutar mediante pkexec o sudo.")
    action, uid_text = sys.argv[1:]
    uid = int(uid_text)
    caller = os.environ.get("PKEXEC_UID", os.environ.get("SUDO_UID"))
    if uid <= 0 or caller is None or int(caller) != uid:
        raise RuntimeError("El usuario debe coincidir con quien solicitó la autenticación.")
    pwd.getpwuid(uid)
    if action == 'persist':
        rules = ('# Managed by GNOME Glass LittleBigMouse\n'
                 'SUBSYSTEM=="input", KERNEL=="event*", ENV{ID_INPUT_MOUSE}=="1", '
                 'ENV{ID_INPUT_TOUCHPAD}!="1", ENV{ID_INPUT_KEYBOARD}!="1", '
                 'ATTRS{name}=="Logitech MX Anywhere 3", TAG+="uaccess"\n'
                 'SUBSYSTEM=="misc", KERNEL=="uinput", TAG+="uaccess", OPTIONS+="static_node=uinput"\n')
        rule_path = Path('/etc/udev/rules.d/69-gnome-glass-littlebigmouse.rules')
        module_path = Path('/etc/modules-load.d/gnome-glass-littlebigmouse.conf')
        for path, content in [(rule_path, rules), (module_path, 'uinput\n')]:
            if path.is_symlink() or (path.exists() and path.read_text() != content):
                raise RuntimeError(f'No se reemplaza una configuración diferente: {path}')
        for path, content in [(rule_path, rules), (module_path, 'uinput\n')]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            path.chmod(0o644)
        run('/usr/sbin/modprobe', 'uinput')
        run('/usr/bin/udevadm', 'control', '--reload-rules')
        run('/usr/bin/udevadm', 'trigger', '--action=change', '--subsystem-match=misc', '--sysname-match=uinput')
        for event in Path('/sys/class/input').glob('event*'):
            if (event / 'device/name').read_text().strip() == 'Logitech MX Anywhere 3':
                run('/usr/bin/udevadm', 'trigger', '--action=change', str(event))
        run('/usr/bin/udevadm', 'settle', '--timeout=10')
        print('Permisos persistentes por sesión activa: Logitech MX Anywhere 3 y uinput.')
        return
    state_dir = Path('/run/gnome-glass-lbm')
    state_dir.mkdir(mode=0o700, exist_ok=True)
    if state_dir.is_symlink() or state_dir.stat().st_uid != 0:
        raise RuntimeError("Directorio de estado no confiable.")
    os.chmod(state_dir, 0o700)
    state_path = state_dir / f'{uid}.json'
    saved = json.loads(state_path.read_text()) if state_path.exists() else {}
    if action == 'revoke':
        for name, entry in saved.items():
            path = Path(name)
            if path.exists() and identity(path) == entry['identity']:
                run('/usr/bin/setfacl', '--restore=-', input=entry['acl'])
        state_path.unlink(missing_ok=True)
        print('Acceso temporal retirado.')
        return
    if action != 'grant':
        raise RuntimeError('Acción desconocida.')
    mice = []
    for event in Path('/sys/class/input').glob('event*'):
        if (event / 'device/name').read_text().strip() != 'Logitech MX Anywhere 3':
            continue
        props = dict(line.split('=', 1) for line in run('/usr/bin/udevadm', 'info', '-q', 'property', '-p', str(event)).splitlines() if '=' in line)
        if props.get('ID_INPUT_MOUSE') == '1' and props.get('ID_INPUT_TOUCHPAD') != '1' and props.get('ID_INPUT_KEYBOARD') != '1':
            mice.append(Path('/dev/input') / event.name)
    if not mice:
        raise RuntimeError('Conectá el Logitech MX Anywhere 3 antes de iniciar la prueba.')
    devices = [Path('/dev/uinput'), *mice]
    for path in devices:
        fingerprint = identity(path)
        if str(path) not in saved or saved[str(path)]['identity'] != fingerprint:
            saved[str(path)] = {'identity': fingerprint, 'acl': run('/usr/bin/getfacl', '-p', str(path))}
    # Save before granting so even an interrupted grant can be undone.
    state_path.write_text(json.dumps(saved, indent=2) + '\n')
    os.chmod(state_path, 0o600)
    for path in devices:
        run('/usr/bin/setfacl', '-m', f'u:{uid}:rw', str(path))
    print('Acceso temporal habilitado: ' + ', '.join(map(str, devices)))

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        sys.exit(str(exc))
