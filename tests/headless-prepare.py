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
data.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=data.parent) as temporary:
    stage = Path(temporary) / 'stage'
    i.stage_payload(i.REPO, stage, components)
    i.deploy(stage, components, data)
i.apply_profile(profile, data / 'gnome-shell/extensions')
i.enable_profile(components)
os.execvp(sys.argv[1], sys.argv[1:])
