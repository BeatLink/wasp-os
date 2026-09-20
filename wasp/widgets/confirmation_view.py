# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Confirmation view widget
~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import fonts
import wasp

from widgets.button import Button

class ConfirmationView:
    """Confirmation widget allowing user confirmation of a setting."""

    def __init__(self):
        self.active = False
        self.value = False
        self._yes = Button(20, 140, 90, 45, 'Yes')
        self._no = Button(130, 140, 90, 45, 'No')

    def draw(self, message):
        draw = wasp.watch.drawable
        mute = wasp.watch.display.mute

        mute(True)
        draw.set_color(wasp.system.theme('bright'))
        draw.set_font(fonts.sans24)
        draw.fill()
        draw.string(message, 0, 60)
        self._yes.draw()
        self._no.draw()
        mute(False)

        self.active = True

    def touch(self, event):
        if not self.active:
            return False

        if self._yes.touch(event):
            self.active = False
            self.value = True
            return True
        elif self._no.touch(event):
            self.active = False
            self.value = False
            return True

        return False
