#!/usr/bin/python3
"""Install/restore the frozen GNOME profile; all user writes are backed up."""
import argparse
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

from gi.repository import Gio, GLib

from native import build_package, command, installed_version, native_plan

REPO = Path(__file__).resolve().parents[1]
SHELL_SCHEMA = 'org.gnome.shell'
SHELL_KEYS = ['enabled-extensions', 'disabled-extensions', 'disable-user-extensions']


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def variant(spec):
    return GLib.Variant.parse(GLib.VariantType.new(spec['type']), spec['value'], None, None)


def serialize(value):
    return None if value is None else {'type': value.get_type_string(), 'value': value.print_(True)}


def verify_payload(repo=REPO):
    count = 0
    for line in (repo / 'SHA256SUMS').read_text().splitlines():
        digest, relative = line.split('  ', 1)
        path = repo / relative
        if path.is_symlink() or not path.resolve().is_relative_to(repo.resolve()):
            raise RuntimeError(f'Ruta inválida en manifiesto: {relative}')
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            raise RuntimeError(f'Archivo modificado o corrupto: {relative}')
        count += 1
    return count


def validate_system():
    release = {}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            release[key] = value.strip('"')
    if release.get('ID') != 'ubuntu' or release.get('VERSION_ID') != '26.04':
        raise RuntimeError('Este perfil está preparado para Ubuntu 26.04 con GNOME 50.')
    version = subprocess.check_output(['gnome-shell', '--version'], text=True).strip()
    if not version.split()[-1].startswith('50.'):
        raise RuntimeError(f'Versión de GNOME no compatible: {version}')
    if os.environ.get('XDG_SESSION_TYPE') != 'wayland':
        raise RuntimeError('Ejecutá el instalador dentro de tu sesión GNOME con Wayland.')
    if not os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
        raise RuntimeError('No hay un bus de sesión. Abrí una terminal de tu escritorio.')
    return version


def schema_settings(name, entry, extension_root):
    if 'extension' in entry:
        source = Gio.SettingsSchemaSource.new_from_directory(
            str(extension_root / entry['extension'] / 'schemas'),
            Gio.SettingsSchemaSource.get_default(), False)
    else:
        source = Gio.SettingsSchemaSource.get_default()
    schema = source.lookup(name, True)
    if schema is None:
        raise RuntimeError(f'No se encontró el esquema {name}')
    return Gio.Settings.new_full(schema, None, None), schema


def validate_profile(profile, extension_root):
    for name, entry in profile['schemas'].items():
        settings, schema = schema_settings(name, entry, extension_root)
        for key, spec in entry['values'].items():
            if not schema.has_key(key) or not schema.get_key(key).range_check(variant(spec)):
                raise RuntimeError(f'Ajuste inválido: {name}.{key}')
            if not settings.is_writable(key):
                raise RuntimeError(f'Ajuste bloqueado por el sistema: {name}.{key}')


def paths(data_home, components):
    return [*(Path('gnome-shell/extensions') / c['uuid'] for c in components['extensions']),
            *(Path('icons') / name for name in components['themes'])]


