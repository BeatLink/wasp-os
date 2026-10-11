"""Which widget and font modules stay loaded once an application is left."""

import sys

import pytest

import wasp
import widgets


@pytest.fixture
def system(monkeypatch):
    system = wasp.system
    if not system.app:
        system.secondary_init()
    # Other tests import apps directly, which can load stopwatch before start up records what is resident.
    monkeypatch.setattr(system, '_resident', [m for m in system._resident if m != 'widgets.stopwatch'])
    if 'widgets.stopwatch' in sys.modules:
        wasp._unload('widgets.stopwatch')
    widgets.__dict__.pop('Stopwatch', None)
    yield system
    system.switch(system.quick_ring[0])


def open_app(system, name):
    for ring in (system.quick_ring, system.launcher_ring):
        for entry in ring:
            if entry.NAME == name:
                system.switch(entry)
                return entry
    raise LookupError(name)


def test_a_widget_an_app_loaded_is_unloaded_when_it_is_left(system):
    open_app(system, 'Stopclock')
    assert 'widgets.stopwatch' in sys.modules

    system.switch(system.quick_ring[0])

    assert 'widgets.stopwatch' not in sys.modules
    assert 'Stopwatch' not in widgets.__dict__


def test_a_widget_loaded_again_still_works(system):
    open_app(system, 'Stopclock')
    system.switch(system.quick_ring[0])

    open_app(system, 'Stopclock')

    assert type(system.app._timer).__name__ == 'Stopwatch'


def test_the_widgets_loaded_at_start_up_stay_loaded(system):
    open_app(system, 'Settings')
    system.switch(system.quick_ring[0])

    for modname in ('widgets.checkbox', 'widgets.spinner', 'widgets.confirmation_view'):
        assert modname in sys.modules
    assert 'Spinner' in widgets.__dict__
