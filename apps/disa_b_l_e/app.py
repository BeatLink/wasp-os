# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2021 Francesco Gazzetta

"""DisaBLE
~~~~~~~~~~

Disable BLE to save energy and enhance privacy.

This app shows the bluetooth status and provides a button to disable/enable it.
Unfortunately, re-enabling bluetooth normally has some issues, so as a
workaround the "enable" button restarts the watch.

.. figure:: apps/disa_b_l_e/screenshot.png
    :width: 179
"""

import wasp
import widgets
import ble

class DisaBLEApp():
    NAME = 'DisaBLE'
    # 1-bit RLE, 48x48, generated from apps/disa_b_l_e/icon.png, 193 bytes
    ICON = (
        48, 48,
        b'\x13\n#\x10\x1d\x16\x18\x19\x16\x1c\x13\x1e\x11\x0c\x08\x0c'
        b'\x0f\n\x0e\n\r\t\x12\t\x0b\t\x15\x08\t\x0b\x15\x08'
        b'\x07\r\x15\x07\x07\x0e\x15\x07\x05\x10\x15\x06\x05\x07\x01\t'
        b'\x14\x07\x04\x06\x03\t\x14\x06\x03\x07\x04\t\x13\x07\x02\x06'
        b'\x06\t\x13\x06\x02\x06\x07\t\x12\x06\x01\x07\x08\t\x11\x06'
        b'\x01\x06\n\t\x11\x0c\x0b\t\x10\x0c\x0c\t\x0f\x0c\r\t'
        b'\x0e\x0c\x0e\t\r\x0c\x0f\t\x0c\x0c\x10\t\x0b\x0c\x11\t'
        b'\n\r\x11\t\x08\x06\x02\x06\x12\t\x07\x06\x02\x06\x13\t'
        b'\x06\x06\x02\x07\x13\t\x04\x07\x03\x06\x14\t\x03\x06\x04\x07'
        b'\x14\t\x01\x07\x04\x07\x15\x0f\x06\x07\x15\x0e\x06\x08\x15\x0c'
        b'\x08\x08\x15\x0b\t\x08\x15\t\x0b\t\x12\t\r\n\x0e\n'
        b'\x0f\x0c\x08\x0c\x11\x1e\x13\x1c\x15\x19\x19\x16\x1d\x10#\n'
        b'\x13'
    )

    def foreground(self):
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH)

    def _draw(self):
        draw = wasp.watch.drawable
        draw.set_color(wasp.system.theme('bright'))
        draw.fill()
        draw.string('BLE status: ' + ('ON' if ble.enabled() else 'OFF'), 0, 60, width=240)
        self._btn = widgets.Button(10, 120, 220, 80, 'Disable' if ble.enabled() else 'Reboot to enable')
        self._btn.draw()

    def touch(self, event):
        if self._btn.touch(event):
            if ble.enabled():
                ble.disable()
                self._draw()
            else:
                wasp.machine.reset()
        else:
            self._draw()
