"""Saved alarms must ring after a restart, even though apps load lazily."""

import pytest

import wasp


@pytest.fixture
def system(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    system = wasp.system
    # Without the Alarm entry start up made, so the app finds the one each test registers.
    monkeypatch.setattr(system, 'launcher_ring',
                        [app for app in system.launcher_ring if app.NAME != 'Alarm'])
    before = list(system._alarms)
    yield system
    for (when, action) in list(system._alarms):
        if (when, action) not in before:
            system.cancel_alarm(when, action)


def register_alarm(system):
    system.register('apps.user.alarm.AlarmApp', name='Alarm')
    return [app for app in system.launcher_ring if app.NAME == 'Alarm'][-1]


def test_a_switched_on_alarm_is_scheduled_at_start_up(tmp_path, system):
    (tmp_path / 'alarms.txt').write_text('7,30,194;')

    entry = register_alarm(system)

    # The app is built to schedule the alarm and then let go: the scheduler holds the entry.
    assert entry._app is None
    assert [t for (t, a) in system._alarms if a is entry]


def test_a_pending_alarm_brings_the_app_up_ringing(tmp_path, system):
    (tmp_path / 'alarms.txt').write_text('7,30,194;')
    entry = register_alarm(system)
    (when, action) = [alarm for alarm in system._alarms if alarm[1] is entry][0]
    system.cancel_alarm(when, action)

    action()

    assert type(system.app).__name__ == 'AlarmApp'
    assert system.app.page == -2
    system.switch(system.quick_ring[0])


def test_building_the_app_again_schedules_nothing_twice(tmp_path, system):
    (tmp_path / 'alarms.txt').write_text('7,30,194;')
    entry = register_alarm(system)
    entry.load()
    entry.load()

    assert len([t for (t, a) in system._alarms if a is entry]) == 1


def test_without_an_alarm_switched_on_the_app_stays_unbuilt(tmp_path, system):
    (tmp_path / 'alarms.txt').write_text('7,30,66;')

    entry = register_alarm(system)

    assert entry._app is None


def test_snoozing_queues_the_entry_and_frees_the_app(tmp_path, system):
    (tmp_path / 'alarms.txt').write_text('7,30,194;')
    entry = register_alarm(system)
    (when, action) = [alarm for alarm in system._alarms if alarm[1] is entry][0]
    system.cancel_alarm(when, action)
    action()

    system.app.touch(None)

    assert type(system.app).__name__ != 'AlarmApp'
    assert entry._app is None
    assert len([t for (t, a) in system._alarms if a is entry]) == 2
