# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson
"""Gadgetbridge/Bangle.js protocol

Currently implemented messages are:

 * t:"notify", id:int, src,title,subject,body,sender,tel:string - new
   notification
 * t:"notify-", id:int - delete notification
 * t:"alarm", d:[{h,m,on,rep},...] - replace the alarms, or read them back
   when d is left out
 * t:"find", n:bool - findDevice
 * t:"vibrate", n:int - buzz n times, 1 to 5
 * t:"weather", temp,hum,txt,wind,loc - weather report
 * t:"musicstate", state:"play/pause",position,shuffle,repeat - music
   play/pause/etc
 * t:"musicinfo", artist,album,track,dur,c(track count),n(track num) -
   currently playing music track
 * t:"call", cmd:"accept/incoming/outgoing/reject/start/end", name: "name", number: "+491234" - call
 * t:"settings", brightness,notify_level,units,blank_after,clock_24h,
   step_goal,launcher_style,theme,face - change the given settings, then reply with all of
   them
 * t:"steps", y,m,d:int - reply with that day's step counts
 * t:"status" - reply with the battery level, voltage, charging and steps
 * t:"http", id:string, resp|err:string - answer a request made by http()

The watch sends JSON lines back, each tagged with t: "settings", "alarm",
"steps", "status", "call" (n:"ACCEPT/REJECT/IGNORE"), "http" (url, id, and
method and body when not a plain GET), "music",
"findPhone" or "error".
"""

import io
import json
import sys
import wasp
import time

# JSON compatibility
null = None
true = True
false = False

# Requests made by http() that the phone has not answered yet, by id.
_http = {}
_http_id = 0

# How many unanswered requests are kept before the oldest is dropped.
_HTTP_PENDING = 8


def send(msg):
    """Send one message to the phone as a JSON line."""
    json.dump(msg, sys.stdout)
    sys.stdout.write('\r\n')


def _info(msg):
    send({'t': 'info', 'msg': msg})


def _error(msg):
    send({'t': 'error', 'msg': msg})


def http(url, callback, method='GET', body=None):
    """Ask the phone to fetch a URL, and call callback(resp, err) when it answers.

    Exactly one of resp and err is a string, the other is None. method is any
    HTTP method, and body is text sent with it.
    """
    global _http_id
    _http_id += 1
    key = str(_http_id)
    if len(_http) >= _HTTP_PENDING:
        del _http[str(min([int(k) for k in _http]))]
    _http[key] = callback
    msg = {'t': 'http', 'url': url, 'id': key}
    if method != 'GET':
        msg['method'] = method
    if body is not None:
        msg['body'] = body
    send(msg)


def _companion(task, cmd):
    """Handle a larger message in the companion module without keeping it loaded."""
    loaded = 'companion' in sys.modules
    import companion
    try:
        getattr(companion, task)(cmd)
    finally:
        if not loaded:
            del sys.modules['companion']


def _vibrate(n):
    """Buzz n short times, clamped to between one and five."""
    vibrator = wasp.watch.vibrator
    for i in range(max(1, min(5, int(n)))):
        if i:
            time.sleep_ms(150)
        vibrator.pulse(duty=50, ms=100)


def _call(cmd):
    """Show the call screen for an incoming call, and close it for anything else."""
    system = wasp.system
    if cmd.get('cmd') == 'incoming':
        from apps.system.call import CallApp
        app = CallApp(cmd.get('name', ''), cmd.get('number', ''))
        # The instance keeps its class, so the module itself need not stay loaded.
        wasp._unload('apps.system.call')
        system.wake()
        system.switch(app)
    elif type(system.app).__name__ == 'CallApp':
        system.switch(system.quick_ring[0])


def _answer(cmd):
    """Hand the phone's answer to the http() request it belongs to."""
    callback = _http.pop(str(cmd.get('id')), None)
    if not callback:
        return
    if 'err' in cmd:
        callback(None, str(cmd['err']))
    else:
        callback(str(cmd.get('resp', ''))[:1024], None)


def GB(cmd):
    task = cmd['t']
    del cmd['t']

    try:
        if task == 'find':
            wasp.watch.vibrator.pin(not cmd['n'])
        elif task == 'notify':
            id = cmd['id']
            del cmd['id']
            wasp.system.notify(id, cmd)
            wasp.watch.vibrator.pulse(ms=wasp.system.notify_duration)
        elif task == 'notify-':
            wasp.system.unnotify(cmd['id'])
        elif task == 'musicstate':
            wasp.system.toggle_music(cmd)
        elif task == 'musicinfo':
            wasp.system.set_music_info(cmd)
        elif task == 'weather':
            wasp.system.set_weather_info(cmd)
        elif task == 'vibrate':
            _vibrate(cmd.get('n', 1))
        elif task == 'call':
            _call(cmd)
        elif task == 'http':
            _answer(cmd)
        elif task in ('settings', 'alarm', 'steps', 'status'):
            _companion(task, cmd)
        else:
            pass
            #_info('Command "{}" is not implemented'.format(cmd))
    except Exception as e:
        msg = io.StringIO()
        sys.print_exception(e, msg)
        _error(msg.getvalue())
        msg.close()

def send_cmd(cmd = ''):
    print('\r')
    for i in range(0, len(cmd), 20):
        print(cmd[i: i + 20], end='')
        time.sleep(0.2)
    print(' ')
    print(' ')


class _Packages():
    """The package manager, imported for each call the phone makes and let go of afterwards."""

    def __getattr__(self, name):
        return lambda *args: wasp._pkgmgr(name, *args)


# Every main.py imports this module's names, so the companion app finds pkg there.
pkg = _Packages()
