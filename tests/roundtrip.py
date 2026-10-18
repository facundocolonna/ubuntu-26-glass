"""Exercise real staging, settings, reinstall, restore and rollback in isolation."""
import os
from pathlib import Path
import shutil
import sys

if os.environ.get('GSETTINGS_BACKEND') != 'keyfile' or not os.environ.get('XDG_DATA_HOME', '').startswith('/tmp/'):
    raise SystemExit('Ejecutá ./tests/run.sh para aislar los archivos y ajustes.')

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import installer as i

repo = i.REPO
profile = i.read_json(repo / 'profile/settings.json')
components = i.read_json(repo / 'profile/components.json')
data = Path(os.environ['XDG_DATA_HOME'])
data.mkdir(parents=True)
base = data.parent
assert i.verify_payload() > 100
i.validate_profile(profile, repo / 'vendor/extensions')

# Simulate a previous installation and unrelated user preferences.
old_extension = data / 'gnome-shell/extensions' / components['extensions'][0]['uuid']
old_extension.mkdir(parents=True)
(old_extension / 'old-file.txt').write_text('Previous extension content\n')
old_theme = data / 'icons/WhiteSur'
old_theme.mkdir(parents=True)
(old_theme / 'old-file.txt').write_text('Previous icon content\n')
interface = i.Gio.Settings.new('org.gnome.desktop.interface')
interface.set_string('icon-theme', 'Yaru')
interface.set_double('text-scaling-factor', 1.1)
shell = i.Gio.Settings.new('org.gnome.shell')
shell.set_strv('enabled-extensions', ['ubuntu-dock@ubuntu.com', 'example@unrelated'])
i.Gio.Settings.sync()


def verify_installed():
    for name, entry in profile['schemas'].items():
        settings, _ = i.schema_settings(name, entry, data / 'gnome-shell/extensions')
        for key, spec in entry['values'].items():
            assert settings.get_value(key).equal(i.variant(spec)), f'{name}.{key}'
    enabled = shell.get_strv('enabled-extensions')
    assert 'example@unrelated' in enabled
    assert 'ubuntu-dock@ubuntu.com' not in enabled
    assert enabled.index('dash-to-panel@jderose9.github.com') < enabled.index('blur-my-shell@aunetx')
    for c in components['extensions']:
        assert (data / 'gnome-shell/extensions' / c['uuid'] / 'metadata.json').exists()
    for name in components['themes']:
        assert (data / 'icons' / name / 'index.theme').exists()


def verify_original():
    assert (old_extension / 'old-file.txt').read_text() == 'Previous extension content\n'
    assert (old_theme / 'old-file.txt').read_text() == 'Previous icon content\n'
    assert not (data / 'icons/WhiteSur-dark').exists()
    assert interface.get_string('icon-theme') == 'Yaru'
    assert interface.get_double('text-scaling-factor') == 1.1
    assert shell.get_strv('enabled-extensions') == ['ubuntu-dock@ubuntu.com', 'example@unrelated']
    for name, entry in profile['schemas'].items():
        if 'extension' in entry:
            settings, _ = i.schema_settings(name, entry, repo / 'vendor/extensions')
            for key in entry['values']:
                assert settings.get_user_value(key) is None, f'Reset failed: {name}.{key}'


stage = base / 'stage-1'
i.stage_payload(repo, stage, components)
i.install_user_profile(profile, components, data, stage, base / 'backup-1')
verify_installed()
print('PASS installation: files, all settings, enabled order and unrelated extension')

stage = base / 'stage-2'
i.stage_payload(repo, stage, components)
i.install_user_profile(profile, components, data, stage, base / 'backup-2')
verify_installed()
i.restore_backup(base / 'backup-2', data, components)
verify_installed()
i.restore_backup(base / 'backup-1', data, components)
verify_original()
print('PASS reinstall and restore: old files, missing files, user values and unset keys')

stage = base / 'stage-failure'
i.stage_payload(repo, stage, components)
shutil.rmtree(stage / 'icons/Bibata-Modern-Ice')
try:
    i.install_user_profile(profile, components, data, stage, base / 'backup-failure')
except FileNotFoundError:
    pass
else:
    raise AssertionError('Expected partial deployment to fail')
verify_original()
print('PASS rollback after a failure during partial deployment')
