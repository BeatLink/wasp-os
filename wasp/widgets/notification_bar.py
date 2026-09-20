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

    def draw(self):
        """Redraw the notification widget.

        For this simple widget :py:meth:`~.draw` is simply a synonym for
        :py:meth:`~.update` because we unconditionally update from scratch.
        """
        self.update()

    def update(self):
        """Update the widget.

        This widget does not implement lazy redraw internally since this
        can often be implemented (with less state) by the container.
        """
        draw = watch.drawable
        (x, y) = self._pos

        if wasp.watch.connected():
            draw.blit(icons.blestatus, x, y, fg=wasp.system.theme('ble'))
            if wasp.system.notifications:
                draw.blit(icons.notification, x+22, y,
                          fg=wasp.system.theme('notify-icon'))
            else:
                draw.fill(0, x+22, y, 30, 32)
        elif wasp.system.notifications:
            draw.blit(icons.notification, x, y,
                      fg=wasp.system.theme('notify-icon'))
            draw.fill(0, x+30, y, 22, 32)
        else:
            draw.fill(0, x, y, 52, 32)
