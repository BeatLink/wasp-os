# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Spinner widget
~~~~~~~~~~~~~~~~
"""

import cards
import fonts
import wasp
import watch

from micropython import const
from widgets.page import clip

# Corner radius of a card, which the value is kept clear of.
_RADIUS = const(12)

class Spinner():
    """A spinner drawn as three stacked cards: plus, the value, and minus.

    Tap the top card to count up and the bottom one to count down. The
    default size of 60x120 px keeps the hit boxes large enough to use.
    """
    def __init__(self, x, y, mn, mx, field=1, incr=1, w=60, h=120):
        self._im = bytes((x, y, mn, mx, field, incr, w, h))
        self.value = mn

    def _card(self):
        """Height of each card and the distance from one to the next."""
        h = self._im[7]
        size = (h - 2 * cards.GAP) // 3
        return (size, (h - size) // 2)

    def draw(self, top=0, height=240, sy=0):
        """Draw the spinner, or the part of it inside a band of rows.

        :param top:    First page row of the band
        :param height: How many rows the band covers
        :param sy:     Add a page row to this to get its screen row
        """
        draw = watch.drawable
        im = self._im
        (size, pitch) = self._card()
        th = fonts.sans28.height()
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans28)
        for i in range(3):
            tile = im[1] + i * pitch
            (first, rows) = clip(top, height, tile, size)
            if not rows:
                continue
            draw.rounded_rect(im[0], sy + tile, im[6], size, cards.COLOR,
                              first=first, rows=rows)
            if i == 1:
                continue
            ty = tile + (size - th) // 2
            (first, rows) = clip(top, height, ty, th)
            if rows:
                draw.string('+' if i == 0 else '-', im[0], sy + ty,
                            width=im[6], first=first, rows=rows)
        self.update(top, height, sy)

    def update(self, top=0, height=240, sy=0):
        """Update the spinner value, or the part of it inside a band of rows."""
        draw = watch.drawable
        im = self._im
        (size, pitch) = self._card()
        ty = im[1] + pitch + (size - fonts.sans28.height()) // 2
        (first, rows) = clip(top, height, ty, fonts.sans28.height())
        if not rows:
            return
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans28)
        s = str(self.value)
        if len(s) < im[4]:
            s = '0' * (im[4] - len(s)) + s
        # Keep the padding inside the straight part of the card.
        draw.string(s, im[0] + _RADIUS, sy + ty, width=im[6] - 2 * _RADIUS,
                    first=first, rows=rows)

    def touch(self, event):
        x = event[1]
        y = event[2]
        im = self._im
        (size, pitch) = self._card()
        if x < im[0] or x >= im[0] + im[6] or y < im[1] or y >= im[1] + im[7]:
            return False

        # The middle card only shows the value.
        if y < im[1] + pitch:
            self.value += im[5]
            if self.value > im[3]:
                self.value = im[2]
        elif y >= im[1] + 2 * pitch:
            self.value -= im[5]
            if self.value < im[2]:
                self.value = im[3]
        else:
            return False
        while self.value % im[5] != 0:
            self.value -= 1

        self.update()
        return True
