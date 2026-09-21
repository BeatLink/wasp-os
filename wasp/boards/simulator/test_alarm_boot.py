"""Saved alarms must ring after a restart, even though apps load lazily."""

import pytest

import wasp


@pytest.fixture
def system(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    system = wasp.system
    monkeypatch.setattr(system, 'launcher_ring', list(system.launcher_ring))
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

    assert entry._app is not None
    assert [a for (t, a) in system._alarms if a == entry._app._alert]


def test_without_an_alarm_switched_on_the_app_stays_unbuilt(tmp_path, system):
    (tmp_path / 'alarms.txt').write_text('7,30,66;')

    entry = register_alarm(system)

    assert entry._app is None
