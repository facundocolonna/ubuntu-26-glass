#!/usr/bin/env bash
set -euo pipefail
bundle_dir="$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
exec /usr/bin/python3 - "$bundle_dir" "$@" <<'PY'
import datetime
import os
from pathlib import Path
import shutil
import subprocess
import sys
from gi.repository import Gio, GLib

if os.geteuid() == 0:
    sys.exit('Ejecutar sin sudo; el acceso al mouse se habilita al iniciar la aplicación.')
bundle=Path(sys.argv[1]).resolve()
data=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
uuid='littlebigmouse-cursor@gnome-glass.local'
dest=data/'gnome-shell/extensions'/uuid
if dest.exists():
    backup=data/'gnome-glass/backups'/('lbm-cursor-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(dest,backup)
shutil.copytree(bundle/'extension',dest,dirs_exist_ok=True)
settings=Gio.Settings.new('org.gnome.shell')
enabled=settings.get_strv('enabled-extensions')
if uuid not in enabled:
    settings.set_strv('enabled-extensions',[*enabled,uuid])
settings.set_strv('disabled-extensions',[s for s in settings.get_strv('disabled-extensions') if s!=uuid])
Gio.Settings.sync()
applications=data/'applications'
applications.mkdir(parents=True,exist_ok=True)
# Desktop entry quoted arguments escape %, backslash, quote, backtick and dollar.
def quoted(path):
    text=str(path).replace('%','%%')
    for old,new in [('\\','\\\\'),('"','\\"'),('`','\\`'),('$','\\$')]:
        text=text.replace(old,new)
    return '"'+text+'"'
(applications/'littlebigmouse-glass.desktop').write_text(
    '[Desktop Entry]\nType=Application\nName=LittleBigMouse (prueba)\n'
    'Comment=Corrección del mouse entre pantallas, sin límite de tiempo\n'
    f'Exec={quoted(bundle/"probar.sh")}\nIcon={bundle/"app/lbm.png"}\n'
    'Terminal=false\nCategories=Settings;HardwareSettings;\n'
    'StartupWMClass=LittleBigMouse.Ui.Avalonia\n')
# Optional per-monitor workspace controller shipped with the updated bundle.
workspace=bundle/'workspace-extension'
if workspace.exists():
    workspace_uuid='workspace-islands@danielbernalo.github.io'
    workspace_dest=data/'gnome-shell/extensions'/workspace_uuid
    if workspace_dest.exists():
        saved=data/'gnome-glass/backups'/('workspace-islands-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        saved.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(workspace_dest,saved)
    shutil.copytree(workspace,workspace_dest,dirs_exist_ok=True)
    subprocess.run(['glib-compile-schemas','--strict',str(workspace_dest/'schemas')],check=True)
    import json
    source=Gio.SettingsSchemaSource.new_from_directory(str(workspace_dest/'schemas'),Gio.SettingsSchemaSource.get_default(),False)
    controller=Gio.Settings.new_full(source.lookup('org.gnome.shell.extensions.workspace-islands',False),None,None)
    for key,spec in json.loads((bundle/'workspace-settings.json').read_text()).items():
        controller.set_value(key,GLib.Variant.parse(GLib.VariantType.new(spec['type']),spec['value'],None,None))
    Gio.Settings.new('org.gnome.mutter').set_boolean('workspaces-only-on-primary',True)
    enabled=settings.get_strv('enabled-extensions')
    if workspace_uuid not in enabled:
        settings.set_strv('enabled-extensions',[*enabled,workspace_uuid])
    settings.set_strv('disabled-extensions',[s for s in settings.get_strv('disabled-extensions') if s!=workspace_uuid])
    Gio.Settings.sync()

print('Instalado. Si es la primera instalación, guardá tu trabajo y volvé a iniciar sesión.')
print('Abrir: LittleBigMouse (prueba). Detener: ./probar.sh --stop')
if '--autostart' in sys.argv[2:]:
    auto=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'autostart'
    auto.mkdir(parents=True,exist_ok=True)
    # GNOME 50 ignores entries with X-GNOME-Autostart-Phase, including
    # Applications. Rewrite the complete entry to migrate older installations.
    (auto/'gnome-glass-littlebigmouse.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=LittleBigMouse\n'
        f'Exec={quoted(bundle/"probar.sh")} --autostart\n'
        'Terminal=false\nOnlyShowIn=GNOME;\nX-GNOME-Autostart-enabled=true\n')
    subprocess.run(['pkexec','/usr/bin/python3',str(bundle/'access.py'),'persist',str(os.getuid())],check=True)
    print('Inicio automático habilitado, con permisos persistentes limitados al Logitech y uinput.')
PY
