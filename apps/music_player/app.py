# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson
# Copyright (C) 2020 Carlos Gil

"""Music Player for GadgetBridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. figure:: apps/music_player/screenshot.png
        :width: 179

        Screenshot of the Music Player application

Music Player Controller:

* Touch: play/pause
* Swipe UPDOWN: Volume down/up
* Swipe LEFTRIGHT: next/previous
"""

import wasp


from micropython import const
from gadgetbridge import send_cmd

# 2-bit RLE, generated from wasp/resources/play.png, 303 bytes
_PLAY = (
    b'\x02'
    b'HH'
    b'?\xff\x8f\xcd8\xd41\xd9.\xdc*\xe0&\xe4#\xd1'
    b'\x01\x02\xd2!\xcd\r\xce\x1f\xcb\x13\xcc\x1d\xca\x17\xcb\x1b'
    b'\xca\x1a\xca\x19\xc9\x1d\xca\x17\xc9 \xc9\x16\xc8"\xc8\x15'
    b'\xc8$\xc8\x14\xc7%\xc8\x13\xc8&\xc8\x11\xc8\x0c\xc4\x11'
    b'\x07\xc7\x11\xc7\r\xc6\x0f\x07\xc8\x10\xc7\r\xc7\x0e\x08\xc7'
    b'\x0f\xc7\x0e\xc9\x0c\t\xc7\x0e\xc7\x0e\xcb\n\t\xc7\x0e\xc7'
    b'\x0e\xcc\t\t\xc7\r\xc7\x0f\xce\x07\n\xc6\r\xc7\x0f\xd0'
    b'\x05\n\xc7\x0c\xc7\x0f\xd1\x04\n\xc7\x0c\xc7\x0f\xd3\x02\n'
    b'\xc7\x0c\xc7\x0f\xd4\x01\n\x01\xc6\x0c\xc6\x10\xd5\n\x01\xc6'
    b'\x0c\xc6\x10\xd6\n\xc6\x0c\xc6\x10\xd6\n\xc6\x0c\xc6\x10\xd5'
    b'\n\xc7\x0c\xc7\x0f\xd4\x01\n\xc7\x0c\xc7\x0f\xd3\x02\n\xc7'
    b'\x0c\xc7\x0f\xd1\x04\n\xc7\x0c\xc7\x0f\xd0\x05\n\xc7\x0c\xc7'
    b'\x0f\xce\x07\n\xc7\r\xc7\x0e\xcc\t\t\xc7\x0e\xc7\x0e\xcb'
    b'\n\t\xc7\x0e\xc7\x0e\xc9\x0c\t\xc7\x0f\xc7\r\xc7\x0e\x08'
    b'\xc7\x10\xc7\r\xc6\x0f\x08\xc7\x10\xc8\x0c\xc4\x11\x07\xc8\x11'
    b'\xc7\x0e\x02\x17\xc8\x12\xc8&\xc7\x14\xc8$\xc8\x15\xc8"'
    b'\xc8\x16\xc9 \xc9\x17\xc9\x1e\xc9\x19\xc9\x1b\xca\x1b\xca\x18'
    b'\xca\x1d\xcb\x14\xcb\x1f\xcd\x0e\xcd!\xd1\x04\xd1#\xe4&'
    b'\xe0)\xdd-\xda1\xd47\xce?\xff\x8f'
)

