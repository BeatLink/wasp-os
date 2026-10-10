"""Waking the watch with a wrist raise or a double tap."""

import json

import pytest

import wasp
from wristraise import WristRaise

# Readings in the driver's axes: lying flat, then rolled towards the face.
FLAT = (0, 0, -1024)
RAISED = (0, 900, -490)


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
    wasp.watch.accel.xyz = (0, 0, 0)
    wasp.watch.touch.reset_touch_data()
    system.wake()


def asleep(system):
    system.sleep()
    # The simulator presses the button as the backlight goes off, which would wake it at once.
    system._button.get_event()
    assert not system.sleep_at


def tick_with(system, xyz):
    """Run one sleeping tick with the accelerometer reading ``xyz``."""
    wasp.watch.accel.xyz = xyz
    # The detector reads ten times a second; a test does not wait for that.
    system._sample_at = 0
    system._tick()


def test_the_gestures_are_kept_and_reloaded(system):
    (system, path) = system
    system.wake_on_tap = True
    assert json.loads(path.read_text())['wake_on_tap'] is True

    manager = wasp.Manager()
    manager.settings_file = str(path)
    manager.register_defaults()
    manager._load_settings()

    assert manager.wake_on_tap is True
    assert manager.wake_on_raise is False


def test_a_raise_wakes_a_sleeping_watch(system):
    (system, path) = system
    system.wake_on_raise = True
    asleep(system)

    for xyz in (FLAT,) * 6 + (RAISED,):
        tick_with(system, xyz)
        assert not system.sleep_at
    tick_with(system, RAISED)

    assert system.sleep_at


def test_a_still_wrist_leaves_the_watch_asleep(system):
    (system, path) = system
    system.wake_on_raise = True
    asleep(system)

    for _ in range(16):
        tick_with(system, FLAT)

    assert not system.sleep_at


def test_a_raise_is_ignored_when_raise_to_wake_is_off(system):
    (system, path) = system
    asleep(system)

    for xyz in (FLAT,) * 6 + (RAISED,) * 2:
        tick_with(system, xyz)

    assert not system.sleep_at


def test_the_touch_screen_listens_for_double_taps_only_when_asked(system, monkeypatch):
    (system, path) = system
    asked = []
    monkeypatch.setattr(wasp.watch.touch, 'sleep', lambda double_tap=False: asked.append(double_tap))

    asleep(system)
    system.wake()
    system.wake_on_tap = True
    asleep(system)

    assert asked == [False, True]


def test_a_double_tap_wakes_a_sleeping_watch(system):
    (system, path) = system
    system.wake_on_tap = True
    asleep(system)

    wasp.watch.touch.event[0] = 0x0b
    system._tick()

    assert system.sleep_at


def test_a_single_tap_leaves_the_watch_asleep_and_is_dropped(system):
    (system, path) = system
    system.wake_on_tap = True
    asleep(system)

    wasp.watch.touch.event[0] = 5
    system._tick()

    assert not system.sleep_at
    assert wasp.watch.touch.get_event() is None


def test_a_swinging_arm_is_not_a_raise():
    detector = WristRaise()
    # Driver axes turned to InfiniTime's, as the system does, swinging between two poses.
    swing = ((0, 0, -1024), (0, -900, -490))
    assert not any(detector.sample(x, -y, z) for _ in range(8) for (x, y, z) in swing)


def test_a_raise_with_the_arm_pointing_down_is_not_a_raise():
    detector = WristRaise()
    readings = [(900, 0, -500)] * 6 + [(900, -900, -490)] * 2
    assert not any(detector.sample(*r) for r in readings)
