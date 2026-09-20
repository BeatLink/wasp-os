# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Stopwatch
~~~~~~~~~~~~

Simple stop/start watch with support for split times.

.. figure:: apps/stopwatch/screenshot.png
    :width: 179
"""
import wasp
import fonts

# 1-bit RLE, 32x32, generated from apps/stopwatch/icon.png, 89 bytes
icon = (
    32, 32,
    b'\x0c\x08\x17\n\x16\n\x17\x08\x1a\x04\x1c\x04\x1a\x08\x16\x0c'
    b'\x04\x02\x0c\x10\x01\x04\n\x16\t\x16\t\n\x02\n\n\t'
    b'\x04\t\t\x0b\x02\x0b\x08\x0b\x02\x0b\x07\x0c\x02\x0c\x06\x0c'
    b'\x02\x0c\x06\x0c\x02\x0c\x06\x0c\x02\x0c\x06\x0b\x04\x0b\x06\x0c'
    b'\x02\x0c\x06\x1a\x06\x1a\x07\x18\x08\x18\t\x16\n\x16\x0b\x14'
    b'\r\x12\x0f\x10\x12\x0c\x16\x08\x0c'
)

class StopwatchApp():
    """Stopwatch application."""
    # Stopwatch requires too many pixels to fit into the launcher

    NAME = 'Stopclock'
    ICON = icon

    def __init__(self):
        self._timer = wasp.widgets.Stopwatch(120-36)
        self._reset()

    def foreground(self):
        """Activate the application."""
        wasp.system.bar.clock = True
        self._draw()
        wasp.system.request_tick(97)
        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.BUTTON |
                                  wasp.EventMask.NEXT)

    def sleep(self):
        return True

    def wake(self):
        self._update()

    def swipe(self, event):
        """Handle NEXT events by augmenting the default processing by resetting
        the count if we are not currently timing something.

        No other swipe event is possible for this application.
        """
        if not self._timer._started_at:
            self._reset()
        return True     # Request system default handling

    def press(self, button, state):
        if not state:
            return

        if self._timer.started:
            self._timer.stop()
        else:
            self._timer.start()

    def touch(self, event):
        if self._timer.started:
            self._splits.insert(0, self._timer.count)
            del self._splits[4:]
            self._nsplits += 1
        else:
            self._reset()

        self._update()
        self._draw_splits()

    def tick(self, ticks):
        self._update()

    def _reset(self):
        self._timer.reset()
        self._splits = []
        self._nsplits = 0

    def _draw_splits(self):
        draw = wasp.watch.drawable
        splits = self._splits
        if 0 == len(splits):
            draw.fill(0, 0, 120, 240, 120)
            return
        y = 240 - 6 - (len(splits) * 24)

        draw.set_font(fonts.sans24)
        draw.set_color(wasp.system.theme('mid'))

        n = self._nsplits
        for i, s in enumerate(splits):
            centisecs = s
            secs = centisecs // 100
            centisecs %= 100
            minutes = secs // 60
            secs %= 60

            t = '# {}   {:02}:{:02}.{:02}'.format(n, minutes, secs, centisecs)
            n -= 1

            w = fonts.width(fonts.sans24, t)
            draw.string(t, 0, y + (i*24), 240)

    def _draw(self):
        """Draw the display from scratch."""
        draw = wasp.watch.drawable
        draw.fill()

        wasp.system.bar.draw()
        self._timer.draw()
        self._draw_splits()

    def _update(self):
        wasp.system.bar.update()
        self._timer.update()
