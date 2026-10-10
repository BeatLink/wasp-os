# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Wolfgang Ginolas
"""Timer Application
~~~~~~~~~~~~~~~~~~~~

An application to set a vibration in a specified amount of time. Like a kitchen timer.

The minutes and seconds each have a column of cards to count them up and
down, over a card that starts the timer. While it runs, one large card counts
down above a card that stops it.

    .. figure:: apps/timer/screenshot.png
        :width: 179

        Screenshot of the Timer Application

"""

import wasp
import cards
import fonts
import widgets
import math
from micropython import const

# 1-bit RLE, 32x32, generated from apps/timer/icon.png, 101 bytes
icon = (
    32, 32,
    b'\x05\x16\t\x18\x08\x18\t\x16\x0b\x04\x0c\x04\x0c\x04\x0c\x04'
    b'\x0c\x04\x0c\x04\x0c\x05\n\x05\r\x04\n\x04\x0e\x05\x08\x05'
    b'\x0f\x05\x06\x05\x11\x05\x04\x05\x13\x05\x02\x05\x15\n\x17\x08'
    b'\x19\x06\x1a\x06\x19\x08\x17\n\x15\x05\x02\x05\x13\x05\x04\x05'
    b'\x11\x05\x06\x05\x0f\x05\x08\x05\x0e\x04\n\x04\r\x05\n\x05'
    b'\x0c\x04\x0c\x04\x0c\x04\x0c\x04\x0c\x04\x0c\x04\x0b\x16\t\x18'
    b'\x08\x18\t\x16\x05'
)

_STOPPED = const(0)
_RUNNING = const(1)
_RINGING = const(2)

# Four rows: three for the minute and second columns, then the action card.
_ROW_H = cards.size(4)
_ROW_TOPS = cards.edges((_ROW_H,) * 4)
_BUTTON_Y = _ROW_TOPS[3]
_FIELDS_H = _BUTTON_Y - cards.GAP - cards.MARGIN
_COL_W = cards.size(2)
_COLS = cards.edges((_COL_W, _COL_W))

class TimerApp():
    """Allows the user to set a vibration alarm.
    """
    NAME = 'Timer'

    @property
    def PERSIST(self):
        """Stay resident while counting, because the alarm callback holds this instance."""
        return self.state == _RUNNING
    ICON = icon

    def __init__(self):
        """Initialize the application."""
        self.minutes = widgets.Spinner(_COLS[0], cards.MARGIN, 0, 99, 2,
                                       w=_COL_W, h=_FIELDS_H)
        self.seconds = widgets.Spinner(_COLS[1], cards.MARGIN, 0, 59, 2,
                                       w=_COL_W, h=_FIELDS_H)
        self.current_alarm = None

        self.minutes.value = 10
        self.state = _STOPPED

    def foreground(self):
        """Activate the application."""
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH)
        wasp.system.request_tick(1000)

    def background(self):
        """De-activate the application."""
        if self.state == _RINGING:
            self.state = _STOPPED

    def tick(self, ticks):
        """Notify the application that its periodic tick is due."""
        if self.state == _RINGING:
            wasp.watch.vibrator.pulse(duty=50, ms=500)
            wasp.system.keep_awake()
        self._update()

    def touch(self, event):
        """Notify the application of a touchscreen touch event."""
        if self.state == _RINGING:
            mute = wasp.watch.display.mute
            mute(True)
            self._stop()
            mute(False)
        elif self.state == _RUNNING:
            self._stop()
        else:  # _STOPPED
            if self.minutes.touch(event) or self.seconds.touch(event):
                pass
            else:
                y = event[2]
                if y >= _BUTTON_Y:
                    self._start()


    def _start(self):
        self.state = _RUNNING
        now = wasp.watch.rtc.time()
        self.current_alarm = now + self.minutes.value * 60 + self.seconds.value
        wasp.system.set_alarm(self.current_alarm, self._alert)
        self._draw()

    def _stop(self):
        self.state = _STOPPED
        wasp.system.cancel_alarm(self.current_alarm, self._alert)
        self._draw()

    def _draw(self):
        """Draw the display from scratch."""
        draw = wasp.watch.drawable
        draw.fill(0)

        if self.state == _STOPPED:
            self.minutes.draw()
            self.seconds.draw()
            self._draw_button(self._draw_play)
            return

        draw.rounded_rect(cards.MARGIN, cards.MARGIN, cards.SPAN, _FIELDS_H,
                          cards.COLOR)
        if self.state == _RINGING:
            draw.set_color(wasp.system.theme('bright'), cards.COLOR)
            draw.set_font(fonts.sans24)
            draw.string(self.NAME, cards.MARGIN, 120, width=cards.SPAN)
            draw.rleblit(icon, (104, 50), wasp.system.theme('bright'),
                         cards.COLOR)
        else:  # _RUNNING
            self._update()
        self._draw_button(self._draw_stop)

    def _draw_button(self, symbol):
        """Draw the action card along the bottom with a symbol on it."""
        wasp.watch.drawable.rounded_rect(cards.MARGIN, _BUTTON_Y, cards.SPAN,
                                         _ROW_H, cards.COLOR)
        symbol(120, _BUTTON_Y + _ROW_H // 2)

    def _update(self):
        draw = wasp.watch.drawable
        if self.state == _RUNNING:
            now = wasp.watch.rtc.time()
            s = self.current_alarm - now
            if s<0:
                s = 0
            m = math.floor(s // 60)
            s = math.floor(s) % 60
            draw.set_color(wasp.system.theme('bright'), cards.COLOR)
            draw.set_font(fonts.sans36)
            # Keep the padding inside the straight part of the card.
            draw.string('{:02d}:{:02d}'.format(m, s), cards.MARGIN + 12,
                        cards.MARGIN + (_FIELDS_H - 36) // 2,
                        width=cards.SPAN - 24)

    def _draw_play(self, x, y):
        """Draw a play triangle centred on x, y."""
        draw = wasp.watch.drawable
        fg = wasp.system.theme('bright')
        for i in range(0, 18):
            draw.fill(fg, x - 8 + i, y - 18 + i, 1, 36 - 2*i)

    def _draw_stop(self, x, y):
        """Draw a stop square centred on x, y."""
        wasp.watch.drawable.fill(wasp.system.theme('bright'),
                                 x - 15, y - 15, 30, 30)

    def _alert(self):
        self.state = _RINGING
        wasp.system.wake()
        wasp.system.switch(self)