# 2-bit RLE, generated from wasp/resources/pause.png, 320 bytes
_PAUSE = (
    b'\x02'
    b'HH'
    b'?\xff\x8f\xcd8\xd41\xd9.\xdc*\xe0&\xe4#\xd1'
    b'\x03\xd2!\xcd\r\xce\x1f\xcb\x13\xcc\x1d\xca\x17\xcb\x1b\xca'
    b'\x1a\xca\x19\xc9\x1d\xca\x17\xc9 \xc9\x16\xc8"\xc8\x15\xc8'
    b'$\xc8\x14\xc7%\xc8\x13\xc8&\xc8\x11\xc8(\xc7\x11\xc7'
    b'\x0c\xc6\x06\xc6\x0b\xc8\x10\xc7\x0c\xc6\x06\xc6\x0c\xc7\x0f\xc7'
    b'\r\xc6\x06\xc6\r\xc7\x0e\xc7\r\xc6\x06\xc6\r\xc7\x0e\xc7'
    b'\r\xc6\x06\xc6\r\xc7\r\xc7\x0e\xc6\x06\xc6\x0e\xc6\r\xc7'
    b'\x0e\xc6\x06\xc6\x0e\xc7\x0c\xc7\x0e\xc6\x06\xc6\x0e\xc7\x0c\xc7'
    b'\x0e\xc6\x06\xc6\x0e\xc7\x0c\xc7\x0e\xc6\x06\xc6\x0e\xc7\x0c\xc6'
    b'\x0f\xc6\x06\xc6\x0f\xc6\x0c\xc6\x0f\xc6\x06\xc6\x0f\xc6\x0c\xc6'
    b'\x0f\xc6\x06\xc6\x0f\xc6\x0c\xc6\x0f\xc6\x06\xc6\x0f\xc6\x0c\xc7'
    b'\x0e\xc6\x06\xc6\x0e\xc7\x0c\xc7\x0e\xc6\x06\xc6\x0e\xc7\x0c\xc7'
    b'\x0e\xc6\x06\xc6\x0e\xc7\x0c\xc7\x0e\xc6\x06\xc6\x0e\xc7\x0c\xc7'
    b'\x0e\xc6\x06\xc6\x0e\xc7\r\xc7\r\xc6\x06\xc6\r\xc7\x0e\xc7'
    b'\r\xc6\x06\xc6\r\xc7\x0e\xc7\r\xc6\x06\xc6\r\xc7\x0f\xc7'
    b'\x0c\xc6\x06\xc6\x0c\xc7\x10\xc7\x0c\xc6\x06\xc6\x0c\xc7\x10\xc8'
    b"(\xc8\x11\xc7'\xc8\x12\xc8&\xc7\x14\xc8$\xc8\x15\xc8"
    b'"\xc8\x16\xc9 \xc9\x17\xc9\x1e\xc9\x19\xc9\x1b\xca\x1b\xca'
    b'\x18\xca\x1d\xcb\x14\xcb\x1f\xcd\x0e\xcd!\xd1\x04\xd1#\xe4'
    b'&\xe0)\xdd-\xda1\xd47\xce?\xff\x8f'
)

# 2-bit RLE, generated from wasp/resources/fwd.png, 93 bytes
_FWD = (
    b'\x02'
    b'0\x18'
    b'\xc4\x11\xc4\x11\xcc\x0f\xc6\x0f\xcd\x0e\xc7\x0e\xcf\x0c\xc9\x0c'
    b'\xd1\n\xcb\n\xd2\t\xcc\t\xd4\x07\xce\x07\xd6\x05\xd0\x05'
    b'\xd7\x04\xd1\x04\xd9\x02\xd3\x02\xda\x01\xd4\x01\xff;\x01\xd4'
    b'\x01\xd9\x02\xd3\x02\xd7\x04\xd1\x04\xd6\x05\xd0\x05\xd4\x07\xce'
    b'\x07\xd2\t\xcc\t\xd1\n\xcb\n\xcf\x0c\xc9\x0c\xcd\x0e\xc7'
    b'\x0e\xcc\x0f\xc6\x0f\xca\x11\xc4\x11\xc6'
)

# 2-bit RLE, generated from wasp/resources/back.png, 93 bytes
_BACK = (
    b'\x02'
    b'0\x18'
    b'\xc6\x11\xc4\x11\xca\x0f\xc6\x0f\xcc\x0e\xc7\x0e\xcd\x0c\xc9\x0c'
    b'\xcf\n\xcb\n\xd1\t\xcc\t\xd2\x07\xce\x07\xd4\x05\xd0\x05'
    b'\xd6\x04\xd1\x04\xd7\x02\xd3\x02\xd9\x01\xd4\x01\xff;\x01\xd4'
    b'\x01\xda\x02\xd3\x02\xd9\x04\xd1\x04\xd7\x05\xd0\x05\xd6\x07\xce'
    b'\x07\xd4\t\xcc\t\xd2\n\xcb\n\xd1\x0c\xc9\x0c\xcf\x0e\xc7'
    b'\x0e\xcd\x0f\xc6\x0f\xcc\x11\xc4\x11\xc4'
)

# 1-bit RLE, 32x32, generated from apps/music_player/icon.png, 99 bytes
icon = (
    32, 32,
    b'\x1d\x02\x1a\x07\x16\n\x13\r\x0f\x11\x0c\x14\t\x17\x08\x18'
    b'\x08\x18\x08\x18\x08\x10\x04\x04\x08\r\x07\x04\x08\n\n\x04'
    b'\x08\x06\x0e\x04\x08\x04\x10\x04\x08\x04\x10\x04\x08\x04\x10\x04'
    b'\x08\x04\x10\x04\x08\x04\x0c\x08\x08\x04\n\n\x08\x04\t\x0b'
    b'\x08\x04\x08\x0c\x04\x08\x08\x0c\x02\n\x08\x0c\x01\x0b\x08\x18'
    b'\t\n\x01\x0c\n\x08\x02\x0c\x0b\x06\x03\x0c\x15\n\x17\x08'
    b'\x19\x06\x17'
)

