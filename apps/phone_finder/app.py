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

# 1-bit RLE, 32x32, generated from apps/phone_finder/icon.png, 113 bytes
icon = (
    32, 32,
    b'\x07\x12\r\x14\x0b\x16\n\x16\n\x04\x0e\x04\n\x04\x0e\x04'
    b'\n\x04\x0e\x04\n\x04\x0e\x04\n\x04\x0e\x04\n\x04\x0e\x04'
    b'\n\x04\x0e\x04\n\x04\x0e\x04\n\x04\x0e\x04\n\x04\x0e\x04'
    b'\n\x04\x0e\x04\n\x04\x0e\x04\n\x04\x0e\x04\n\x04\x0e\x04'
    b'\n\x04\x0e\x04\n\x04\x0e\x04\n\x04\x0e\x04\n\x04\x0e\x04'
    b'\n\x04\x0e\x04\n\x04\x0e\x04\n\x16\n\x16\n\n\x02\n'
    b'\n\t\x04\t\n\t\x04\t\n\n\x02\n\x0b\x14\r\x12'
    b'\x07'
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