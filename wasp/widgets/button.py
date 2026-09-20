# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Button widget
~~~~~~~~~~~~~~~
"""

import fonts
import wasp

class Button():
    """A button with a text label."""
    def __init__(self, x, y, w, h, label):
        self._im = (x, y, w, h, label)

    def draw(self):
        """Draw the button."""
        bg = wasp.watch.drawable.darken(wasp.system.theme('ui'))
        frame = wasp.system.theme('mid')
        txt = wasp.system.theme('bright')
        self.update(bg, frame, txt)

    def update(self, bg, frame, txt):
        draw = wasp.watch.drawable
        im = self._im

        draw.fill(bg, im[0], im[1], im[2], im[3])
        draw.set_color(txt, bg)
        draw.set_font(fonts.sans24)
        draw.string(im[4], im[0], im[1]+(im[3]//2)-12, width=im[2])

        draw.fill(frame, im[0],im[1],          im[2], 2)
        draw.fill(frame, im[0], im[1]+im[3]-2, im[2], 2)
        draw.fill(frame, im[0],         im[1], 2, im[3])
        draw.fill(frame, im[0]+im[2]-2, im[1], 2, im[3])

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