DISPLAY_WIDTH = const(240)
ICON_SIZE = const(72)
CENTER_AT = const((DISPLAY_WIDTH - ICON_SIZE) // 2)

class MusicPlayerApp(object):
    """ Music Player Controller application."""
    NAME = 'Music'
    ICON = icon

    def __init__(self):
        self._pauseplay = wasp.widgets.GfxButton(CENTER_AT, CENTER_AT, _PLAY)
        self._back = wasp.widgets.GfxButton(0, 120-12, _BACK)
        self._fwd = wasp.widgets.GfxButton(240-48, 120-12, _FWD)
        self._play_state = False
        self._musicstate = 'pause'
        self._artist = ''
        self._track = ''
        self._state_changed = True
        self._track_changed = True
        self._artist_changed = True

    def _fill_space(self, key):
        if key == 'top':
            wasp.watch.drawable.fill(
                x=0, y=0, w=DISPLAY_WIDTH, h=CENTER_AT)
        elif key == 'down':
            wasp.watch.drawable.fill(x=0, y=CENTER_AT + ICON_SIZE,
                                     w=DISPLAY_WIDTH,
                            h=DISPLAY_WIDTH - (CENTER_AT + ICON_SIZE))

    def foreground(self):
        """Activate the application."""
        state = wasp.system.musicstate.get('state')
        artist = wasp.system.musicinfo.get('artist')
        track = wasp.system.musicinfo.get('track')
        if state:
            self._musicstate = state
            if self._musicstate == 'play':
                self._play_state = True
            elif self._musicstate == 'pause':
                self._play_state = False
        if artist:
            self._artist = artist
        if track:
            self._track = track
        wasp.watch.drawable.fill()
        self.draw()
        wasp.system.request_tick(1000)
        wasp.system.request_event(wasp.EventMask.SWIPE_UPDOWN |
                                  wasp.EventMask.TOUCH)

    def background(self):
        """De-activate the application (without losing state)."""
        self._state_changed = True
        self._track_changed = True
        self._artist_changed = True

    def tick(self, ticks):
        wasp.system.keep_awake()
        music_state_now = wasp.system.musicstate.get('state')
        music_artist_now = wasp.system.musicinfo.get('artist')
        music_track_now = wasp.system.musicinfo.get('track')
        if music_state_now:
            if music_state_now != self._musicstate:
                self._musicstate = music_state_now
                self._state_changed = True
        else:
            self._state_changed = False
        wasp.system.musicstate = {}
        if music_track_now:
            if music_track_now != self._track:
                self._track = music_track_now
                self._track_changed = True
        else:
            self._track_changed = False
        if music_artist_now:
            if music_artist_now != self._artist:
                self._artist = music_artist_now
                self._artist_changed = True
        else:
            self._artist_changed = False
        wasp.system.musicinfo = {}
        self._update()

    def swipe(self, event):
        """
        Notify the application of a touchscreen swipe event.
        """
        if event[0] == wasp.EventType.UP:
            send_cmd('{"t":"music", "n":"volumeup"} ')
        elif event[0] == wasp.EventType.DOWN:
            send_cmd('{"t":"music", "n":"volumedown"} ')

    def touch(self, event):
        if self._pauseplay.touch(event):
            self._play_state = not self._play_state
            if self._play_state:
                self._musicstate = 'play'
                self._pauseplay.gfx = _PAUSE
                self._pauseplay.draw()
                send_cmd('{"t":"music", "n":"play"} ')
            else:
                self._musicstate = 'pause'
                self._pauseplay.gfx = _PLAY
                self._pauseplay.draw()
                send_cmd('{"t":"music", "n":"pause"} ')
        elif self._back.touch(event):
            send_cmd('{"t":"music", "n":"previous"} ')
        elif self._fwd.touch(event):
            send_cmd('{"t":"music", "n":"next"} ')

    def draw(self):
        """Redraw the display from scratch."""
        self._draw()

    def _draw(self):
        """Redraw the updated zones."""
        if self._state_changed:
            self._pauseplay.draw()
        if self._track_changed:
            self._draw_label(self._track, 24 + 144)
        if self._artist_changed:
            self._draw_label(self._artist, 12)
        self._back.draw()
        self._fwd.draw()

    def _draw_label(self, label, pos):
        """Redraw label info"""
        if label:
            draw = wasp.watch.drawable
            chunks = draw.wrap(label, 240)
            self._fill_space(pos)
            for i in range(len(chunks)-1):
                sub = label[chunks[i]:chunks[i+1]].rstrip()
                draw.string(sub, 0, pos + 24 * i, 240)

    def _update(self):
        if self._musicstate == 'play':
            self._play_state = True
            self._pauseplay.gfx = _PAUSE
        elif self._musicstate == 'pause':
            self._play_state = False
            self._pauseplay.gfx = _PLAY
        self._draw()

    def update(self):
        pass
