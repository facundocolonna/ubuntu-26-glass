"""Build a version-matched Debian package without installing into /usr."""
import os
from pathlib import Path
import shutil
import subprocess


def command(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def query(*args):
    return subprocess.check_output(list(map(str, args)), text=True).strip()


def installed_version(package):
    result = subprocess.run(
        ['dpkg-query', '-W', '-f=${db:Status-Status}\t${Version}', package],
        capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.startswith('installed\t'):
        return result.stdout.split('\t', 1)[1]
    return None


def native_plan(repo, component):
    version = installed_version(component['mutter_package'])
    if component.get('required') is False:
        return 'not-needed', version
    arch = query('dpkg', '--print-architecture')
    if not version:
        raise RuntimeError('No está instalado libmutter-18-0; se requiere GNOME 50.')
    current = installed_version(component['package'])
    if current:
        dependencies = query('dpkg-query', '-W', '-f=${Depends}', component['package'])
        library = Path('/usr/lib') / query('dpkg-architecture', '-qDEB_HOST_MULTIARCH') / 'libblur-effect-1.0.so.1'
        typelib = library.parent / 'girepository-1.0/Blur-1.0.typelib'
        if f"{component['mutter_package']} (= {version})" in dependencies and library.exists() and typelib.exists():
            return 'installed', version
    if arch == component['binary_arch'] and version == component['binary_mutter']:
        return 'bundled', version
    return 'build', version


def build_package(repo, work):
    repo, work = Path(repo), Path(work)
    source = repo / 'vendor/native/gnome-rounded-blur'
    work.mkdir(parents=True, exist_ok=True)
    build = work / 'build'
    stage = work / 'stage'
    multiarch = query('dpkg-architecture', '-qDEB_HOST_MULTIARCH')
    arch = query('dpkg', '--print-architecture')
    mutter = installed_version('libmutter-18-0')
    dev_version = installed_version('libmutter-18-dev')
    if not mutter or dev_version != mutter:
        raise RuntimeError('libmutter-18-dev y libmutter-18-0 deben tener la misma versión.')
    command('meson', 'setup', build, source, '--prefix=/usr', f'--libdir=lib/{multiarch}', '--buildtype=release')
    command('meson', 'compile', '-C', build)
    command('meson', 'install', '-C', build, '--destdir', stage)
    # The runtime package only needs the library and its typelib.
    for directory in [stage / 'usr/include', stage / 'usr/share', stage / f'usr/lib/{multiarch}/pkgconfig']:
        if directory.exists():
            shutil.rmtree(directory)
    debian = stage / 'DEBIAN'
    debian.mkdir()
    revision = mutter.replace(':', '+').replace('~', '+')
    (debian / 'control').write_text(
        'Package: gnome-rounded-blur-local\n'
        f'Version: 1.0.0+git.a4db9e5+{revision}-2\n'
        f'Architecture: {arch}\n'
        'Maintainer: Local build <local@localhost>\n'
        f'Depends: libmutter-18-0 (= {mutter}), libglib2.0-0t64\n'
        'Description: Rounded dynamic blur for GNOME Shell 50\n'
        ' Built from the source bundled with gnome-glass.\n')
    doc = stage / 'usr/share/doc/gnome-rounded-blur-local'
    doc.mkdir(parents=True)
    shutil.copy2(source / 'LICENSE', doc / 'copyright')
    package = work / 'gnome-rounded-blur-local.deb'
    command('dpkg-deb', '--root-owner-group', '--build', stage, package)
    return package
