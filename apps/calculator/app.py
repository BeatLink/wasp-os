# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Johannes Wache
"""Calculator
~~~~~~~~~~~~~

This is a simple calculator app that uses the build-in eval() function to
compute the solution.

.. figure:: apps/calculator/screenshot.png
    :width: 179
"""

import wasp, fonts

# 1-bit RLE, 48x48, generated from apps/calculator/icon.png, 211 bytes
calc = (
    48, 48,
    b'\n\x1c\x12 \x0f"\x0e"\r$\x0c$\x0c\x07\x16\x07'
    b'\x0c\x06\x18\x06\x0c\x06\x18\x06\x0c\x06\x18\x06\x0c\x06\x18\x06'
    b'\x0c\x06\x18\x06\x0c\x06\x18\x06\x0c\x06\x18\x06\x0c\x07\x16\x07'
    b'\x0c$\x0c$\x0c$\x0c\x07\x04\x05\x04\x05\x04\x07\x0c\x06'
    b'\x06\x03\x06\x03\x06\x06\x0c\x06\x06\x03\x06\x03\x06\x06\x0c\x06'
    b'\x06\x03\x06\x03\x06\x06\x0c\x06\x06\x03\x06\x03\x06\x06\x0c\x07'
    b'\x04\x05\x04\x05\x04\x07\x0c$\x0c$\x0c$\x0c\x07\x04\x05'
    b'\x04\x05\x04\x07\x0c\x06\x06\x03\x06\x03\x06\x06\x0c\x06\x06\x03'
    b'\x06\x03\x06\x06\x0c\x06\x06\x03\x06\x03\x06\x06\x0c\x06\x06\x03'
    b'\x06\x03\x06\x06\x0c\x07\x04\x05\x04\x05\x04\x07\x0c$\x0c$'
    b'\x0c$\x0c\x07\r\x05\x04\x07\x0c\x06\x0f\x03\x06\x06\x0c\x06'
    b'\x0f\x03\x06\x06\x0c\x06\x0f\x03\x06\x06\x0c\x06\x0f\x03\x06\x06'
    b'\x0c\x07\r\x05\x04\x07\x0c$\x0c$\r"\x0e"\x0f '
    b'\x12\x1c\n'
)

fields = ( '789+('
           '456-)'
           '123*^'
           'C0./=' )

class CalculatorApp():
    NAME = 'Calc'
    ICON = calc

    def __init__(self):
        self.output = ""

    def foreground(self):
        self._draw()
        self._update()
        wasp.system.request_event(wasp.EventMask.TOUCH)

    def touch(self, event):
        if (event[2] < 48):
            if (event[1] > 200): # undo button pressed
                if (self.output != ""):
                    self.output = self.output[:-1]
        else:
            x = event[1] // 47
            y = (event[2] // 48) - 1

            # Error handling for touching at the border
            if x > 4:
                x = 4
            if y > 3:
                y = 3
            button_pressed = fields[x + 5*y]
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
        line = draw.line
        fill = draw.fill

        hi = theme('bright')
        lo = theme('mid')
        mid = draw.lighten(lo, 2)
        bg = draw.darken(theme('ui'), theme('contrast'))
        bg2 = draw.darken(bg, 2)

        # Draw the background
        fill(0, 0, 0, 239, 47)
        fill(0, 236, 239, 3)
        fill(bg, 141, 48, 239-141, 236-48)
        fill(bg2, 0, 48, 141, 236-48)

        # Make grid:
        draw.set_color(lo)
        for i in range(4):
            # horizontal lines
            line(x0=0,y0=(i+1)*47,x1=239,y1=(i+1)*47)
            # vertical lines
            line(x0=(i+1)*47,y0=47,x1=(i+1)*47,y1=235)
        line(x0=0, y0=47, x1=0, y1=236)
        line(x0=239, y0=47, x1=239, y1=236)
        line(x0=0, y0=236, x1=239, y1=236)

        # Draw button labels
        draw.set_color(hi, bg2)
        for x in range(5):
            if x == 3:
                draw.set_color(mid, bg)
            for y in range(4):
                label = fields[x + 5*y]
                if (x == 0):
                    draw.string(label, x*47+14, y*47+60)
                else:
                    draw.string(label, x*47+16, y*47+60)
        draw.set_color(hi)
        draw.string("<", 215, 10)
    
    def _update(self):
        output = self.output if len(self.output) < 12 else self.output[len(self.output)-12:]
        wasp.watch.drawable.string(output, 0, 14, width=200, right=True)
