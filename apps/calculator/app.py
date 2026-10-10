# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Johannes Wache
"""Calculator
~~~~~~~~~~~~~

This is a simple calculator app that uses the build-in eval() function to
compute the solution.

.. figure:: apps/calculator/screenshot.png
    :width: 179
"""

import wasp
import cards
import fonts

# 1-bit RLE, 32x32, generated from apps/calculator/icon.png, 141 bytes
calc = (
    32, 32,
    b'\x06\x14\x0b\x16\t\x18\x08\x18\x08\x05\x0e\x05\x08\x04\x10\x04'
    b'\x08\x04\x10\x04\x08\x04\x10\x04\x08\x04\x10\x04\x08\x05\x0e\x05'
    b'\x08\x18\x08\x18\x08\x05\x02\x04\x02\x04\x02\x05\x08\x04\x04\x02'
    b'\x04\x02\x04\x04\x08\x04\x04\x02\x04\x02\x04\x04\x08\x05\x02\x04'
    b'\x02\x04\x02\x05\x08\x18\x08\x18\x08\x05\x02\x04\x02\x04\x02\x05'
    b'\x08\x04\x04\x02\x04\x02\x04\x04\x08\x04\x04\x02\x04\x02\x04\x04'
    b'\x08\x05\x02\x04\x02\x04\x02\x05\x08\x18\x08\x18\x08\x05\x08\x04'
    b'\x02\x05\x08\x04\n\x02\x04\x04\x08\x04\n\x02\x04\x04\x08\x05'
    b'\x08\x04\x02\x05\x08\x18\x08\x18\t\x16\x0b\x14\x06'
)

fields = ( '789+('
           '456-)'
           '123*^'
           'C0./=' )

# Five rows of five cards: the display and undo, then four rows of keys.
_KEY = cards.size(5)
_LEFTS = cards.edges((_KEY,) * 5)
_TOPS = cards.edges((_KEY,) * 5)
_PITCH = _LEFTS[1] - _LEFTS[0]
_DISPLAY_W = _LEFTS[3] + _KEY - cards.MARGIN
# Where a label sits within a key.
_TEXT_Y = (_KEY - 24) // 2

class CalculatorApp():
    NAME = 'Calc'
    ICON = calc

    def __init__(self):
        self.output = ""

    def save(self):
        """Keep what has been typed for when the app is opened again."""
        return self.output

    def restore(self, saved):
        self.output = saved

    def foreground(self):
        self._draw()
        self._update()
        wasp.system.request_event(wasp.EventMask.TOUCH)

    def touch(self, event):
        x = min(max(event[1] - cards.MARGIN, 0) // _PITCH, 4)
        y = min(max(event[2] - cards.MARGIN, 0) // _PITCH, 4)
        if y == 0:
            if x == 4: # undo button pressed
                if (self.output != ""):
                    self.output = self.output[:-1]
        else:
            button_pressed = fields[x + 5*(y-1)]
            if (button_pressed == "C"):
                self.output = ""
            elif (button_pressed == "="):
                try:
                    self.output = str(eval(self.output.replace('^', '**')))[:12]
                except:
                    wasp.watch.vibrator.pulse()
            else:
                self.output +=  button_pressed
        self._update()

    def _draw(self):
        draw = wasp.watch.drawable
        theme = wasp.system.theme

        hi = theme('bright')
        op = draw.lighten(theme('ui'), theme('contrast'))
        accent = theme('ui')

        draw.fill(0)
        draw.set_font(fonts.sans24)
        draw.rounded_rect(cards.MARGIN, _TOPS[0], _DISPLAY_W, _KEY, cards.COLOR)
        draw.rounded_rect(_LEFTS[4], _TOPS[0], _KEY, _KEY, cards.COLOR)
        draw.set_color(hi, cards.COLOR)
        draw.string("<", _LEFTS[4], _TOPS[0] + _TEXT_Y, width=_KEY)

        # Digits in white, operators in the accent, and = filled with it.
        for y in range(4):
            for x in range(5):
                label = fields[x + 5*y]
                bg = accent if label == '=' else cards.COLOR
                if label == '=' or label in '0123456789.':
                    fg = hi
                elif label == 'C':
                    fg = theme('mid')
                else:
                    fg = op
                draw.rounded_rect(_LEFTS[x], _TOPS[y+1], _KEY, _KEY, bg)
                draw.set_color(fg, bg)
                draw.string(label, _LEFTS[x], _TOPS[y+1] + _TEXT_Y, width=_KEY)

    def _update(self):
        draw = wasp.watch.drawable
        output = self.output if len(self.output) < 12 else self.output[len(self.output)-12:]
        draw.set_font(fonts.sans24)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        # Keep the padding inside the straight part of the card.
        draw.string(output, cards.MARGIN + 12, _TOPS[0] + _TEXT_Y,
                    width=_DISPLAY_W - 24, right=True)
