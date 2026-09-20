# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Slider widget
~~~~~~~~~~~~~~~
"""

import icons
import wasp
import watch

from micropython import const

_SLIDER_KNOB_DIAMETER = const(40)
_SLIDER_KNOB_RADIUS = const(_SLIDER_KNOB_DIAMETER // 2)
_SLIDER_WIDTH = const(220)
_SLIDER_TRACK = const(_SLIDER_WIDTH - _SLIDER_KNOB_DIAMETER)
_SLIDER_TRACK_HEIGHT = const(8)
_SLIDER_TRACK_Y1 = const(_SLIDER_KNOB_RADIUS - (_SLIDER_TRACK_HEIGHT // 2))
_SLIDER_TRACK_Y2 = const(_SLIDER_TRACK_Y1 + _SLIDER_TRACK_HEIGHT)

class Slider():
    """A slider to select values."""
    def __init__(self, steps, x=10, y=90, color=None):
        self.value = 0
        self._steps = steps
        self._stepsize = _SLIDER_TRACK / (steps-1)
        self._x = x
        self._y = y
        self._color = color
        self._lowlight = None

    def draw(self):
        """Draw the slider."""
        draw = watch.drawable
        x = self._x
        y = self._y
        color = self._color
        if self._color is None:
            self._color = wasp.system.theme('ui')
            color = self._color
        if self._lowlight is None:
            self._lowlight = draw.lighten(color, wasp.system.theme('contrast'))
        light = self._lowlight

        knob_x = x + ((_SLIDER_TRACK * self.value) // (self._steps-1))
        draw.blit(icons.knob, knob_x, y, color)

        w = knob_x - x
        if w > 0:
            draw.fill(0, x, y, w, _SLIDER_TRACK_Y1)
            if w > _SLIDER_KNOB_RADIUS:
                draw.fill(0, x, y+_SLIDER_TRACK_Y1,
                          _SLIDER_KNOB_RADIUS, _SLIDER_TRACK_HEIGHT)
                draw.fill(color, x+_SLIDER_KNOB_RADIUS, y+_SLIDER_TRACK_Y1,
                          w-_SLIDER_KNOB_RADIUS, _SLIDER_TRACK_HEIGHT)
            else:
                draw.fill(0, x, y+_SLIDER_TRACK_Y1, w, _SLIDER_TRACK_HEIGHT)
            draw.fill(0, x, y+_SLIDER_TRACK_Y2, w, _SLIDER_TRACK_Y1)

        sx = knob_x + _SLIDER_KNOB_DIAMETER
        w = _SLIDER_WIDTH - _SLIDER_KNOB_DIAMETER - w
        if w > 0:
            draw.fill(0, sx, y, w, _SLIDER_TRACK_Y1)
            if w > _SLIDER_KNOB_RADIUS:
                draw.fill(0, sx+w-_SLIDER_KNOB_RADIUS, y+_SLIDER_TRACK_Y1,
                          _SLIDER_KNOB_RADIUS, _SLIDER_TRACK_HEIGHT)
                draw.fill(light, sx, y+_SLIDER_TRACK_Y1,
                          w-_SLIDER_KNOB_RADIUS, _SLIDER_TRACK_HEIGHT)
            else:
                draw.fill(0, sx, y+_SLIDER_TRACK_Y1, w, _SLIDER_TRACK_HEIGHT)
            draw.fill(0, sx, y+_SLIDER_TRACK_Y2, w, _SLIDER_TRACK_Y1)

    def update(self):
        self.draw()

    def touch(self, event):
        tx = event[1]
        threshold = self._x + 20 - (self._stepsize / 2)
        v = int((tx - threshold) / self._stepsize)
        if v < 0:
            v = 0
        elif v >= self._steps:
            v = self._steps - 1
        changed = self.value != v
        self.value = v
        return changed
