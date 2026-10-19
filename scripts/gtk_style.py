"""Manage a scoped Nautilus stylesheet without replacing unrelated GTK CSS."""
import os
from pathlib import Path
import shutil
import tempfile
from gi.repository import GLib

NAMES = ('gtk-4.0/gtk.css', 'gtk-4.0/gnome-glass-nautilus.css')
IMPORT = '@import url("gnome-glass-nautilus.css");\n'

def config_home():
    return Path(GLib.get_user_config_dir())

def safe_path(relative):
    root = config_home()
    if relative not in NAMES or (root / 'gtk-4.0').is_symlink():
        raise RuntimeError('Ruta de estilos GTK no válida o carpeta enlazada.')
    path = root / relative
    if path.exists() and path.is_dir():
        raise RuntimeError(f'Se esperaba un archivo CSS: {path}')
    return path

def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        target.symlink_to(os.readlink(source))
    else:
        shutil.copy2(source, target)

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as temp:
        temp.write(text)
    os.replace(temp.name, path)

def snapshot(backup, state):
    state['config_home'] = str(config_home())
    state['config_files'] = []
    for name in NAMES:
        path = safe_path(name)
        existed = path.exists() or path.is_symlink()
        state['config_files'].append({'relative': name, 'existed': existed})
        if existed:
            copy(path, backup / 'config-files' / name)

def install(repo):
    css = safe_path(NAMES[0])
    style = safe_path(NAMES[1])
    existing = css.read_text() if css.exists() else ''
    write(style, (repo / 'profile/nautilus-glass.css').read_text())
    # Imports belong before other CSS rules. Reinstallation is idempotent.
    write(css, IMPORT + existing.replace(IMPORT, ''))

def validate(backup, state):
    for name in NAMES:
        safe_path(name)
    if 'config_files' not in state:
        return
    if Path(state['config_home']) != config_home():
        raise RuntimeError('La copia corresponde a otra carpeta de configuración.')
    entries = state['config_files']
    if {f['relative'] for f in entries} != set(NAMES):
        raise RuntimeError('Lista de archivos GTK no válida en la copia.')
    for entry in entries:
        source = backup / 'config-files' / entry['relative']
        if entry['existed'] and not (source.exists() or source.is_symlink()):
            raise RuntimeError(f'Copia de GTK incompleta: {source}')

def restore(backup, state):
    validate(backup, state)
    if 'config_files' not in state:
        # Older backups predate GTK management: withdraw only our import/style.
        css, style = [safe_path(name) for name in NAMES]
        if css.exists():
            text = css.read_text()
            if IMPORT in text:
                text = text.replace(IMPORT, '')
                if text:
                    write(css, text)
                else:
                    css.unlink()
        if style.exists() and style.read_text().startswith('/* GNOME Glass:'):
            style.unlink()
        return
    entries = state['config_files']
    for entry in entries:
        target = safe_path(entry['relative'])
        target.unlink(missing_ok=True)
        if entry['existed']:
            copy(backup / 'config-files' / entry['relative'], target)
