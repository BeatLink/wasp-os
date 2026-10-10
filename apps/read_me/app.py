# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2021 Daniel Thompson
"""Example of any automatically discovered application.

Any python file (``.py`` or ``.mpy``) discovered in the ``apps/``
directory will be automatically added to the Software application.
"""

import cards
import fonts
import wasp
from micropython import const

# 1-bit RLE, 32x32, generated from apps/read_me/icon.png, 61 bytes
icon = (
    32, 32,
    b'd\x07\n\x07\x05\r\x04\r\x01\x0f\x02\x1e\x02\x1e\x02\x1e'
    b'\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e'
    b'\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e'
    b'\x02\x1e\x02\x1e\x02\x12\n\x02\x02\x02\n\x03\x80'
)

# Inset that keeps padded text clear of the card's rounded corners.
_INSET = const(12)

class ReadMeApp():
    NAME = "ReadMe"
    ICON = icon

    def foreground(self):
        draw = wasp.watch.drawable
        draw.fill(0)
        draw.rounded_rect(cards.MARGIN, cards.MARGIN, cards.SPAN, cards.SPAN,
                          cards.COLOR)
        fg = wasp.system.theme('bright')
        draw.rleblit(icon, (104, 56), fg, cards.COLOR)
        draw.set_color(fg, cards.COLOR)
        draw.set_font(fonts.sans24)
        x = cards.MARGIN + _INSET
        w = cards.SPAN - 2 * _INSET
        draw.string('Autoloaded from', x, 112, width=w)
        draw.set_color(wasp.system.theme('mid'), cards.COLOR)
        draw.string('apps/read_me.py', x, 144, width=w)
