# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Spinner widget
~~~~~~~~~~~~~~~~
"""

import fonts
import icons
import wasp
import watch

class Spinner():
    """A simple Spinner widget.

    In order to have large enough hit boxes the spinner is a fairly large
    widget and requires 60x120 px.
    """
    def __init__(self, x, y, mn, mx, field=1, incr=1):
        self._im = bytes((x, y, mn, mx, field, incr))
        self.value = mn

    def draw(self):
        """Draw the spinner."""
        draw = watch.drawable
        im = self._im
        fg = draw.lighten(wasp.system.theme('ui'), wasp.system.theme('contrast'))
        draw.blit(icons.up_arrow, im[0]+30-8, im[1]+20, fg)
        draw.blit(icons.down_arrow, im[0]+30-8, im[1]+120-20-9, fg)
        self.update()

    def update(self):
        """Update the spinner value."""
        draw = watch.drawable
        im = self._im
        draw.set_color(wasp.system.theme('bright'))
        draw.set_font(fonts.sans28)
        s = str(self.value)
        if len(s) < im[4]:
            s = '0' * (im[4] - len(s)) + s
        draw.string(s, im[0], im[1]+60-14, width=60)

    def touch(self, event):
        x = event[1]
        y = event[2]
        im = self._im
        if x >= im[0] and x < im[0]+60 and y >= im[1] and y < im[1]+120:
            if y < im[1] + 60:
                self.value += im[5]
                if self.value > im[3]:
                    self.value = im[2]
            else:
                self.value -= im[5]
                if self.value < im[2]:
                    self.value = im[3]
            while self.value % im[5] != 0:
                self.value -= 1

            self.update()
            return True

        return False
