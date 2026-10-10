"""Waking the watch with a wrist raise or a double tap."""

import json

import pytest

import wasp


@pytest.fixture
def system(tmp_path, monkeypatch):
    system = wasp.system
    if not system.app:
        system.secondary_init()
    path = tmp_path / 'settings.json'
    monkeypatch.setattr(system, 'settings_file', str(path))
    monkeypatch.setattr(system, '_settings_text', system._settings())
    # The simulated battery drifts in and out of charging, which also wakes the watch.
    monkeypatch.setattr(wasp.watch.battery, 'charging', lambda: False)
    yield system, path
    system.wake_on_raise = False
    system.wake_on_tap = False
    wasp.watch.accel.gesture = False
    system.wake()


def asleep(system):
    system.sleep()
    assert not system.sleep_at


def test_changing_a_setting_reaches_the_accelerometer(system):
    (system, path) = system
    system.wake_on_raise = True
    assert wasp.watch.accel.wake_on == (True, False)
    system.wake_on_tap = True
    assert wasp.watch.accel.wake_on == (True, True)


def test_the_gestures_are_kept_and_reapplied_at_start_up(system):
    (system, path) = system
    system.wake_on_tap = True
    assert json.loads(path.read_text())['wake_on_tap'] is True

    manager = wasp.Manager()
    manager.settings_file = str(path)
    manager.register_defaults()
    wasp.watch.accel.wake_on = (False, False)
    manager._load_settings()
    manager._apply_wake()

    assert manager.wake_on_tap is True
    assert wasp.watch.accel.wake_on == (False, True)


def test_a_raise_wakes_a_sleeping_watch(system):
    (system, path) = system
    system.wake_on_raise = True
    asleep(system)

    wasp.watch.accel.gesture = True
    system._tick()

    assert system.sleep_at


def test_nothing_wakes_the_watch_without_a_gesture(system):
    (system, path) = system
    system.wake_on_raise = True
    asleep(system)

    system._tick()

    assert not system.sleep_at


def test_a_gesture_is_ignored_when_both_are_off(system):
    (system, path) = system
    asleep(system)

    wasp.watch.accel.gesture = True
    system._tick()

    assert not system.sleep_at
