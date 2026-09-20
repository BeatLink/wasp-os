# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Battery meter widget
~~~~~~~~~~~~~~~~~~~~~~
"""

import icons
import wasp
import watch

class BatteryMeter:
    """Battery meter widget.

    A simple battery meter with a charging indicator, will draw at the
    top-right of the display.
    """
    def __init__(self):
        self.level = -2

    def draw(self):
        """Draw from meter (from scratch)."""
        self.level = -2
        self.update()

    def update(self):
        """Update the meter.

        The update is lazy and won't redraw unless the level has changed.
        """
        icon = icons.battery
        draw = watch.drawable

        if watch.battery.charging():
            if self.level != -1:
                draw.blit(icon, 239-icon[1], 0,
                             fg=wasp.system.theme('battery'))
                self.level = -1
        else:
            level = watch.battery.level()
            if level == self.level:
                return


            green = level // 3
            if green > 31:
                green = 31
            red = 31-green
            rgb = (red << 11) + (green << 6)

            if self.level < 0 or ((level > 5) ^ (self.level > 5)):
                if level  > 5:
                    draw.blit(icon, 239-icon[1], 0,
                             fg=wasp.system.theme('battery'))
                else:
                    rgb = 0xf800
                    draw.blit(icon, 239-icon[1], 0, fg=0xf800)

            w = icon[1] - 10
            x = 239 - 5 - w
            h = 2*level // 11
            if 18 - h:
                draw.fill(0, x, 9, w, 18 - h)
            if h:
                draw.fill(rgb, x, 27 - h, w, h)

            self.level = level
