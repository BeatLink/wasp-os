# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Button widget
~~~~~~~~~~~~~~~
"""

import cards
import fonts
import wasp

class Button():
    """A button with a text label, drawn as a card."""
    def __init__(self, x, y, w, h, label):
        self._im = (x, y, w, h, label)

    def draw(self):
        """Draw the button."""
        self.update(cards.COLOR, None, wasp.system.theme('bright'))

    def update(self, bg, frame, txt):
        """Draw the button in the given colours.

        :param bg:    Colour of the card
        :param frame: Unused, kept so that older apps still run
        :param txt:   Colour of the label
        """
        draw = wasp.watch.drawable
        im = self._im

        draw.rounded_rect(im[0], im[1], im[2], im[3], bg)
        draw.set_color(txt, bg)
        draw.set_font(fonts.sans24)
        draw.string(im[4], im[0], im[1]+(im[3]//2)-12, width=im[2])

    def touch(self, event):
        """Handle touch events."""
        x = event[1]
        y = event[2]

        # Adopt a slightly oversized hit box
        im = self._im
        x1 = im[0] - 10
        x2 = x1 + im[2] + 20
        y1 = im[1] - 10
        y2 = y1 + im[3] + 20

        if x >= x1 and x < x2 and y >= y1 and y < y2:
            return True

        return False
