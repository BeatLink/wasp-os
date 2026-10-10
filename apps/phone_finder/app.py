# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2023 Adam Blair
"""Phone finder application
~~~~~~~~~~~~~~~~~~~~~~~~~~~

An application to find a phone connected via Gadgetbridge.

The top card names the app and the bottom card rings the phone, filled with
the accent while it rings.

    .. figure:: apps/phone_finder/screenshot.png
        :width: 179

        Screenshot of the Phone Finder Application

"""

import wasp
import cards
import fonts
import widgets
from gadgetbridge import send_cmd

# A title card above the ring card.
_CARD_H = cards.size(2)
_TITLE_Y, _RING_Y = cards.edges((_CARD_H, _CARD_H))

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
        self.ring_btn = widgets.ToggleButton(cards.MARGIN, _RING_Y, cards.SPAN,
                                             _CARD_H, 'Ring')

        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH)

    def background(self):
        """De-activate the application."""
        self.ring_btn = None
        del self.ring_btn

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
        draw.fill(0)
        draw.rounded_rect(cards.MARGIN, _TITLE_Y, cards.SPAN, _CARD_H,
                          cards.COLOR)
        bright = wasp.system.theme('bright')
        draw.rleblit(icon, (104, _TITLE_Y + 18), bright, cards.COLOR)
        draw.set_color(bright, cards.COLOR)
        draw.set_font(fonts.sans24)
        draw.string('Find phone', cards.MARGIN + 12, _TITLE_Y + 62,
                    width=cards.SPAN - 24)
        self.ring_btn.draw()
