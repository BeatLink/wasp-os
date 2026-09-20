# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Status bar widget
~~~~~~~~~~~~~~~~~~~
"""

from widgets.battery_meter import BatteryMeter
from widgets.clock import Clock
from widgets.notification_bar import NotificationBar

class StatusBar:
    """Combo widget to handle notification, time and battery level."""
    def __init__(self):
        self._clock = Clock()
        self._meter = BatteryMeter()
        self._notif = NotificationBar()

    @property
    def clock(self):
        """True if the clock should be included in the status bar, False
        otherwise.
        """
        return self._clock.enabled

    @clock.setter
    def clock(self, enabled):
        self._clock.enabled = enabled

    def draw(self):
        """Redraw the status bar from scratch."""
        self._clock.draw()
        self._meter.draw()
        self._notif.draw()

    def update(self):
        """Lazily update the status bar.

        :returns: An time tuple if the time has changed since the last call,
                  None otherwise.
        """
        now = self._clock.update()
        if now:
            self._meter.update()
            self._notif.update()
        return now
