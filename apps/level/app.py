# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2021 Francesco Gazzetta
"""Level application
~~~~~~~~~~~~~~~~~~~~

This app shows a dot that moves depending on the orientation of the watch.
A tap opens a menu with the option to calibrate or reset the level.
To calibrate, place the watch on a flat surface, then tap the "Calibrate"
button while ensuring the watch is stationary.

.. figure:: apps/level/screenshot.png
    :width: 179
"""

import wasp
import cards
import watch
import widgets
from micropython import const

_CENTER = const(120)
# The bubble stays clear of the rounded corners of the card it moves on.
_REACH = cards.SPAN // 2 - 16
# The menu is three stacked cards.
_ROW_H = cards.size(3)
_ROWS = cards.edges((_ROW_H,) * 3)

class LevelApp():
    NAME = "Level"
    # 1-bit RLE, 32x32, generated from apps/level/icon.png, 61 bytes
    ICON = (
        32, 32,
        b'\xff\x00"\x05\x01\x03\x02\x03\x02\x03\x01\x04\x01\x05\x01\x06'
        b'\x01\x03\x02\x03\x02\x03\x01\x04\x01\x0c\x01\x03\x02\x03\x02\x03'
        b'\x01\x04\x01\x0c\x01\x03\x02\x03\x02\x03\x01\x04\x01\x0c\x01\x04'
        b'\x01\x03\x01\x04\x01\x04\x01\xe6\x01\x1e\xff\x00B'
    )

    def __init__(self):
        self.old_xy = (0,0)
        self.calibration = (0,0)
        self.prompt = False
        self.calibrate = widgets.Button(cards.MARGIN, _ROWS[0], cards.SPAN,
                                        _ROW_H, 'Calibrate')
        self.reset = widgets.Button(cards.MARGIN, _ROWS[1], cards.SPAN,
                                    _ROW_H, 'Reset')
        self.cancel = widgets.Button(cards.MARGIN, _ROWS[2], cards.SPAN,
                                     _ROW_H, 'Cancel')

    def foreground(self):
        self.prompt = False # in case the watch went to sleep with prompt on
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH)
        wasp.system.request_tick(125)

    def _draw(self):
        draw = wasp.watch.drawable
        draw.fill(0)
        draw.rounded_rect(cards.MARGIN, cards.MARGIN, cards.SPAN, cards.SPAN,
                          cards.COLOR)
        self._update()

    def _update(self):
        if not self.prompt:
            draw = wasp.watch.drawable
            # Clear the old bubble
            draw.fill(cards.COLOR, self.old_xy[0] - 3 + _CENTER,
                      self.old_xy[1] - 3 + _CENTER, 6, 6)
            # Draw the guide lines inside the straight part of the card.
            mid = wasp.system.theme('mid')
            draw.fill(mid, cards.MARGIN + 12, _CENTER, cards.SPAN - 24, 1)
            draw.fill(mid, _CENTER, cards.MARGIN + 12, 1, cards.SPAN - 24)
            (new_x, new_y, _) = watch.accel.accel_xyz()
            # We clamp and scale the values down a bit to make them fit better,
            # and apply the calibration.
            # The scaling factor is negative because when gravity pulls in one
            # direction we want the bubble to go the other direction.
            new_x = min(_REACH, max(-_REACH, (new_x-self.calibration[0])//-3))
            new_y = min(_REACH, max(-_REACH, (new_y-self.calibration[1])//-3))
            # Draw the new bubble
            draw.fill(wasp.system.theme('bright'), new_x - 3 + _CENTER,
                      new_y - 3 + _CENTER, 6, 6)
            self.old_xy = (new_x, new_y)

    def tick(self, ticks):
        self._update()
        wasp.system.keep_awake()

    def touch(self, event):
        if self.prompt:
            # Handle buttons
            if self.calibrate.touch(event):
                (x, y, _) = watch.accel.accel_xyz()
                self.calibration = (x, y)
            if self.reset.touch(event):
                self.calibration = (0,0)
            #if self.cancel.touch(event):
            #    pass

            self.prompt = False
            self._draw()
        else:
            # Draw menu
            self.prompt = True
            wasp.watch.drawable.fill(0)
            self.calibrate.draw()
            self.reset.draw()
            self.cancel.draw()
