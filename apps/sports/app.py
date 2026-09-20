# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Sports timer
~~~~~~~~~~~~~~~

A combined stopwatch and step counter.

.. figure:: apps/sports/screenshot.png
    :width: 179
"""
import wasp
import fonts

# 1-bit RLE, 48x48, generated from apps/sports/icon.png, 135 bytes
icon = (
    48, 48,
    b"\x1b\x05*\x07(\t'\t'\t'\t(\x07)\x07"
    b'*\x05 \x07\'\x0c"\x11\x1e\x13\x1c\x16\x19\x18\x18\x08'
    b'\x03\r\x17\x08\x03\x0f\x17\x06\x04\x10\x16\x05\x05\x10\x1f\x11'
    b'\x1f\x12\x1e\x0b\x01\x0c\x17\x0b\x02\r\x16\x0b\x03\x0c\x16\x0b'
    b"\x04\x0b\x16\n\x06\n\x16\n\x08\x07\x17\t'\n'\x0b"
    b'!\x01\x04\x0b\x1f\x03\x04\x0c\x1d\x04\x05\x0b\x14\r\x06\t'
    b'\x13\x0f\x06\t\x12\x0e\t\x07\x12\x0e\t\x07\x12\r\n\x06'
    b'\x14\x0b\x0b\x06)\x07)\x06*\x06*\x06)\x07)\x06'
    b'*\x06*\x06+\x04\x12'
)

class SportsApp():
    """Sports timer application."""
    NAME = 'Sports'
    ICON = icon

    def __init__(self):
        self._timer = wasp.widgets.Stopwatch(120-36)
        self._reset()

    def foreground(self):
        """Activate the application."""
        wasp.system.bar.clock = True
        self._draw()
        wasp.system.request_tick(97)
        wasp.system.request_event(wasp.EventMask.TOUCH | wasp.EventMask.BUTTON)

    def background(self):
        if not self._timer.started:
            self._timer.reset()

    def sleep(self):
        return True

    def wake(self):
        self._update()

    def press(self, button, state):
        if not state:
            return

        steps = wasp.watch.accel.steps

        if self._timer.started:
            self._timer.stop()
        else:
            self._timer.start()
            self._last_steps = steps

    def touch(self, event):
        if not self._timer.started:
            self._reset()
            self._update()

    def tick(self, ticks):
        self._update()

    def _reset(self):
        self._timer.reset()
        self._steps = 0
        self._last_steps = 0

    def _draw(self):
        """Draw the display from scratch."""
        draw = wasp.watch.drawable
        draw.fill()

        wasp.system.bar.draw()
        self._timer.draw()

    def _update(self):
        wasp.system.bar.update()
        self._timer.update()

        if self._timer.started:
            steps = wasp.watch.accel.steps
            redraw = bool(steps - self._last_steps)
            self._steps += steps - self._last_steps
            self._last_steps = steps
        else:
            redraw = True

        if redraw:
            draw = wasp.watch.drawable
            draw.set_font(fonts.sans36)
            draw.set_color(draw.lighten(wasp.system.theme('spot1'), wasp.system.theme('contrast')))
            draw.string(str(self._steps), 0, 170, 228, True)
