# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Checkbox widget
~~~~~~~~~~~~~~~~~
"""

import fonts
import icons
import wasp

class Checkbox():
    """A simple (labelled) checkbox."""
    def __init__(self, x, y, label=None):
        self._im = (x, y, label)
        self.state = False

    @property
    def label(self):
        return self._im[2]

    def draw(self, y=None):
        """Draw the checkbox and label.

        :param y: Row to draw at, for a screen that has moved the checkbox
                  from where it normally sits
        """
        draw = wasp.watch.drawable
        im = self._im
        if y is None:
            y = im[1]
        if im[2]:
            draw.set_color(wasp.system.theme('bright'))
            draw.set_font(fonts.sans24)
            draw.string(im[2], im[0], y+6)
        self.update(y)

    def update(self, y=None):
        """Draw the checkbox.

        :param y: Row to draw at, as for :py:meth:`draw`
        """
        draw = wasp.watch.drawable
        im = self._im
        if y is None:
            y = im[1]
        if self.state:
            c1 = wasp.system.theme('ui')
            c2 = draw.lighten(c1, wasp.system.theme('contrast'))
            fg = c2
        else:
            c1 = 0
            c2 = 0
            fg = wasp.system.theme('mid')
        # Draw checkbox on the right margin if there is a label, otherwise
        # draw at the natural location
        x = 239 - 32 - 4 if im[2] else im[0]
        draw.blit(icons.checkbox, x, y, fg, c1, c2)

    def touch(self, event):
        """Handle touch events."""
        x = event[1]
        y = event[2]
        im = self._im
        if (self.label or im[0] <= x < im[0]+40) and im[1] <= y < im[1]+40:
            self.state = not self.state
            self.update()
            return True
        return False
