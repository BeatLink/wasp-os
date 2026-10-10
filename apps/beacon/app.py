# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2021 Francesco Gazzetta
"""Beacon application
~~~~~~~~~~~~~~~~~~~~~

Flash the relatively powerful HRS LED repeatedly, mostly for signaling purposes.

Frequency and intensity can be changed.

The blinking is handled by the HRS, so this app consumes very little power.
With BLE and/or step counter disabled and blinking frequency set to the minimum,
the watch's battery will last for many days.

The top card switches the beacon on and off. The two cards below it set
the intensity and the frequency, and the bottom card previews the pattern.

.. figure:: apps/beacon/screenshot.png
    :width: 179
"""

import wasp
import cards
import fonts
import widgets
from micropython import const

# Colour of the LED, used for the preview of the flashing pattern.
_LED = const(0x27e4)
_INTENSITIES = const(4)
_FREQUENCIES = const(8)

# A switch card, two slider cards and a short preview card.
_SWITCH_H = cards.size(4)
_PREVIEW_H = const(28)
_SLIDER_H = (cards.SPAN - _SWITCH_H - _PREVIEW_H - 3 * cards.GAP) // 2
_SWITCH_Y, _CURRENT_Y, _WAIT_Y, _PREVIEW_Y = cards.edges(
    (_SWITCH_H, _SLIDER_H, _SLIDER_H, _PREVIEW_H))
# The slider track and its knob, inside the straight part of a card.
_KNOB = const(24)
_TRACK_X = const(20)
_TRACK_W = const(200 - _KNOB)
_TRACK_DY = _SLIDER_H - _KNOB - 8

class BeaconApp():
    NAME = "Beacon"
    # 1-bit RLE, 32x32, generated from apps/beacon/icon.png, 139 bytes
    ICON = (
        32, 32,
        b'"\x02\x18\x02\x03\x03\x18\x03\x02\x04\x02\x02\x0e\x02\x02\x04'
        b'\x01\x04\x02\x04\x0c\x04\x02\x08\x02\x04\x04\x04\x04\x04\x02\x08'
        b'\x01\x04\x04\x06\x04\x04\x01\x08\x01\x04\x04\x06\x04\x04\x01\x08'
        b'\x01\x04\x03\x07\x04\x04\x01\x08\x01\x04\x04\x06\x04\x04\x01\x08'
        b'\x02\x03\x04\x06\x04\x03\x02\x08\x02\x04\x04\x04\x04\x04\x02\x08'
        b'\x02\x04\x04\x04\x04\x04\x02\x04\x01\x04\x02\x02\x05\x04\x05\x02'
        b'\x02\x04\x02\x03\n\x04\n\x03\x03\x01\x0b\x04\x0b\x01\x10\x04'
        b'\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1c\x04'
        b'\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1d\x02O'
    )


    def __init__(self):
        self._switch = widgets.ToggleButton(cards.MARGIN, _SWITCH_Y,
                                            cards.SPAN, _SWITCH_H, 'Beacon')
        self._current = 0
        self._wait_time = 0

    def foreground(self):
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH)

    def _draw(self):
        draw = wasp.watch.drawable
        draw.fill(0)
        self._switch.draw()
        self._draw_slider(_CURRENT_Y, 'Intensity', self._current,
                          _INTENSITIES, True)
        self._draw_slider(_WAIT_Y, 'Frequency', self._wait_time,
                          _FREQUENCIES, True)
        self._draw_preview()

    def touch(self, event):
        y = event[2]
        if y < _CURRENT_Y:
            self._switch.state = not self._switch.state
            self._switch.draw()
            if self._switch.state:
                wasp.watch.hrs.enable()
                wasp.watch.hrs.set_hwt(self._wait_time)
                wasp.watch.hrs.set_drive(self._current)
            else:
                wasp.watch.hrs.disable()
        elif y >= _PREVIEW_Y:
            pass
        elif y >= _WAIT_Y:
            value = self._value(event[1], _FREQUENCIES)
            if value != self._wait_time:
                self._wait_time = value
                wasp.watch.hrs.set_hwt(value)
                self._draw_slider(_WAIT_Y, 'Frequency', value, _FREQUENCIES)
                self._draw_preview()
        else:
            value = self._value(event[1], _INTENSITIES)
            if value != self._current:
                self._current = value
                wasp.watch.hrs.set_drive(value)
                self._draw_slider(_CURRENT_Y, 'Intensity', value, _INTENSITIES)
                self._draw_preview()

    def _value(self, x, steps):
        """Work out which step of a slider a touch at x picks."""
        step = _TRACK_W // (steps - 1)
        value = (x - _TRACK_X - _KNOB // 2 + step // 2) // step
        return min(steps - 1, max(0, value))

    def _draw_slider(self, y, label, value, steps, card=False):
        """Draw a labelled slider card, or just its track when card is False."""
        draw = wasp.watch.drawable
        if card:
            draw.rounded_rect(cards.MARGIN, y, cards.SPAN, _SLIDER_H,
                              cards.COLOR)
            draw.set_color(wasp.system.theme('bright'), cards.COLOR)
            draw.set_font(fonts.sans18)
            draw.string(label, _TRACK_X, y + 8)

        ty = y + _TRACK_DY
        knob = _TRACK_X + _TRACK_W * value // (steps - 1)
        middle = ty + _KNOB // 2 - 2
        draw.fill(cards.COLOR, _TRACK_X, ty, _TRACK_W + _KNOB, _KNOB)
        done = knob - _TRACK_X
        if done:
            draw.fill(wasp.system.theme('ui'), _TRACK_X + _KNOB // 2, middle,
                      done, 4)
        if done < _TRACK_W:
            draw.fill(wasp.system.theme('mid'), knob + _KNOB // 2, middle,
                      _TRACK_W - done, 4)
        draw.rounded_rect(knob, ty, _KNOB, _KNOB,
                          wasp.system.theme('bright'), cards.COLOR,
                          radius=_KNOB // 2)

    def _draw_preview(self):
        """
        Draw a dashed line representing intensity and frequency
        with thickness and separation of dashes
        """
        draw = wasp.watch.drawable
        draw.rounded_rect(cards.MARGIN, _PREVIEW_Y, cards.SPAN, _PREVIEW_H,
                          cards.COLOR)
        h = (self._current + 1) * 3
        y = _PREVIEW_Y + (_PREVIEW_H - h) // 2
        x = _TRACK_X
        while x < 220:
            draw.fill(_LED, x, y, 8, h)
            x += (_FREQUENCIES - self._wait_time) * 8
