"""Packages installed on the external flash, as the running system sees them."""

import json
import sys

import pytest

import wasp
import gadgetbridge
import appregistry
from apps.faces.app import FacesApp

# A 2x2 one-bit icon: four background pixels.
ICON = bytes((1, 2, 2, 4))

APP_SOURCE = '''
import wasp

class {cls}():
    NAME = '{label}'

    def foreground(self):
        wasp.watch.drawable.fill()

    def preview(self):
        wasp.watch.drawable.fill()
'''


@pytest.fixture
def flash(tmp_path, monkeypatch):
    """Stand a temporary directory in for /flash, importable as on the watch."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    return tmp_path


@pytest.fixture
def system(monkeypatch):
    system = wasp.system
    if not system.app:
        system.secondary_init()
    monkeypatch.setattr(system, 'quick_ring', list(system.quick_ring))
    monkeypatch.setattr(system, 'launcher_ring', list(system.launcher_ring))
    yield system
    system.switch(system.quick_ring[0])


def install(flash, name, enabled=True, **meta):
    """Lay out a package and its index entry as pkgmgr.py would."""
    cls = name.title() + 'App'
    label = name.title()
    entry = {'name': name, 'label': label, 'cls': cls, 'kind': 'app',
             'resident': False, 'quick_ring': False, 'version': '1.0.0'}
    entry.update(meta)
    path = flash / 'pkg' / name
    path.mkdir(parents=True)
    (path / 'app.py').write_text(APP_SOURCE.format(cls=cls, label=label))
    (path / 'icon.rle').write_bytes(ICON)
    (path / 'meta.json').write_text(json.dumps(entry))
    index_path = flash / 'pkg' / 'index.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    entry['enabled'] = enabled
    index[name] = entry
    index_path.write_text(json.dumps(index))


def listed(system, name):
    return [app for app in system.launcher_ring if app.NAME == name]


def test_an_enabled_package_joins_the_launcher(flash, system):
    install(flash, 'apricot')

    system.register_packages()

    (entry,) = listed(system, 'Apricot')
    assert isinstance(entry, wasp.PackageEntry)
    assert entry.ICON == (2, 2, bytes((4,)))
    assert 'pkgmgr' not in sys.modules


def test_a_package_opens_and_unloads_completely(flash, system):
    install(flash, 'banana')
    system.register_packages()
    (entry,) = listed(system, 'Banana')

    system.switch(entry)
    system._tick()
    assert type(system.app).__name__ == 'BananaApp'

    system.switch(system.quick_ring[0])
    for module in ('pkg', 'pkg.banana', 'pkg.banana.app'):
        assert module not in sys.modules


def test_a_resident_package_keeps_its_instance(flash, system):
    install(flash, 'cherry', resident=True)
    system.register_packages()
    (entry,) = listed(system, 'Cherry')

    assert entry.load() is entry.load()


def test_disabled_packages_and_faces_stay_off_the_launcher(flash, system):
    install(flash, 'damson', enabled=False)
    install(flash, 'elder', kind='face')

    system.register_packages()

    assert not listed(system, 'Damson')
    assert not listed(system, 'Elder')


def test_a_package_can_ask_for_the_quick_ring(flash, system):
    install(flash, 'fig', quick_ring=True)

    system.register_packages()

    assert [app.NAME for app in system.quick_ring if app.NAME == 'Fig']
    assert not listed(system, 'Fig')


def test_a_damaged_index_does_not_stop_start_up(flash, system):
    (flash / 'pkg').mkdir()
    (flash / 'pkg' / 'index.json').write_text('{"g": {"name": "g", "enabled": true}}')

    system.register_packages()


def test_the_faces_app_offers_an_installed_face(flash, system):
    install(flash, 'guava', kind='face')
    faces = FacesApp()

    faces.foreground()
    paths = [path for (path, label) in faces.choices]
    faces.background()

    assert 'pkg.guava.app.GuavaApp' in paths
    assert len(paths) == len(appregistry.faces_list) + 1


def test_the_repl_reaches_the_manager_by_name():
    import sys
    import pkgmgr
    expected = pkgmgr.abi()
    del sys.modules['pkgmgr']

    assert gadgetbridge.pkg.abi() == expected
    assert 'pkgmgr' not in sys.modules

