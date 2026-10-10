# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Toggle button widget
~~~~~~~~~~~~~~~~~~~~~~
"""

import cards
import wasp

from widgets.button import Button

class ToggleButton(Button):
    """A button with a text label that can be toggled on and off.

    It is filled with the accent colour while it is on.
    """
    def __init__(self, x, y, w, h, label):
        super().__init__(x, y, w, h, label)
        self.state = False

    def draw(self):
        """Draw the button."""
        if self.state:
            self.update(wasp.system.theme('ui'), None,
                        wasp.system.theme('bright'))
        else:
            self.update(cards.COLOR, None, wasp.system.theme('mid'))

    def touch(self, event):
        """Handle touch events."""
        if super().touch(event):
            self.state = not self.state
            self.draw()
            return True
        else:
            return False
