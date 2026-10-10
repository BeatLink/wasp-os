"""The companion app's messages: settings, alarms, steps, calls, files, http and vibrate."""

import base64
import gc
import json
import sys

import pytest

import wasp
import appregistry
import gadgetbridge
from gadgetbridge import GB


@pytest.fixture
def flash(tmp_path, monkeypatch):
    """Stand a temporary directory in for /flash."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def system(monkeypatch):
    system = wasp.system
    if not system.app:
        system.secondary_init()
    saved = (system._brightness, system._notifylevel, system._nfylev_ms, system._units,
             system._theme, system._blank_after, system._clock_24h, system._step_goal)
    monkeypatch.setattr(system, 'quick_ring', list(system.quick_ring))
    monkeypatch.setattr(system, 'launcher_ring', list(system.launcher_ring))
    before = list(system._alarms)
    system.switch(system.quick_ring[0])
    yield system
    (system._brightness, system._notifylevel, system._nfylev_ms, system._units,
     system._theme, system._blank_after, system._clock_24h, system._step_goal) = saved
    for alarm in list(system._alarms):
        if alarm not in before:
            system._alarms.remove(alarm)
    system.switch(system.quick_ring[0])


def lines(capsys):
    """Parse the JSON lines written to the phone since the last call, skipping the simulator's own output."""
    out = capsys.readouterr().out
    return [json.loads(line) for line in out.splitlines() if line.startswith('{')]


def gb(capsys, msg):
    capsys.readouterr()
    GB(json.loads(json.dumps(msg)))
    return lines(capsys)


SETTINGS_KEYS = {'t', 'brightness', 'notify_level', 'units', 'blank_after', 'clock_24h',
                 'step_goal', 'theme', 'face', 'faces'}


def test_settings_read_replies_with_every_setting(system, capsys):
    (reply,) = gb(capsys, {'t': 'settings'})

    assert set(reply) == SETTINGS_KEYS
    assert reply['brightness'] == system.brightness
    assert reply['theme'] == list(system._theme)
    assert reply['face'] == system.quick_ring[0].path
    assert [list(face) for face in appregistry.faces_list] == reply['faces'][:len(appregistry.faces_list)]


def test_settings_write_applies_each_key(system, capsys):
    theme = list(range(len(system._theme)))
    (face, label) = appregistry.faces_list[-1]

    (reply,) = gb(capsys, {'t': 'settings', 'brightness': 1, 'notify_level': 3,
                           'units': 'Imperial', 'blank_after': 30, 'clock_24h': False,
                           'step_goal': 8000, 'theme': theme, 'face': face})

    assert (system.brightness, system.notify_level, system.units) == (1, 3, 'Imperial')
    assert (system.blank_after, system.clock_24h, system.step_goal) == (30, False, 8000)
    assert list(system._theme) == theme
    assert system.quick_ring[0].path == face and system.quick_ring[0].NAME == label
    assert reply['face'] == face
    assert (reply['units'], reply['clock_24h'], reply['step_goal']) == ('Imperial', False, 8000)


def test_a_bad_setting_is_reported_and_the_rest_applied(system, capsys):
    brightness = system.brightness

    replies = gb(capsys, {'t': 'settings', 'brightness': True, 'units': 'Imperial',
                          'face': 'faces.gone.GoneApp', 'theme': [1, 2]})

    assert [r['t'] for r in replies] == ['error', 'error', 'error', 'settings']
    assert system.brightness == brightness
    assert system.units == 'Imperial'


def test_changing_the_showing_face_shows_the_new_one(system, capsys):
    (face, label) = [f for f in appregistry.faces_list if f[0] != system.quick_ring[0].path][0]

    gb(capsys, {'t': 'settings', 'face': face})

    assert system.app_entry is system.quick_ring[0]
    assert type(system.app).__name__ == face.rsplit('.', 1)[1]


def alarm_entry(system):
    return [e for e in system.launcher_ring if getattr(e, 'path', '').endswith('.AlarmApp')][0]


def test_alarm_read_reports_the_saved_alarms(flash, system, capsys):
    (flash / 'alarms.txt').write_text('7,30,159;22,5,0;')

    (reply,) = gb(capsys, {'t': 'alarm'})

    assert reply == {'t': 'alarm', 'd': [{'h': 7, 'm': 30, 'on': True, 'rep': 31},
                                        {'h': 22, 'm': 5, 'on': False, 'rep': 0}]}


def test_alarm_replace_saves_and_schedules(flash, system, capsys):
    entry = alarm_entry(system)

    (reply,) = gb(capsys, {'t': 'alarm', 'd': [{'h': 6, 'm': 45, 'rep': 31}, {'h': 9, 'm': 0}]})

    assert (flash / 'alarms.txt').read_text() == '6,45,159;9,0,128;'
    assert reply['d'] == [{'h': 6, 'm': 45, 'on': True, 'rep': 31},
                          {'h': 9, 'm': 0, 'on': True, 'rep': 0}]
    assert entry._app is None
    assert len([t for (t, a) in system._alarms if a is entry]) == 2


