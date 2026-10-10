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
             system._theme, list(system.quick_ring), system._blank_after, system._clock_24h, system._step_goal)
    monkeypatch.setattr(system, 'settings_file', str(path))
    monkeypatch.setattr(system, '_settings_text', system._settings())
    yield system, path
    (system._brightness, system._notifylevel, system._nfylev_ms, system._units,
     system._theme, ring, system._blank_after, system._clock_24h, system._step_goal) = saved
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
    (face, label) = appregistry.faces_list[-1]
    theme = bytes(range(len(system._theme)))
    path.write_text(json.dumps({
        'brightness': 3, 'notify_level': 1, 'units': 'Imperial',
        'theme': list(theme), 'face': [face, label]}))

    manager = restart(path)

    assert (manager.brightness, manager.notify_level, manager.units) == (3, 1, 'Imperial')
    assert bytes(manager._theme) == theme
    assert manager.quick_ring[0].path == face


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


def test_the_screen_timeout_is_kept(system):
    (system, path) = system
    system.blank_after = 30

    manager = restart(path)

    assert manager.blank_after == 30


def test_a_screen_timeout_not_offered_is_ignored(system):
    (system, path) = system
    path.write_text(json.dumps({'blank_after': 7}))

    manager = restart(path)

    assert manager.blank_after == 15


def test_the_settings_app_picks_the_screen_timeout_tapped(system):
    (system, path) = system
    from settings import SettingsApp
    app = SettingsApp()
    system.switch(app)
    app._sett_index = app._settings.index('Screen Timeout')
    app._draw()
    choices = wasp.BLANK_AFTER
    wanted = (choices.index(system.blank_after) + 1) % len(choices)
    (x, y, w) = app._cell(wanted, len(choices))

    app.touch((wasp.EventType.TOUCH, x + w // 2, y + 20))

    assert system.blank_after == choices[wanted]
    system.switch(system.quick_ring[0])


def test_the_clock_format_is_kept(system):
    (system, path) = system
    system.clock_24h = False

    manager = restart(path)

    assert manager.clock_24h is False


def test_a_12_hour_clock_reads_hours_as_people_say_them(system):
    (system, path) = system
    system.clock_24h = False

    assert [system.display_hour(h) for h in (0, 1, 11, 12, 13, 23)] == [12, 1, 11, 12, 1, 11]
    system.clock_24h = True
    assert [system.display_hour(h) for h in (0, 12, 23)] == [0, 12, 23]


def test_the_settings_app_switches_the_clock_format(system):
    (system, path) = system
    from settings import SettingsApp
    app = SettingsApp()
    system.switch(app)
    app._sett_index = app._settings.index('Time Format')
    app._draw()
    (x, y, w) = app._cell(0, 2)

    app.touch((wasp.EventType.TOUCH, x + w // 2, y + 20))

    assert system.clock_24h is False
    system.switch(system.quick_ring[0])


@pytest.mark.parametrize('face', ('Clock', 'WeekClk'))
def test_the_digital_faces_draw_a_12_hour_clock(system, face):
    (system, path) = system
    system.clock_24h = False
    for (face_path, label) in appregistry.faces_list:
        if label == face:
            system.register(face_path, watch_face=True, name=label)
    system.switch(system.quick_ring[0])
    system.app._draw(True)

    clock = system.bar._clock
    clock.enabled = True
    clock.on_screen = None
    assert clock.update() is not None


def test_the_step_goal_is_kept(system):
    (system, path) = system
    system.step_goal = 6000

    manager = restart(path)

    assert manager.step_goal == 6000


def test_a_step_goal_not_offered_is_ignored(system):
    (system, path) = system
    path.write_text(json.dumps({'step_goal': 1234}))

    manager = restart(path)

    assert manager.step_goal == 10000


@pytest.mark.parametrize('x, step', ((60, -1), (180, 1)))
def test_the_settings_app_steps_the_step_goal(system, x, step):
    (system, path) = system
    from settings import SettingsApp
    app = SettingsApp()
    system.switch(app)
    app._sett_index = app._settings.index('Step Goal')
    app._draw()
    before = system.step_goal

    app.touch((wasp.EventType.TOUCH, x, 210))

    goals = wasp.STEP_GOALS
    assert system.step_goal == goals[(goals.index(before) + step) % len(goals)]
    system.switch(system.quick_ring[0])


@pytest.mark.parametrize('steps', (0, 4790, 20000))
def test_the_steps_page_shows_progress_to_the_goal(system, steps):
    (system, path) = system
    wasp.watch.accel._steps = steps
    system.switch([app for app in system.quick_ring if app.NAME == 'Steps'][0])
    system._tick()
    system.switch(system.quick_ring[0])
