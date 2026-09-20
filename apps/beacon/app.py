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
