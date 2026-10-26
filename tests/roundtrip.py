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
shell.set_strv('enabled-extensions', ['ubuntu-dock@ubuntu.com', 'example@unrelated', 'blur-my-shell@aunetx', 'system-monitor-panel@naimur'])
i.Gio.Settings.sync()
gtk_css = Path(os.environ['XDG_CONFIG_HOME']) / 'gtk-4.0/gtk.css'
gtk_css.parent.mkdir(parents=True, exist_ok=True)
original_css = '/* Existing user customizations */\nbutton { padding: 7px; }\n'
gtk_css.write_text(original_css)
gtk_glass = gtk_css.with_name('gnome-glass-nautilus.css')

# A v1.0 backup has four extensions and no ScreenToSpace/Mutter settings.
legacy_components = dict(components)
legacy_components['extensions'] = [c for c in components['extensions']
                                   if c['uuid'] not in ['screentospace@dilzhan.dev', 'workspace-islands@danielbernalo.github.io']]
legacy_profile = {'format': 1, 'schemas': {
    name: entry for name, entry in profile['schemas'].items()
    if name not in ['org.gnome.shell.extensions.screentospace', 'org.gnome.shell.extensions.workspace-islands', 'org.gnome.mutter']}}
i.snapshot(legacy_profile, legacy_components, data, base / 'backup-v1')
legacy_state = i.read_json(base / 'backup-v1/state.json')
legacy_state.pop('config_home', None)
legacy_state.pop('config_files', None)
i.write_json(base / 'backup-v1/state.json', legacy_state)

# Older real backups recorded upstream UUIDs. Keep them restorable after forks.
shutil.copytree(base / 'backup-v1', base / 'backup-upstream-ids')
alias_state = i.read_json(base / 'backup-upstream-ids/state.json')
for component in components['extensions']:
    old = component.get('upstream_uuid')
    if not old:
        continue
    local = component['uuid']
    for item in alias_state['files']:
        if item['relative'] == f'gnome-shell/extensions/{local}':
            item['relative'] = f'gnome-shell/extensions/{old}'
    for entry in alias_state['settings'].values():
        if entry.get('extension') == local:
            entry['extension'] = old
    for prefix in ['files/gnome-shell/extensions', 'schemas']:
        source = base / 'backup-upstream-ids' / prefix / local
        if source.exists():
            source.rename(source.with_name(old))
i.write_json(base / 'backup-upstream-ids/state.json', alias_state)


def verify_installed():
    assert gtk_css.read_text() == i.gtk_style.IMPORT + original_css
    assert gtk_glass.read_text() == (repo / 'profile/nautilus-glass.css').read_text()
    for name, entry in profile['schemas'].items():
        settings, _ = i.schema_settings(name, entry, data / 'gnome-shell/extensions')
        for key, spec in entry['values'].items():
            assert settings.get_value(key).equal(i.variant(spec)), f'{name}.{key}'
    enabled = shell.get_strv('enabled-extensions')
    assert 'example@unrelated' in enabled
    assert 'ubuntu-dock@ubuntu.com' not in enabled
    assert 'blur-my-shell@aunetx' not in enabled
    assert 'system-monitor-panel@naimur' not in enabled
    assert enabled.index('dash-to-panel@jderose9.github.com') < enabled.index('blur-my-shell@gnome-glass.local')
    for c in components['extensions']:
        assert (data / 'gnome-shell/extensions' / c['uuid'] / 'metadata.json').exists()
    for name in components['themes']:
        assert (data / 'icons' / name / 'index.theme').exists()


def verify_original():
    assert gtk_css.read_text() == original_css
    assert not gtk_glass.exists()
    assert (old_extension / 'old-file.txt').read_text() == 'Previous extension content\n'
    assert (old_theme / 'old-file.txt').read_text() == 'Previous icon content\n'
    assert not (data / 'icons/WhiteSur-dark').exists()
    assert interface.get_string('icon-theme') == 'Yaru'
    assert interface.get_double('text-scaling-factor') == 1.1
    assert shell.get_strv('enabled-extensions') == ['ubuntu-dock@ubuntu.com', 'example@unrelated', 'blur-my-shell@aunetx', 'system-monitor-panel@naimur']
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
pending = Path(os.environ['XDG_CONFIG_HOME']) / 'autostart/gnome-glass-local-extensions.desktop'
pending.parent.mkdir(exist_ok=True)
pending.write_text('[Desktop Entry]\nX-GNOME-Glass-Migration=true\n')
i.restore_backup(base / 'backup-1', data, components)
assert not pending.exists(), 'Restore must cancel a pending local-extension migration'
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

# Fail after GTK has been changed, so rollback must restore user CSS as well.
stage = base / 'stage-after-gtk-failure'
i.stage_payload(repo, stage, components)
apply = i.apply_profile
def injected_failure(*args):
    assert gtk_css.read_text().startswith(i.gtk_style.IMPORT)
    raise RuntimeError('Injected failure after GTK deployment')
i.apply_profile = injected_failure
try:
    i.install_user_profile(profile, components, data, stage, base / 'backup-after-gtk-failure')
except RuntimeError:
    pass
else:
    raise AssertionError('Expected injected failure')
finally:
    i.apply_profile = apply
verify_original()
print('PASS GTK rollback: original user CSS and missing glass stylesheet restored')

stage = base / 'stage-legacy-restore'
i.stage_payload(repo, stage, components)
i.install_user_profile(profile, components, data, stage, base / 'backup-before-legacy-restore')
i.restore_backup(base / 'backup-v1', data, components)
assert shell.get_strv('enabled-extensions') == ['ubuntu-dock@ubuntu.com', 'example@unrelated', 'blur-my-shell@aunetx', 'system-monitor-panel@naimur']
assert interface.get_string('icon-theme') == 'Yaru'
assert (old_extension / 'old-file.txt').read_text() == 'Previous extension content\n'
assert (old_theme / 'old-file.txt').read_text() == 'Previous icon content\n'
assert gtk_css.read_text() == original_css
assert not gtk_glass.exists()
for name, entry in legacy_profile['schemas'].items():
    if 'extension' in entry:
        settings, _ = i.schema_settings(name, entry, repo / 'vendor/extensions')
        assert all(settings.get_user_value(key) is None for key in entry['values'])
print('PASS restore of a v1.0 backup: original profile and activation restored; new extension inactive')

i.restore_backup(base / 'backup-upstream-ids', data, components)
assert (data / 'gnome-shell/extensions/blur-my-shell@aunetx/old-file.txt').read_text() == 'Previous extension content\n'
assert shell.get_strv('enabled-extensions') == ['ubuntu-dock@ubuntu.com', 'example@unrelated', 'blur-my-shell@aunetx', 'system-monitor-panel@naimur']
print('PASS restore of upstream UUID backup: old paths and schemas are accepted after local fork migration')
