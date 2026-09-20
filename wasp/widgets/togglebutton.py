# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Toggle button widget
~~~~~~~~~~~~~~~~~~~~~~
"""

import wasp

from widgets.button import Button

class ToggleButton(Button):
    """A button with a text label that can be toggled on and off."""
    def __init__(self, x, y, w, h, label):
        super().__init__(x, y, w, h, label)
        self.state = False

    def draw(self):
        """Draw the button."""
        draw = wasp.watch.drawable

        if self.state:
            bg = draw.darken(wasp.system.theme('ui'))
        else:
            bg = draw.darken(wasp.system.theme('mid'))
        frame = wasp.system.theme('mid')
        txt = wasp.system.theme('bright')

        self.update(bg, frame, txt)

    def touch(self, event):
        """Handle touch events."""
        if super().touch(event):
            self.state = not self.state
            self.draw()
            return True
        else:
            return False
