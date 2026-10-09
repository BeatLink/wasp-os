# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Notification bar widget
~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import icons
import wasp
import watch

class NotificationBar:
    """Show BT status and if there are pending notifications."""
    def __init__(self, x=0, y=0):
        self._pos = (x, y)
        self._shown = None

    def draw(self):
        """Redraw the notification widget from scratch."""
        self._shown = None
        self.update()

    def update(self):
        """Redraw the widget if the connection or notifications have changed."""
        connected = wasp.watch.connected()
        pending = bool(wasp.system.notifications)
        shown = connected * 2 + pending
        if shown == self._shown:
            return
        self._shown = shown

        draw = watch.drawable
        (x, y) = self._pos

        if connected:
            draw.blit(icons.blestatus, x, y, fg=wasp.system.theme('ble'))
            if pending:
                draw.blit(icons.notification, x+22, y,
                          fg=wasp.system.theme('notify-icon'))
            else:
                draw.fill(0, x+22, y, 30, 32)
        elif pending:
            draw.blit(icons.notification, x, y,
                      fg=wasp.system.theme('notify-icon'))
            draw.fill(0, x+30, y, 22, 32)
        else:
            draw.fill(0, x, y, 52, 32)
