# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2023 Adam Blair
"""Phone finder application
~~~~~~~~~~~~~~~~~~~~~~~~~~~

An application to find a phone connected via Gadgetbridge.

    .. figure:: apps/phone_finder/screenshot.png
        :width: 179

        Screenshot of the Phone Finder Application

"""

import wasp
import fonts
import widgets
from gadgetbridge import send_cmd

# 1-bit RLE, 48x48, generated from apps/phone_finder/icon.png, 169 bytes
icon = (
    48, 48,
    b'\x0b\x19\x15\x1d\x12\x1f\x11\x1f\x10!\x0f!\x0f\x06\x15\x06'
    b'\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06'
    b'\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06'
    b'\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06'
    b'\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06'
    b'\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06'
    b'\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06'
    b'\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06\x0f\x06\x15\x06'
    b'\x0f\x06\x15\x06\x0f!\x0f!\x0f!\x0f\x0f\x03\x0f\x0f\x0e'
    b'\x05\x0e\x0f\x0e\x05\x0e\x0f\x0e\x05\x0e\x0f\x0e\x05\x0e\x10\x0e'
    b'\x03\x0e\x11\x1f\x12\x1d\x15\x19\x0c'
)

class PhoneFinderApp():
    """Allows the user to set a vibration alarm.
    """
    NAME = 'Finder'
    ICON = icon

    def __init__(self):
        """Initialize the application."""
        pass

    def foreground(self):
        """Activate the application."""
        self.ring_btn = widgets.ToggleButton(20, 120, 200, 60, 'Ring')

        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH)
        wasp.system.request_tick(1000)

    def background(self):
        """De-activate the application."""
        self.ring_btn = None
        del self.ring_btn

    def tick(self, ticks):
        """Notify the application that its periodic tick is due."""
        wasp.system.bar.update()

    def touch(self, event):
        """Notify the application of a touchscreen touch event."""
        if self.ring_btn.touch(event):
            if self.ring_btn.state:
                send_cmd('{"t":"findPhone", "n":"true"} ')
            else:
                send_cmd('{"t":"findPhone", "n":"false"} ')

    def _draw(self):
        """Draw the display from scratch."""
        draw = wasp.watch.drawable
        draw.fill()
        sbar = wasp.system.bar
        sbar.clock = True
        sbar.draw()

        draw.set_font(fonts.sans24)
        draw.string('Find phone', 60, 70, width=120)
        self.ring_btn.draw()