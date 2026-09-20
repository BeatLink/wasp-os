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
    # 1-bit RLE, 32x32, generated from apps/disa_b_l_e/icon.png, 129 bytes
    ICON = (
        32, 32,
        b'\x0c\x08\x15\x0e\x10\x11\x0e\x14\x0b\x08\x06\x08\t\x06\x0c\x06'
        b'\x07\x06\x0e\x06\x05\x08\x0e\x05\x05\t\x0e\x05\x03\x05\x01\x05'
        b'\x0e\x04\x03\x04\x03\x05\x0e\x04\x02\x04\x04\x05\r\x04\x01\x05'
        b'\x05\x05\x0c\x04\x01\x04\x07\x05\x0c\x08\x08\x05\x0b\x08\t\x05'
        b'\n\x08\n\x05\t\x08\x0b\x05\x08\x08\x0c\x05\x07\x08\r\x05'
        b'\x05\x04\x02\x04\r\x05\x04\x04\x02\x04\r\x06\x03\x04\x02\x05'
        b'\r\x06\x01\x04\x04\x05\r\n\x04\x05\x0e\x08\x06\x06\r\x07'
        b'\x07\x06\x0c\x06\t\x08\x06\x08\x0b\x14\r\x11\x11\x0e\x15\x08'
        b'\x0c'
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
