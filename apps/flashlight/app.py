# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Flashlight
~~~~~~~~~~~~~

Shows a bright screen that you can tap to change brightness or switch to redlight.

.. figure:: apps/flashlight/screenshot.png
    :width: 179
"""

import wasp

# 1-bit RLE, 32x32, generated from wasp/resources/torch_icon.png, 77 bytes
_TORCH = (
    32, 32,
    b'\r\x06\x18\n\x14\x0e\x11\x10\x0f\x07\x03\x08\x0e\x05\x05\x08'
    b'\r\x05\x03\x0c\x0c\x04\x03\r\x0b\x05\x02\x0f\n\x04\x02\x10'
    b'\n\x04\x02\x10\n\x04\x02\x10\n\x16\n\x16\x0b\x14\x0c\x14'
    b'\x0c\x14\r\x12\x0f\x10\x11\x0f\x11\x0e\x13\x0c\x14\x0c\x15\n'
    b'V\n\x16\n\x16\n\x17\x08\x18\x08\x1a\x04\x0e'
)


class FlashlightApp(object):
    """Trivial flashlight application."""
    NAME = 'Torch'
    ICON = _TORCH

    def foreground(self):
        """Activate the application."""
        wasp.system.request_tick(3000)
        wasp.system.request_event(wasp.EventMask.TOUCH)

        self._brightness = wasp.system.brightness
        wasp.system.brightness = 3
        self._ntouch = 1
        wasp.watch.drawable.fill(0xffff)  # white

    def background(self):
        """De-activate the application (without losing original state)."""
        wasp.system.brightness = self._brightness

    def tick(self, ticks):
        wasp.system.keep_awake()

    def touch(self, event):
        self._ntouch += 1
        self._ntouch %= 6
        wasp.system.brightness = (-self._ntouch) % 3 + 1
        if (-self._ntouch + 1) % 3 == 0:
            if -self._ntouch % 6 < 3:
                wasp.watch.drawable.fill(0xf800)  # red
            else:
                wasp.watch.drawable.fill(0xffff)  # white
