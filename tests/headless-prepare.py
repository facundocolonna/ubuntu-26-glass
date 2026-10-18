"""Prepare only the private XDG directories created by GNOME's test tool."""
import os
from pathlib import Path
import sys
import tempfile

data = Path(os.environ['XDG_DATA_HOME'])
if os.environ.get('GSETTINGS_BACKEND') != 'keyfile' or not str(data).startswith('/tmp/'):
    raise SystemExit('Este script solo funciona dentro de gnome-shell-test-tool.')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import installer as i
components = i.read_json(i.REPO / 'profile/components.json')
profile = i.read_json(i.REPO / 'profile/settings.json')
if os.environ.get('GNOME_GLASS_TEST_MONITORS') == '3':
    import json
    from gi.repository import GLib
    layout = profile['schemas']['org.gnome.shell.extensions.dash-to-panel']['values']['panel-element-positions']
    layouts = json.loads(i.variant(layout).get_string())
    # None of the virtual monitor IDs is configured: exercise hotplug fallback.
    layout['value'] = GLib.Variant('s', json.dumps({'previous-monitor': next(iter(layouts.values()))})).print_(True)
data.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=data.parent) as temporary:
    stage = Path(temporary) / 'stage'
    i.stage_payload(i.REPO, stage, components)
    i.deploy(stage, components, data)
i.apply_profile(profile, data / 'gnome-shell/extensions')
i.enable_profile(components)
arguments = sys.argv[1:]
if os.environ.get('GNOME_GLASS_TEST_MONITORS') == '3':
    arguments += ['--virtual-monitor', '1024x768', '--virtual-monitor', '1600x900']
os.execvp(arguments[0], arguments)
