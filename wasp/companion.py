# SPDX-License-Identifier: LGPL-3.0-or-later
"""Companion app messages
~~~~~~~~~~~~~~~~~~~~~~~~~

Handles the Gadgetbridge messages that read and change the watch's settings,
its alarms and its step history. Each reply is one JSON line tagged with the
message's own name.

These are rare and larger than the other messages, so gadgetbridge.py imports
this module for each one and lets go of it afterwards.
"""

import json
import sys

import appregistry
import wasp
from gadgetbridge import _error, send

# The settings that take one value from a fixed list, with that list.
_CHOICES = (
    ('brightness', (1, 2, 3)),
    ('notify_level', (1, 2, 3)),
    ('units', ('Metric', 'Imperial')),
    ('blank_after', wasp.BLANK_AFTER),
    ('step_goal', wasp.STEP_GOALS),
)

# The most alarms the alarm app holds.
_MAX_ALARMS = 12

# The alarm app's flag for a switched on alarm; the low seven bits are its days.
_IS_ACTIVE = 0x80


def _faces():
    """List every watch face as [path, label], built in ones first, then packages."""
    faces = [list(face) for face in appregistry.faces_list]
    for face in wasp.packages('face'):
        faces.append(['pkg.{}.app.{}'.format(face['name'], face['cls']),
                      face.get('label', face['name'])])
    return faces


def _set_face(path, label):
    """Make a face the watch face as the Faces app does, showing it if the old one was showing."""
    system = wasp.system
    old = system.quick_ring[0]
    if isinstance(old, wasp.AppEntry) and old.path == path:
        return
    showing = system.app_entry is old or system.app is old
    system.register(path, watch_face=True, name=label)
    if showing:
        system.switch(system.quick_ring[0])


def _apply(key, value, faces):
    """Apply one setting, returning False if the value is not one it can take."""
    system = wasp.system
    for (name, allowed) in _CHOICES:
        if key == name:
            # True equals 1 in Python, so the type is checked as well as the value.
            if type(value) is not type(allowed[0]) or value not in allowed:
                return False
            setattr(system, key, value)
            return True
    if key == 'clock_24h':
        if value is not True and value is not False:
            return False
        system.clock_24h = value
    elif key == 'theme':
        if not isinstance(value, list) or len(value) != len(system._theme):
            return False
        for part in value:
            if type(part) is not int or part < 0 or part > 255:
                return False
        system.set_theme(bytes(value))
    elif key == 'face':
        for face in faces:
            if face[0] == value:
                _set_face(face[0], face[1])
                return True
        return False
    else:
        return False
    return True


def settings(cmd):
    """Apply the settings given, then reply with every setting and the faces on offer."""
    system = wasp.system
    faces = _faces()
    for key in cmd:
        if not _apply(key, cmd[key], faces):
            _error('bad setting {}: {}'.format(key, cmd[key]))
    face = system.quick_ring[0]
    send({
        't': 'settings',
        'brightness': system.brightness,
        'notify_level': system.notify_level,
        'units': system.units,
        'blank_after': system.blank_after,
        'clock_24h': system.clock_24h,
        'step_goal': system.step_goal,
        'theme': list(system._theme),
        'face': face.path if isinstance(face, wasp.AppEntry) else None,
        'faces': faces,
    })


def _alarm_entry():
    """Find the alarm app's entry, or None if it is not registered."""
    system = wasp.system
    for ring in (system.quick_ring, system.launcher_ring):
        for entry in ring:
            if isinstance(entry, wasp.AppEntry) and entry.path.endswith('.AlarmApp'):
                return entry
    return None


def _read_alarms():
    """Read alarms.txt as (hour, minute, flags) triples."""
    alarms = []
    try:
        with open('alarms.txt') as f:
            text = f.read()
        for alarm in text.split(';'):
            fields = alarm.split(',')
            if len(fields) == 3:
                alarms.append((int(fields[0]), int(fields[1]), int(fields[2])))
    except (OSError, ValueError):
        pass
    return alarms[:_MAX_ALARMS]