def test_alarm_replace_cancels_the_old_alarms(flash, system, capsys):
    entry = alarm_entry(system)
    gb(capsys, {'t': 'alarm', 'd': [{'h': 6, 'm': 45}, {'h': 7, 'm': 0}]})

    gb(capsys, {'t': 'alarm', 'd': [{'h': 8, 'm': 15, 'on': False}]})

    assert [t for (t, a) in system._alarms if a is entry] == []
    assert (flash / 'alarms.txt').read_text() == '8,15,0;'


def test_an_empty_alarm_list_clears_the_file(flash, system, capsys):
    entry = alarm_entry(system)
    gb(capsys, {'t': 'alarm', 'd': [{'h': 6, 'm': 45}]})

    (reply,) = gb(capsys, {'t': 'alarm', 'd': []})

    assert reply == {'t': 'alarm', 'd': []}
    assert (flash / 'alarms.txt').read_text() == ''
    assert [t for (t, a) in system._alarms if a is entry] == []


def test_too_many_alarms_are_refused(flash, system, capsys):
    (reply,) = gb(capsys, {'t': 'alarm', 'd': [{'h': 1, 'm': 0}] * 13})

    assert reply['t'] == 'error'
    assert not (flash / 'alarms.txt').exists()


def test_alarm_replace_updates_a_showing_alarm_app(flash, system, capsys):
    entry = alarm_entry(system)
    system.switch(entry)

    gb(capsys, {'t': 'alarm', 'd': [{'h': 5, 'm': 10, 'rep': 96}]})

    app = system.app
    assert (app.num_alarms, bytes(app.alarms[0])) == (1, bytes((5, 10, 96 | 0x80)))
    (reply,) = gb(capsys, {'t': 'alarm'})
    assert reply['d'] == [{'h': 5, 'm': 10, 'on': True, 'rep': 96}]
    # Leaving the app schedules what the phone sent.
    system.switch(system.quick_ring[0])
    assert len([t for (t, a) in system._alarms if a is entry]) == 1


@pytest.fixture
def accel(monkeypatch):
    """Hold the simulated step count still, since reading it normally makes it grow."""
    monkeypatch.setattr(type(wasp.watch.accel), 'steps', property(lambda self: 1234))


def test_steps_reply_has_240_values(flash, system, capsys, accel):
    (flash / 'logs' / '2026').mkdir(parents=True)
    counts = list(range(240))
    (flash / 'logs' / '2026' / '01-02.steps').write_bytes(
        b''.join(c.to_bytes(2, 'little') for c in counts))

    (reply,) = gb(capsys, {'t': 'steps', 'y': 2026, 'm': 1, 'd': 2})

    assert reply == {'t': 'steps', 'y': 2026, 'm': 1, 'd': 2, 'v': counts,
                     'now': 1234}


def test_steps_for_a_day_with_no_log_is_null(flash, system, capsys, accel):
    (reply,) = gb(capsys, {'t': 'steps', 'y': 2020, 'm': 1, 'd': 1})

    assert reply['v'] is None
    assert reply['now'] == 1234


def pkg(capsys, call, *args):
    capsys.readouterr()
    getattr(gadgetbridge.pkg, call)(*args)
    return lines(capsys)


def test_ls_dir_lists_names_sizes_and_directories(flash, capsys):
    (flash / 'logs').mkdir()
    (flash / 'logs' / 'a.txt').write_text('hello')
    (flash / 'logs' / '2026').mkdir()

    (reply,) = pkg(capsys, 'ls_dir', 'logs')

    assert (reply['t'], reply['ok'], reply['dir']) == ('pkg', True, 'logs')
    assert sorted(reply['entries']) == [['2026', 0, True], ['a.txt', 5, False]]
    assert 'pkgmgr' not in sys.modules


def test_ls_dir_of_the_root_and_of_nothing(flash, capsys):
    (flash / 'settings.json').write_text('{}')

    (root,) = pkg(capsys, 'ls_dir', '')
    (missing,) = pkg(capsys, 'ls_dir', 'nowhere')

    assert root['entries'] == [['settings.json', 2, False]]
    assert missing['ok'] is False


def test_send_streams_a_file_in_base64(flash, capsys):
    data = bytes(range(256)) * 2
    (flash / 'settings.json').write_bytes(data)

    replies = pkg(capsys, 'send', 'settings.json')

    assert replies[0] == {'t': 'pkg', 'ok': True, 'tx': len(data)}
    chunks = replies[1:-1]
    assert [c['off'] for c in chunks] == [0, 192, 384]
    assert b''.join(base64.b64decode(c['d']) for c in chunks) == data
    assert replies[-1] == {'t': 'pkg', 'ok': True, 'got': len(data), 'sum': sum(data)}


def test_send_a_missing_file_fails(flash, capsys):
    (reply,) = pkg(capsys, 'send', 'nothing.txt')

    assert reply['ok'] is False and reply['err']


def test_rm_file_deletes_one_file(flash, capsys):
    (flash / 'alarms.txt').write_text('7,30,128;')

    (reply,) = pkg(capsys, 'rm_file', 'alarms.txt')
    (again,) = pkg(capsys, 'rm_file', 'alarms.txt')

    assert reply == {'t': 'pkg', 'ok': True, 'deleted': 'alarms.txt'}
    assert not (flash / 'alarms.txt').exists()
    assert again['ok'] is False


