# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Clock widget
~~~~~~~~~~~~~~
"""

import fonts
import wasp

class Clock:
    """Small clock widget."""
    def __init__(self, enabled=True):
        self.on_screen = None
        self.enabled = enabled

    def draw(self):
        """Redraw the clock from scratch.

        The container is required to clear the canvas prior to the redraw
        and the clock is only drawn if it is enabled.
        """
        self.on_screen = None
        self.update()

    def update(self):
        """Update the clock widget if needed.

        This is a lazy update that only redraws if the time has changes
        since the last call *and* the clock is enabled.

        :returns: An time tuple if the time has changed since the last call,
                  None otherwise.
        """
        now = wasp.watch.rtc.get_localtime()
        on_screen = self.on_screen

        if on_screen and on_screen == now:
            return None

        if self.enabled and (not on_screen
                or now[4] != on_screen[4] or now[3] != on_screen[3]):
            t1 = '{:02}:{:02}'.format(now[3], now[4])

            draw = wasp.watch.drawable
            draw.set_font(fonts.sans28)
            draw.set_color(wasp.system.theme('status-clock'))
            draw.string(t1, 52, 4, 138)

        self.on_screen = now
        return now
