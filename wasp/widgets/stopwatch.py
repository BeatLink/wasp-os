# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Stopwatch widget
~~~~~~~~~~~~~~~~~~
"""

import cards
import fonts
import wasp

class Stopwatch:
    """A stopwatch widget

    :param y:  Row the digits are drawn at
    :param bg: Colour behind the digits, such as the card they sit on
    """
    def __init__(self, y, bg=0):
        self._y = y
        self._bg = bg
        self.reset()

    def start(self):
        uptime = wasp.watch.rtc.get_uptime_ms() // 10
        self._started_at = uptime - self.count

    def stop(self):
        self._started_at = 0

    @property
    def started(self):
        return bool(self._started_at)

    def save(self):
        """Return the values restore needs to carry on, running or not."""
        return (self.count, self._started_at)

    def restore(self, saved):
        (self.count, self._started_at) = saved
        self._last_count = -1

    def reset(self):
        self.count = 0
        self._started_at = 0
        self._last_count = -1

    def draw(self):
        self._last_count = -1
        self.update()

    def update(self):
        # Before we do anything else let's make sure count is
        # up to date
        if self._started_at:
            uptime = wasp.watch.rtc.get_uptime_ms() // 10
            self.count = uptime - self._started_at
            if self.count > 999*60*100:
                self.reset()

        if self._last_count != self.count:
            centisecs = self.count
            secs = centisecs // 100
            centisecs %= 100
            minutes = secs // 60
            secs %= 60

            t1 = '{}:{:02}'.format(minutes, secs)
            t2 = '{:02}'.format(centisecs)

            y = self._y
            draw = wasp.watch.drawable
            draw.set_font(fonts.sans36)
            bg = self._bg
            draw.set_color(draw.lighten(wasp.system.theme('ui'), wasp.system.theme('contrast')), bg)
            w = fonts.width(fonts.sans36, t1)
            draw.string(t1, 180-w, y)
            # Leave the margin alone, so a card the digits sit on keeps its corners.
            draw.fill(bg, cards.MARGIN + 12, y, 180-w-cards.MARGIN-12, 36)
            draw.set_font(fonts.sans24)
            draw.string(t2, 180, y+18, width=46)

            self._last_count = self.count