@pytest.mark.parametrize('call,args', [('ls_dir', ('../x',)), ('send', ('/etc/passwd',)),
                                       ('rm_file', ('a/../b',)), ('recv', ('/x', 4, True))])
def test_paths_outside_flash_are_refused(flash, capsys, call, args):
    (reply,) = pkg(capsys, call, *args)

    assert reply == {'t': 'pkg', 'ok': False, 'err': 'bad path'}


def test_mem_reports_the_heap(flash, capsys, monkeypatch):
    monkeypatch.setattr(gc, 'mem_free', lambda: 19152, raising=False)
    monkeypatch.setattr(gc, 'mem_alloc', lambda: 40000, raising=False)

    (reply,) = pkg(capsys, 'mem')

    assert reply == {'t': 'pkg', 'ok': True, 'free': 19152, 'alloc': 40000}


def test_recv_restores_a_file_outside_pkg(flash, capsys, monkeypatch):
    payload = b'{"brightness": 1}'
    encoded = iter([base64.b64encode(payload).decode()])
    monkeypatch.setattr('builtins.input', lambda: next(encoded))

    replies = pkg(capsys, 'recv', 'settings.json', len(payload), True)

    assert (flash / 'settings.json').read_bytes() == payload
    assert replies[-1] == {'t': 'pkg', 'ok': True, 'got': len(payload), 'sum': sum(payload)}


@pytest.fixture
def http(monkeypatch):
    monkeypatch.setattr(gadgetbridge, '_http', {})
    return gadgetbridge


def test_http_round_trip(http, capsys):
    answers = []

    http.http('https://example.org/a', lambda resp, err: answers.append((resp, err)))
    (request,) = lines(capsys)
    gb(capsys, {'t': 'http', 'id': '0', 'resp': 'ignored'})
    gb(capsys, {'t': 'http', 'id': request['id'], 'resp': 'x' * 2000})

    assert (request['t'], request['url']) == ('http', 'https://example.org/a')
    assert answers == [('x' * 1024, None)]
    assert http._http == {}


def test_http_error_reaches_the_callback(http, capsys):
    answers = []
    http.http('https://example.org/b', lambda resp, err: answers.append((resp, err)))
    (request,) = lines(capsys)

    gb(capsys, {'t': 'http', 'id': request['id'], 'err': 'timeout'})

    assert answers == [(None, 'timeout')]


def test_http_keeps_only_eight_requests(http, capsys):
    for i in range(9):
        http.http('https://example.org/{}'.format(i), lambda resp, err: None)
    requests = lines(capsys)

    assert len(http._http) == 8
    assert requests[0]['id'] not in http._http
    assert requests[-1]['id'] in http._http


def test_an_incoming_call_shows_then_end_closes(system, capsys, monkeypatch):
    pulses = []
    monkeypatch.setattr(wasp.watch.vibrator, 'pulse', lambda **kw: pulses.append(kw))

    gb(capsys, {'t': 'call', 'cmd': 'incoming', 'name': 'Alex', 'number': '+44123'})

    assert type(system.app).__name__ == 'CallApp'
    assert 'apps.system.call' not in sys.modules
    assert pulses
    gb(capsys, {'t': 'call', 'cmd': 'end'})
    assert system.app_entry is system.quick_ring[0]


@pytest.mark.parametrize('x,answer', [(60, 'REJECT'), (180, 'ACCEPT')])
def test_a_call_tile_answers_the_phone(system, capsys, monkeypatch, x, answer):
    monkeypatch.setattr(wasp.watch.vibrator, 'pulse', lambda **kw: None)
    gb(capsys, {'t': 'call', 'cmd': 'incoming', 'name': '', 'number': '+44123'})

    system.app.touch([wasp.EventType.TOUCH, x, 200])

    assert lines(capsys) == [{'t': 'call', 'n': answer}]
    assert system.app_entry is system.quick_ring[0]


def test_the_button_ignores_a_call(system, capsys, monkeypatch):
    monkeypatch.setattr(wasp.watch.vibrator, 'pulse', lambda **kw: None)
    gb(capsys, {'t': 'call', 'cmd': 'incoming', 'name': 'Alex', 'number': ''})

    system.app.press(wasp.EventType.HOME, True)

    assert lines(capsys) == [{'t': 'call', 'n': 'IGNORE'}]
    assert system.app_entry is system.quick_ring[0]


@pytest.mark.parametrize('n,buzzes', [(3, 3), (0, 1), (99, 5)])
def test_vibrate_buzzes_n_times(monkeypatch, capsys, n, buzzes):
    pulses = []
    monkeypatch.setattr(wasp.watch.vibrator, 'pulse', lambda **kw: pulses.append(kw))
    monkeypatch.setattr(gadgetbridge.time, 'sleep_ms', lambda ms: None)

    assert gb(capsys, {'t': 'vibrate', 'n': n}) == []

    assert len(pulses) == buzzes
