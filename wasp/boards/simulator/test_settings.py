"""Settings kept on the flash across a restart."""

import json

import pytest

import wasp
import appregistry


@pytest.fixture
def system(tmp_path, monkeypatch):
    system = wasp.system
    if not system.app:
        system.secondary_init()
    path = tmp_path / 'settings.json'
    saved = (system._brightness, system._notifylevel, system._nfylev_ms, system._units,
             system._theme, list(system.quick_ring))
    monkeypatch.setattr(system, 'settings_file', str(path))
    monkeypatch.setattr(system, '_settings_text', system._settings())
    yield system, path
    (system._brightness, system._notifylevel, system._nfylev_ms, system._units,
     system._theme, ring) = saved
    system.quick_ring[:] = ring


def restart(path):
    """Build a second manager from the defaults and the saved file, as start up does."""
    manager = wasp.Manager()
    manager.settings_file = str(path)
    manager.register_defaults()
    manager._load_settings()
    return manager


def test_a_change_is_written(system):
    (system, path) = system
    system.brightness = 1
    system.units = 'Imperial'

    saved = json.loads(path.read_text())
    assert (saved['brightness'], saved['units']) == (1, 'Imperial')


def test_setting_a_value_it_already_has_writes_nothing(system):
    (system, path) = system
    system.brightness = system.brightness

    assert not path.exists()


def test_a_restart_brings_the_settings_back(system):
    (system, path) = system
    (module, label) = appregistry.faces_list[-1]
    theme = bytes(range(len(system._theme)))
    path.write_text(json.dumps({
        'brightness': 3, 'notify_level': 1, 'units': 'Imperial',
        'theme': list(theme), 'face': ['{}.{}App'.format(module, label), label]}))

    manager = restart(path)

    assert (manager.brightness, manager.notify_level, manager.units) == (3, 1, 'Imperial')
    assert bytes(manager._theme) == theme
    assert manager.quick_ring[0].path == '{}.{}App'.format(module, label)


def test_a_face_that_no_longer_exists_is_ignored(system):
    (system, path) = system
    path.write_text(json.dumps({'face': ['faces.gone.app.GoneApp', 'Gone']}))

    manager = restart(path)

    assert manager.quick_ring[0].path != 'faces.gone.app.GoneApp'


def test_a_damaged_file_leaves_the_defaults(system):
    (system, path) = system
    path.write_text('{not json')

    manager = restart(path)

    assert (manager.brightness, manager.units) == (2, 'Metric')
