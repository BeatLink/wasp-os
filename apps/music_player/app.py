# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson
# Copyright (C) 2020 Carlos Gil

"""Music Player for GadgetBridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. figure:: apps/music_player/screenshot.png
        :width: 179

        Screenshot of the Music Player application

The artist and track sit on the top card, over a row of three cards that
skip back, play or pause, and skip forward.

* Touch a card: previous, play/pause or next
* Swipe UPDOWN: Volume up/down
"""

import wasp
import cards
import fonts

from micropython import const
from gadgetbridge import send_cmd

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

# A tall card for the artist and track over a row of three control cards.
_KEY_H = cards.size(3)
_INFO_H = cards.SPAN - _KEY_H - cards.GAP
_INFO_Y, _KEY_Y = cards.edges((_INFO_H, _KEY_H))
_KEY_W = cards.size(3)
_KEY_X = cards.edges((_KEY_W,) * 3)
# Text keeps clear of the rounded corners of the top card.
_TEXT_X = const(16)
_TEXT_W = const(208)
_TRACK_LINES = const(4)

class MusicPlayerApp(object):
    """ Music Player Controller application."""
    NAME = 'Music'
    ICON = icon

    def __init__(self):
        self._play_state = False
        self._musicstate = 'pause'
        self._artist = ''
        self._track = ''
        self._state_changed = True
        self._track_changed = True
        self._artist_changed = True

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
        wasp.watch.drawable.fill(0)
        self._draw_info()
        for i in range(3):
            self._draw_key(i)
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
        if event[2] < _KEY_Y:
            return
        if event[1] < _KEY_X[1]:
            send_cmd('{"t":"music", "n":"previous"} ')
        elif event[1] < _KEY_X[2]:
            self._play_state = not self._play_state
            if self._play_state:
                self._musicstate = 'play'
                send_cmd('{"t":"music", "n":"play"} ')
            else:
                self._musicstate = 'pause'
                send_cmd('{"t":"music", "n":"pause"} ')
            self._draw_key(1)
        else:
            send_cmd('{"t":"music", "n":"next"} ')

    def draw(self):
        """Redraw the display from scratch."""
        self._draw()

    def _draw(self):
        """Redraw the cards whose contents changed."""
        if self._state_changed:
            self._draw_key(1)
        if self._track_changed or self._artist_changed:
            self._draw_info()

    def _draw_info(self):
        """Draw the artist in grey above the wrapped track title, centred on the card."""
        draw = wasp.watch.drawable
        draw.rounded_rect(cards.MARGIN, _INFO_Y, cards.SPAN, _INFO_H,
                          cards.COLOR)
        draw.set_font(fonts.sans24)
        track = self._track
        chunks = draw.wrap(track, _TEXT_W) if track else (0,)
        lines = min(len(chunks) - 1, _TRACK_LINES)
        y = _INFO_Y + (_INFO_H - 26 * (lines + 1)) // 2

        draw.set_font(fonts.sans18)
        draw.set_color(wasp.system.theme('mid'), cards.COLOR)
        artist = self._artist
        if artist:
            end = draw.wrap(artist, _TEXT_W)[1]
            draw.string(artist[:end].rstrip(), _TEXT_X, y + 4, width=_TEXT_W)

        draw.set_font(fonts.sans24)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        for i in range(lines):
            sub = track[chunks[i]:chunks[i+1]].rstrip()
            draw.string(sub, _TEXT_X, y + 26 * (i + 1), width=_TEXT_W)

    def _draw_key(self, i):
        """Draw one control card with its symbol."""
        draw = wasp.watch.drawable
        x = _KEY_X[i]
        # The play card is the main action, so it carries the accent.
        bg = wasp.system.theme('ui') if i == 1 else cards.COLOR
        draw.rounded_rect(x, _KEY_Y, _KEY_W, _KEY_H, bg)
        fg = wasp.system.theme('bright')
        cx = x + _KEY_W // 2
        cy = _KEY_Y + _KEY_H // 2
        if i == 0:
            draw.fill(fg, cx - 12, cy - 12, 4, 24)
            for j in range(12):
                draw.fill(fg, cx - 6 + j, cy - j, 1, 2 * j + 1)
        elif i == 2:
            for j in range(12):
                draw.fill(fg, cx + 5 - j, cy - j, 1, 2 * j + 1)
            draw.fill(fg, cx + 8, cy - 12, 4, 24)
        elif self._play_state:
            draw.fill(fg, cx - 12, cy - 15, 9, 30)
            draw.fill(fg, cx + 3, cy - 15, 9, 30)
        else:
            for j in range(18):
                draw.fill(fg, cx - 8 + j, cy - 18 + j, 1, 36 - 2 * j)

    def _update(self):
        if self._musicstate == 'play':
            self._play_state = True
        elif self._musicstate == 'pause':
            self._play_state = False
        self._draw()

    def update(self):
        pass
