"""The button on the home screen and away from it."""

import pytest

import wasp


@pytest.fixture
def system(monkeypatch):
    system = wasp.system
    if not system.app:
        system.secondary_init()
    # The simulated battery drifts in and out of charging, which also wakes the watch.
    monkeypatch.setattr(wasp.watch.battery, 'charging', lambda: False)
    yield system
    system.wake()


def test_the_button_on_the_home_screen_turns_the_screen_off(system):
    system.switch(system.quick_ring[0])
    system._handle_button(True)
    assert not system.sleep_at


def test_the_button_in_an_app_goes_home_and_leaves_the_screen_on(system):
    system.switch(system.launcher)
    system._handle_button(True)
    assert system.sleep_at
    assert (system.app_entry or system.app) is system.quick_ring[0]
