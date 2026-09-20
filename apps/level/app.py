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
import watch
import widgets
from micropython import const

_X_MAX = const(240)
_Y_MAX = const(240)
_X_CENTER = const(120)
_Y_CENTER = const(120)

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
        self.calibrate = widgets.Button(20, 20, 200, 60, 'Calibrate')
        self.reset = widgets.Button(20, 90, 200, 60, 'Reset')
        self.cancel = widgets.Button(20, 160, 200, 60, 'Cancel')

    def foreground(self):
        self.prompt = False # in case the watch went to sleep with prompt on
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH)
        wasp.system.request_tick(125)

    def _draw(self):
        wasp.watch.drawable.fill()
        self._update()

    def _update(self):
        if not self.prompt:
            draw = wasp.watch.drawable
            # Clear the old bubble
            draw.fill(None, self.old_xy[0] - 3 + _X_CENTER, self.old_xy[1] - 3 + _Y_CENTER, 6, 6)
            # draw guide lines
            draw.line(0, _Y_CENTER, _X_MAX, _Y_CENTER, color = wasp.system.theme('mid'))
            draw.line(_X_CENTER, 0, _X_CENTER, _Y_MAX, color = wasp.system.theme('mid'))
            (new_x, new_y, _) = watch.accel.accel_xyz()
            # We clamp and scale the values down a bit to make them fit better,
            # and apply the calibration.
            # The scaling factor is negative because when gravity pulls in one
            # direction we want the bubble to go the other direction.
            new_x = min(_X_CENTER, max(-_X_CENTER, (new_x-self.calibration[0])//-3))
            new_y = min(_Y_CENTER, max(-_Y_CENTER, (new_y-self.calibration[1])//-3))
            # Draw the new bubble
            draw.fill(wasp.system.theme('bright'), new_x - 3 + _X_CENTER, new_y - 3 + _Y_CENTER, 6, 6)
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

            # reset the color (buttons set it to blue) and disable prompt
            wasp.watch.drawable.set_color(wasp.system.theme('bright'))
            self.prompt = False
            self._draw()
        else:
            # Draw menu
            self.prompt = True
            wasp.watch.drawable.fill()
            self.calibrate.draw()
            self.reset.draw()
            self.cancel.draw()