def copy_item(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        target.symlink_to(os.readlink(source), target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    else:
        shutil.copy2(source, target)


def remove_item(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def ensure_safe_parents(data_home, relative):
    # Do not follow a pre-existing symlink in an installation destination.
    parent = data_home
    for part in relative.parts[:-1]:
        parent /= part
        if parent.is_symlink():
            raise RuntimeError(f'La carpeta de destino es un enlace simbólico: {parent}')


def snapshot(profile, components, data_home, backup):
    backup.mkdir(parents=True, mode=0o700)
    state = {'format': 1, 'data_home': str(data_home), 'settings': {}, 'files': [],
             'native_package_before': installed_version('gnome-rounded-blur-local')}
    source_root = REPO / 'vendor/extensions'
    for name, entry in profile['schemas'].items():
        settings, _ = schema_settings(name, entry, source_root)
        state['settings'][name] = {'extension': entry.get('extension'), 'values': {
            key: serialize(settings.get_user_value(key)) for key in entry['values']}}
    shell = Gio.Settings.new(SHELL_SCHEMA)
    state['settings'][SHELL_SCHEMA] = {'values': {
        key: serialize(shell.get_user_value(key)) for key in SHELL_KEYS}}
    for relative in paths(data_home, components):
        ensure_safe_parents(data_home, relative)
        source = data_home / relative
        exists = source.exists() or source.is_symlink()
        state['files'].append({'relative': str(relative), 'existed': exists})
        if exists:
            copy_item(source, backup / 'files' / relative)
    # Save the exact schemas used for restoration even if extensions are removed.
    for c in components['extensions']:
        shutil.copytree(source_root / c['uuid'] / 'schemas', backup / 'schemas' / c['uuid'])
    write_json(backup / 'state.json', state)
    return state


def apply_profile(profile, extension_root):
    for name, entry in profile['schemas'].items():
        settings, _ = schema_settings(name, entry, extension_root)
        settings.delay()
        for key, spec in entry['values'].items():
            if not settings.set_value(key, variant(spec)):
                raise RuntimeError(f'No se pudo guardar {name}.{key}')
        settings.apply()
    Gio.Settings.sync()


def pause_extensions(components):
    shell = Gio.Settings.new(SHELL_SCHEMA)
    managed = {c['uuid'] for c in components['extensions']}
    shell.set_strv('enabled-extensions', [x for x in shell.get_strv('enabled-extensions') if x not in managed])
    Gio.Settings.sync()
    # Let Shell finish callbacks before replacing loaded extension files.
    for c in reversed(components['extensions']):
        subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.gnome.Shell.Extensions',
                        '--object-path', '/org/gnome/Shell/Extensions', '--method',
                        'org.gnome.Shell.Extensions.DisableExtension', c['uuid']],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)


def enable_profile(components):
    shell = Gio.Settings.new(SHELL_SCHEMA)
    managed = [c['uuid'] for c in components['extensions']]
    # Dash to Panel first, Blur my Shell last: it needs the final panel geometry.
    managed.sort(key=lambda uuid: (uuid == 'blur-my-shell@aunetx', uuid != 'dash-to-panel@jderose9.github.com'))
    disabled = set(components['disable'])
    current = [x for x in shell.get_strv('enabled-extensions') if x not in disabled and x not in managed]
    shell.set_strv('disabled-extensions', [x for x in shell.get_strv('disabled-extensions') if x not in managed] +
                   [x for x in disabled if x not in shell.get_strv('disabled-extensions')])
    shell.set_strv('enabled-extensions', current + managed)
    shell.set_boolean('disable-user-extensions', False)
    Gio.Settings.sync()


def stage_payload(repo, stage, components):
    for c in components['extensions']:
        destination = stage / 'gnome-shell/extensions' / c['uuid']
        shutil.copytree(repo / 'vendor/extensions' / c['uuid'], destination, symlinks=True)
        command('glib-compile-schemas', '--strict', destination / 'schemas')
    icons = stage / 'icons'
    icons.mkdir()
    for name in components['themes']:
        with tarfile.open(repo / 'vendor/themes' / f'{name}.tar.xz') as archive:
            members = archive.getmembers()
            if any(Path(m.name).parts[0] != name for m in members):
                raise RuntimeError(f'Tema con rutas inválidas: {name}')
            archive.extractall(icons, filter='data')
        if not (icons / name / 'index.theme').is_file():
            raise RuntimeError(f'Tema incompleto: {name}')


def deploy(stage, components, data_home):
    for relative in paths(data_home, components):
        ensure_safe_parents(data_home, relative)
        target = data_home / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        remove_item(target)
        shutil.move(stage / relative, target)


def restore_backup(backup, data_home, components):
    state = read_json(backup / 'state.json')
    if Path(state['data_home']) != data_home:
        raise RuntimeError('La copia corresponde a otra carpeta de usuario.')
    allowed = set(map(str, paths(data_home, components)))
    if {f['relative'] for f in state['files']} != allowed:
        raise RuntimeError('La lista de archivos de la copia no coincide con este instalador.')
    for f in state['files']:
        relative = Path(f['relative'])
        ensure_safe_parents(data_home, relative)
        if f['existed'] and not ((backup / 'files' / relative).exists() or (backup / 'files' / relative).is_symlink()):
            raise RuntimeError(f'Copia incompleta: {relative}')
    pause_extensions(components)
    # First restore files; schemas needed by absent extensions live in the backup.
    for f in state['files']:
        target = data_home / f['relative']
        remove_item(target)
        if f['existed']:
            copy_item(backup / 'files' / f['relative'], target)
    for name, entry in state['settings'].items():
        if entry.get('extension'):
            schema_root = backup / 'schemas'
            source = Gio.SettingsSchemaSource.new_from_directory(
                str(schema_root / entry['extension']), Gio.SettingsSchemaSource.get_default(), False)
            settings = Gio.Settings.new_full(source.lookup(name, True), None, None)
        else:
            settings = Gio.Settings.new(name)
        settings.delay()
        for key, spec in entry['values'].items():
            if spec is None:
                settings.reset(key)
            elif not settings.set_value(key, variant(spec)):
                raise RuntimeError(f'No se pudo restaurar {name}.{key}')
        settings.apply()
    Gio.Settings.sync()


def ensure_packages(packages):
    missing = [p for p in packages if installed_version(p) is None]
    if missing:
        print('Instalando paquetes: ' + ', '.join(missing), flush=True)
        command('sudo', 'apt-get', 'update')
        command('sudo', 'apt-get', 'install', '-y', *missing)


def install_user_profile(profile, components, data_home, stage, backup):
    snapshot(profile, components, data_home, backup)
    print(f'Copia anterior: {backup}', flush=True)
    try:
        pause_extensions(components)
        deploy(stage, components, data_home)
        apply_profile(profile, data_home / 'gnome-shell/extensions')
        enable_profile(components)
    except BaseException:
        print('La instalación falló; restaurando la copia anterior...', file=sys.stderr, flush=True)
        restore_backup(backup, data_home, components)
        raise


def main():
    parser = argparse.ArgumentParser(description='Instalador de GNOME Glass para Ubuntu 26.04 / GNOME 50.')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--check', action='store_true', help='verificar integridad y compatibilidad, sin cambiar nada')
    modes.add_argument('--dry-run', action='store_true', help='mostrar el plan, sin instalar ni escribir ajustes')
    modes.add_argument('--restore', type=Path, metavar='COPIA', help='restaurar una copia creada por este instalador')
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise RuntimeError('Ejecutá sin sudo; se pedirá solo para los paquetes del sistema.')
    count = verify_payload()
    profile = read_json(REPO / 'profile/settings.json')
    components = read_json(REPO / 'profile/components.json')
    data_home = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))).resolve()
    if args.restore:
        backup = args.restore.expanduser().resolve()
        restore_backup(backup, data_home, components)
        print('Ajustes y archivos de usuario restaurados. Cerrá sesión y volvé a entrar.')
        print('Los paquetes del sistema se conservan; consultá docs/PAQUETES.md.')
        return
    version = validate_system()
    validate_profile(profile, REPO / 'vendor/extensions')
    mode, mutter = native_plan(REPO, components['native'])
    packages = read_json(REPO / 'profile/packages.json')
    missing = [p for p in packages['runtime'] + packages['tools'] + packages['build'] if installed_version(p) is None]
    print(f'Integridad: {count} archivos verificados. {version}; Mutter {mutter}.')
    print('Extensiones: barra, desenfoque, esquinas de ventanas, CPU y RAM.')
    print('Temas: WhiteSur-dark, Bibata-Modern-Ice, Yaru-blue-dark.')
    print('Biblioteca de desenfoque: ' + {'installed': 'ya instalada y compatible', 'bundled': 'instalar .deb incluido', 'build': 'compilar para el Mutter instalado'}[mode])
    print('Paquetes pendientes: ' + (', '.join(missing) or 'ninguno'))
    if args.check or args.dry_run:
        print('Verificación terminada. No se modificó el escritorio.')
        return
    data_home.mkdir(parents=True, exist_ok=True)
    state_root = data_home / 'gnome-glass'
    state_root.mkdir(mode=0o700, exist_ok=True)
    with (state_root / 'installer.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ensure_packages(packages['runtime'] + packages['tools'] + packages['build'])
        # Package installation can update Mutter; inspect the actual version again.
        mode, mutter = native_plan(REPO, components['native'])
        with tempfile.TemporaryDirectory(prefix='gnome-glass-', dir=state_root) as temporary:
            temporary = Path(temporary)
            if mode != 'installed':
                package = (REPO / 'vendor/native/gnome-rounded-blur-local.deb' if mode == 'bundled'
                           else build_package(REPO, temporary / 'native'))
                command('sudo', 'dpkg', '-i', package)
                command('sudo', 'ldconfig')
            stage = temporary / 'payload'
            stage_payload(REPO, stage, components)
            backup = state_root / 'backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            install_user_profile(profile, components, data_home, stage, backup)
            write_json(state_root / 'last-install.json', {'backup': str(backup), 'repository': str(REPO)})
    print('Instalación completa. Guardá tu trabajo, cerrá sesión y volvé a entrar.')
    print(f'Para restaurar: ./install.sh --restore "{backup}"')


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
