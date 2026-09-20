# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2021 Francesco Gazzetta
"""Beacon application
~~~~~~~~~~~~~~~~~~~~~

Flash the relatively powerful HRS LED repeatedly, mostly for signaling purposes.

Frequency and intensity can be changed.

The blinking is handled by the HRS, so this app consumes very little power.
With BLE and/or step counter disabled and blinking frequency set to the minimum,
the watch's battery will last for many days.

.. figure:: apps/beacon/screenshot.png
    :width: 179
"""

import wasp
import machine
from micropython import const

class BeaconApp():
    NAME = "Beacon"
    # 1-bit RLE, 48x48, generated from apps/beacon/icon.png, 209 bytes
    ICON = (
        48, 48,
        b'c\x02&\x02\x05\x04$\x04\x04\x05"\x05\x03\x06\x03\x03'
        b'\x16\x03\x03\x06\x02\x05\x03\x05\x14\x05\x03\x05\x02\x05\x03\x05'
        b'\x14\x05\x03\x05\x01\x06\x03\x05\x07\x06\x07\x05\x03\x0c\x02\x06'
        b'\x06\x08\x06\x06\x02\x0b\x03\x06\x05\n\x05\x06\x03\n\x03\x05'
        b'\x06\n\x06\x05\x03\n\x03\x05\x06\n\x06\x05\x03\n\x03\x05'
        b'\x06\n\x06\x05\x03\n\x03\x05\x06\n\x06\x05\x03\x0b\x02\x06'
        b'\x05\n\x05\x06\x02\x0c\x02\x06\x06\x08\x06\x06\x02\x0c\x03\x05'
        b'\x07\x06\x07\x05\x03\x06\x01\x05\x03\x05\x07\x06\x07\x05\x03\x05'
        b'\x02\x06\x02\x05\x07\x06\x07\x05\x02\x06\x02\x06\x03\x03\x08\x06'
        b'\x08\x03\x03\x06\x03\x05\x0e\x06\x0e\x05\x04\x04\x0f\x06\x0f\x04'
        b'\x05\x02\x10\x06\x10\x01\x19\x06*\x06*\x06*\x06*\x06'
        b'*\x06*\x06*\x06*\x06*\x06*\x06*\x06*\x06'
        b'*\x06*\x06*\x06*\x06*\x06*\x06+\x04,\x04'
        b'\xa6'
    )


    def __init__(self):
        self._checkbox = wasp.widgets.Checkbox(10, 45, "Enable beacon")
        self._slider_current = wasp.widgets.Slider(4, 10, 110, 0x27e4)
        self._slider_wait_time = wasp.widgets.Slider(8, 10, 180)

    def foreground(self):
        wasp.system.bar.clock = True
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH)

    def _draw(self):
        draw = wasp.watch.drawable
        draw.fill()
        wasp.system.bar.draw()
        self._checkbox.draw()
        draw.string("Intensity:", 10, 85)
        self._slider_current.draw()
        draw.string("Frequency:", 10, 155)
        self._slider_wait_time.draw()
        self._draw_preview()

    def touch(self, event):
        if self._checkbox.touch(event):
            if self._checkbox.state:
                wasp.watch.hrs.enable()
                wasp.watch.hrs.set_hwt(self._slider_wait_time.value)
                wasp.watch.hrs.set_drive(self._slider_current.value)
            else:
                wasp.watch.hrs.disable()
            self._checkbox.update()
        elif event[2] >= 180:
            if self._slider_wait_time.touch(event):
                wasp.watch.hrs.set_hwt(self._slider_wait_time.value)
                self._slider_wait_time.update()
                self._draw_preview()
        elif event[2] >= 110:
            if self._slider_current.touch(event):
                wasp.watch.hrs.set_drive(self._slider_current.value)
                self._slider_current.update()
                self._draw_preview()
        wasp.system.bar.update()

    def _draw_preview(self):
        """
        Draw a dashed line representing intensity and frequency
        with thickness and separation of dashes
        """
        draw = wasp.watch.drawable
        draw.fill(None, 10, 220, 227, 20)
        x = 10
        while x < 220:
            wasp.watch.drawable.fill(0x27e4, x, 227, 8, (self._slider_current.value + 1) * 3)
            x += (8 - self._slider_wait_time.value) * 8