def _parse_alarms(d):
    """Turn the phone's alarm list into (hour, minute, flags) triples, or None if any is wrong."""
    if not isinstance(d, list) or len(d) > _MAX_ALARMS:
        return None
    alarms = []
    for alarm in d:
        if not isinstance(alarm, dict):
            return None
        h = alarm.get('h')
        m = alarm.get('m')
        on = alarm.get('on', True)
        rep = alarm.get('rep', 0)
        if type(h) is not int or type(m) is not int or type(rep) is not int \
                or not 0 <= h < 24 or not 0 <= m < 60 or not 0 <= rep < 128 \
                or (on is not True and on is not False):
            return None
        alarms.append((h, m, rep | (_IS_ACTIVE if on else 0)))
    return alarms


def _fill(app, alarms):
    """Copy alarms into a built alarm app's list."""
    for (n, alarm) in enumerate(alarms):
        slot = app.alarms[n]
        slot[0] = alarm[0]
        slot[1] = alarm[1]
        slot[2] = alarm[2]
    app.num_alarms = len(alarms)


def _replace_alarms(alarms):
    """Store a new alarm list and schedule it, whether or not the alarm app is built."""
    system = wasp.system
    entry = _alarm_entry()
    app = system.app if type(system.app).__name__ == 'AlarmApp' else None
    built = app or (entry and entry._app)
    if built and hasattr(built, 'set_alarms'):
        # The alarm app stores, schedules and redraws its own list where it offers to.
        built.set_alarms(alarms)
        return
    if app:
        # A foreground alarm app has nothing scheduled; it schedules its list as it is left.
        _fill(app, alarms)
        if app.page != -2:
            app.draft = False
            app.page = -1
            app.step = 0
            app.scroll = 0
            app._draw()
    elif entry and entry._app:
        app = entry._app
        app._deactivate_pending_alarms()
        _fill(app, alarms)
        app._set_pending_alarms()
    elif entry:
        system.cancel_alarm(None, entry)

    with open('alarms.txt', 'w') as f:
        for alarm in alarms:
            f.write('{},{},{};'.format(alarm[0], alarm[1], alarm[2]))

    # An unbuilt app schedules its alarms as it is built, which is how start up arms them too.
    if not app and entry:
        for alarm in alarms:
            if alarm[2] & _IS_ACTIVE:
                entry.load()
                break


def alarm(cmd):
    """Replace the alarms if a list is given, then reply with the alarms as they stand."""
    if 'd' in cmd:
        alarms = _parse_alarms(cmd['d'])
        if alarms is None:
            _error('bad alarm list')
            return
        _replace_alarms(alarms)
    else:
        app = wasp.system.app
        if type(app).__name__ == 'AlarmApp':
            alarms = [tuple(app.alarms[n]) for n in range(app.num_alarms)]
        else:
            alarms = _read_alarms()
    send({'t': 'alarm', 'd': [
        {'h': a[0], 'm': a[1], 'on': bool(a[2] & _IS_ACTIVE), 'rep': a[2] & 0x7f}
        for a in alarms]})


def steps(cmd):
    """Reply with one day's step counts, written a value at a time rather than built as a list."""
    (y, m, d) = (int(cmd['y']), int(cmd['m']), int(cmd['d']))
    logger = getattr(wasp.system, 'steps', None)
    data = logger.data((y, m, d)) if logger else None
    try:
        now = wasp.watch.accel.steps
    except Exception:
        now = None

    write = sys.stdout.write
    write('{"t": "steps", "y": %d, "m": %d, "d": %d, "v": ' % (y, m, d))
    if data is None:
        write('null')
    else:
        write('[')
        first = True
        for value in data:
            write(('%d' if first else ', %d') % value)
            first = False
        data.close()
        write(']')
    write(', "now": ')
    write(json.dumps(now))
    write('}\r\n')
