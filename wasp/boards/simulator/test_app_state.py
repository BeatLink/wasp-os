"""What an application keeps when it is closed and opened again."""

import pytest

import wasp


@pytest.fixture
def system(monkeypatch):
    system = wasp.system
    if not system.app:
        system.secondary_init()
    touched = []

    def open_app(name):
        for ring in (system.quick_ring, system.launcher_ring):
            for entry in ring:
                if entry.NAME == name:
                    touched.append(entry)
                    system.switch(entry)
                    return entry
        raise LookupError(name)

    system.open_app = open_app
    yield system
    system.switch(system.quick_ring[0])
    for entry in touched:
        entry._app = None
        entry.state = None


def home(system):
    system.switch(system.quick_ring[0])


def test_a_running_timer_is_kept_and_a_stopped_one_is_not(system):
    entry = system.open_app('Timer')
    timer = system.app
    timer._start()
    home(system)

    assert entry._app is timer
    system.switch(entry)
    assert system.app is timer

    timer._stop()
    home(system)
    assert entry._app is None
    system.switch(entry)
    assert system.app is not timer


def test_a_timer_that_rings_by_itself_is_still_tracked(system):
    entry = system.open_app('Timer')
    timer = system.app
    timer._start()
    home(system)

    timer._alert()

    assert system.app is timer
    assert system.app_entry is entry
    home(system)
    assert entry._app is None


def test_the_stopwatch_keeps_counting_while_closed(system):
    entry = system.open_app('Stopclock')
    before = system.app
    before._timer.start()
    before.touch(None)
    splits = list(before._splits)
    home(system)

    assert entry._app is None
    system.switch(entry)
    after = system.app

    assert after is not before
    assert after._timer.started
    assert after._splits == splits
    after._timer.stop()


def test_the_calculator_keeps_what_was_typed(system):
    # Calc is not registered by default, so it gets an entry of its own here.
    entry = wasp.AppEntry('apps.user.calculator.CalculatorApp', 'Calc')
    system.switch(entry)
    system.app.output = '12+3'
    home(system)
    system.switch(entry)

    assert system.app.output == '12+3'


def test_a_closed_app_leaves_no_module_behind(system):
    import sys
    system.open_app('Timer')
    home(system)

    package = sys.modules.get('apps.user')
    assert 'apps.user.timer' not in sys.modules
    assert package is None or not hasattr(package, 'timer')
