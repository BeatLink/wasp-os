# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Graphical button widget
~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import wasp

class GfxButton():
    """A button with a graphical icon."""
    def __init__(self, x, y, gfx):
        self._im = bytes((x, y))
        self.gfx = gfx

    def draw(self):
        """Draw the button."""
        im = self._im
        wasp.watch.drawable.blit(self.gfx, im[0], im[1])

    def touch(self, event):
        x = event[1]
        y = event[2]

        # Adopt a slightly oversized hit box
        im = self._im
        gfx = self.gfx
        x1 = im[0] - 10
        x2 = x1 + gfx[1] + 20
        y1 = im[1] - 10
        y2 = y1 + gfx[2] + 20

        if x >= x1 and x < x2 and y >= y1 and y < y2:
            return True

        return False
