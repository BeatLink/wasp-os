# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Scroll indicator widget
~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import icons
import wasp
import watch

class ScrollIndicator:
    """Scrolling indicator.

    A pair of arrows that prompted the user to swipe up/down to access
    additional pages of information.
    """
    def __init__(self, x=240-18, y=240-24):
        self._pos = (x, y)
        self.up = True
        self.down = True

    def draw(self):
        """Draw from scrolling indicator.

        For this simple widget :py:meth:`~.draw` is simply a synonym for
        :py:meth:`~.update`.
        """
        self.update()

    def update(self):
        """Update from scrolling indicator."""
        draw = watch.drawable
        color = wasp.system.theme('scroll-indicator')

        if self.up:
            draw.blit(icons.up_arrow, self._pos[0], self._pos[1], fg=color)
        if self.down:
            draw.blit(icons.down_arrow, self._pos[0], self._pos[1]+13, fg=color)
