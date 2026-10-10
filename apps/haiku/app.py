# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Haiku viewer
~~~~~~~~~~~~~~~

These three lines poems are fun to write and fit nicely on a tiny screen.

.. figure:: apps/haiku/screenshot.png
    :width: 179

If there is a file called haiku.txt in the flash filesystem then this app
shows the next verse from it each time it is opened, one line to a card.
Verses are three lines each, followed by a blank line.

This application also (optionally) loads an icon from the filesystem allowing
to be customized to match whether theme your verses are based around.
"""


import wasp
import cards
import fonts

from micropython import const

# 1-bit RLE, 32x32, generated from apps/haiku/icon.png, 89 bytes
icon = (
    32, 32,
    b'\x19\x05\x17\n\x12\x0e\x10\x10\x0e\x12\x0c\x14\x0b\x14\n\x16'
    b'\t\x17\x08\x18\x08\x17\x08\x18\x07\x0b\x01\r\x07\n\x02\r'
    b'\x07\t\x02\r\x07\t\x02\r\x08\x08\x02\x0b\x0b\x07\x02\n'
    b'\r\x06\x02\x0f\t\x05\x02\x10\t\x04\x02\x10\n\x03\x02\x0f'
    b'\r\x01\x02\r\x12\x0c\x13\x0f\x10\x10\x0f\x0f\x10\x05\x02\x07'
    b'\x11\x05\x1a\x05\x1b\x04\x1c\x03\x1d'
)

# One card per line of the verse.
_CARD_H = cards.size(3)
_CARD_Y = cards.edges((_CARD_H,) * 3)
# Text keeps clear of the rounded corners of its card.
_TEXT_X = const(16)
_TEXT_W = const(208)

class HaikuApp():
    NAME = 'Haiku'
    ICON = icon

    def __init__(self):
        # Throw an exception if there is no poetry for us to read...
        open('haiku.txt').close()

        try:
            with open('haiku.rle', 'rb') as f:
                self.ICON = f.read()
        except:
            # Leave the default app icon if none is present
            pass

        self._counter = -4

    def foreground(self):
        self._counter += 4

        with open('haiku.txt') as f:
            for i in range(self._counter):
                _ = f.readline()
            lines = [f.readline() for i in range(3)]

            if len(lines[1]) == 0:
                self._counter = 0
                f.seek(0)
                lines = [f.readline() for i in range(3)]

        self._draw(lines)
        wasp.system.request_event(wasp.EventMask.SWIPE_UPDOWN)

    def swipe(self, event):
        """Swipe up to leave, as the last page of a pager does."""
        if event[0] == wasp.EventType.UP:
            wasp.system.navigate(wasp.EventType.BACK)
        else:
            wasp.watch.vibrator.pulse()

    def _draw(self, lines):
        draw = wasp.watch.drawable
        draw.fill(0)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        for (y, line) in zip(_CARD_Y, lines):
            draw.rounded_rect(cards.MARGIN, y, cards.SPAN, _CARD_H,
                              cards.COLOR)
            line = line.strip()
            # A line too long for two rows drops to the smaller font.
            for (font, pitch) in ((fonts.sans24, 26), (fonts.sans18, 19)):
                draw.set_font(font)
                chunks = draw.wrap(line, _TEXT_W)
                rows = len(chunks) - 1
                if rows * pitch <= _CARD_H - 18:
                    break
            rows = min(rows, (_CARD_H - 18) // pitch)
            top = y + (_CARD_H - rows * pitch) // 2 + 1
            for i in range(rows):
                sub = line[chunks[i]:chunks[i+1]].rstrip()
                draw.string(sub, _TEXT_X, top + i * pitch, width=_TEXT_W)
