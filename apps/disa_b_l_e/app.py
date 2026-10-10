# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2021 Francesco Gazzetta

"""DisaBLE
~~~~~~~~~~

Disable BLE to save energy and enhance privacy.

This app shows the bluetooth status and provides a button to disable/enable it.
Unfortunately, re-enabling bluetooth normally has some issues, so as a
workaround the "enable" button restarts the watch.

The top card shows whether Bluetooth is on and the bottom card turns it off,
or restarts the watch to turn it back on.

.. figure:: apps/disa_b_l_e/screenshot.png
    :width: 179
"""

import wasp
import cards
import fonts
import widgets
import ble

# A status card above the action card.
_CARD_H = cards.size(2)
_STATUS_Y, _ACTION_Y = cards.edges((_CARD_H, _CARD_H))

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
        on = ble.enabled()
        fg = wasp.system.theme('bright') if on else wasp.system.theme('mid')
        draw.fill(0)
        draw.rounded_rect(cards.MARGIN, _STATUS_Y, cards.SPAN, _CARD_H,
                          cards.COLOR)
        draw.rleblit(self.ICON, (104, _STATUS_Y + 18), fg, cards.COLOR)
        draw.set_color(fg, cards.COLOR)
        draw.set_font(fonts.sans24)
        draw.string('BLE is ' + ('on' if on else 'off'), cards.MARGIN + 12,
                    _STATUS_Y + 62, width=cards.SPAN - 24)
        self._btn = widgets.Button(cards.MARGIN, _ACTION_Y, cards.SPAN, _CARD_H,
                                   'Disable' if on else 'Reboot to enable')
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
