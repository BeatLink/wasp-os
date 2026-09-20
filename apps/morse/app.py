# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2021 Francesco Gazzetta

"""Morse translator and notepad
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This app is a simple morse translator that also doubles as a notepad.
Swipe up for a line, swipe down for a dot, tap for end letter, double tap for
end word. Swipe right for space, twice for newline. Swipe left to delete
character.
Up to 7 lines of translation will be displayed on a 240x240 screen, and old
lines will be deleted.
There is a preview of the next letter at the bottom of the screen.


.. figure:: apps/morse/screenshot.png
    :width: 179
"""

import wasp
import icons
import fonts
from math import floor
from micropython import const


_WIDTH = const(240)
_HEIGHT = const(240)
# No easy way to make this depend on _WIDTH
_MAXINPUT = const(16)

# These two need to match
_FONTH = const(24)
_FONT = fonts.sans24

# Precomputed for efficiency
_LINEH = const(30) # int(_FONTH * 1.25)
_MAXLINES = const(7) # floor(_HEIGHT / _LINEH) - 1 # the "-1" is the input line

# The morse lookup table, represented as a flattened binary tree.
# The head is the value of the node, the tail are the subtrees:
# left half of the tail = the next symbol is a dot
# right half of the tail = the next symbol is a line
_CODE = " eish54v?3uf????2arl?????wp??j?1tndb6?x??kc??y??mgz7?q??o?8??90"
# uppercase:
#_CODE = " EISH54V?3UF????2ARL?????WP??J?1TNDB6?X??KC??Y??MGZ7?Q??O?8??90"
# letters only:
#_CODE = " EISHVUF?ARL?WPJTNDBXKCYMGZQO??"

class MorseApp():
    NAME = 'Morse'
    # 1-bit RLE, 48x48, generated from apps/morse/icon.png, 233 bytes
    ICON = (
        48, 48,
        b'c\x03$\x03\x05\x05"\x05\x03\x06"\x06\x02\x06\x04\x01'
        b'\x18\x01\x04\x06\x02\x05\x04\x04\x14\x04\x04\x05\x02\x05\x04\x04'
        b'\t\x02\t\x04\x04\x05\x01\x06\x03\x04\x08\x06\x08\x04\x03\x0c'
        b'\x03\x04\x07\x08\x07\x04\x03\x0b\x04\x04\x06\n\x06\x04\x04\n'
        b'\x04\x04\x06\n\x06\x04\x04\n\x04\x04\x06\n\x06\x04\x04\n'
        b'\x04\x04\x06\n\x06\x04\x04\n\x04\x04\x06\n\x06\x04\x04\x0b'
        b'\x03\x04\x06\n\x06\x04\x03\x0c\x03\x04\x06\n\x06\x04\x03\x0c'
        b'\x03\x05\x05\n\x05\x05\x03\x06\x01\x05\x04\x04\x04\x0c\x04\x04'
        b'\x04\x05\x02\x06\x03\x03\x05\x0c\x05\x03\x03\x06\x02\x06\x0b\x05'
        b'\x02\x05\x0b\x06\x03\x05\n\x06\x02\x06\n\x05\x04\x04\x0b\x05'
        b'\x04\x05\x0b\x04\x12\x06\x04\x06 \x06\x04\x06\x1f\x06\x06\x06'
        b'\x1e\x12\x1d\x14\x1c\x14\x1b\x16\x1a\x16\x1a\x06\n\x06\x19\x06'
        b'\x0c\x06\x18\x06\x0c\x06\x17\x1a\x16\x1a\x15\x1c\x14\x1c\x13\x1e'
        b'\x12\x06\x12\x06\x11\x06\x14\x06\x10\x06\x14\x06\x10\x05\x16\x05'
        b'\x10\x05\x16\x05\x12\x02\x18\x02\x9a'
    )

    def __init__(self):
        self.letter = ""
        self.text = [""]

    def foreground(self):
        try:
            f = open("Morse.txt", "r")
            text = "".join(f.readlines()).replace("\n", "%").replace("%%", "%")
            f.close()
            text = text.split("%")
            if len(text) > _MAXLINES:
                text = text[-_MAXLINES:]
            self.text = text
        except:
            self.text = [""]
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.SWIPE_LEFTRIGHT |
                                  wasp.EventMask.SWIPE_UPDOWN)

    def background(self):
        text = "%".join(self.text)
        f = open("Morse.txt", "w")
        for line in text:
            f.write(line)
        f.close()

    def swipe(self, event):
        if event[0] == wasp.EventType.LEFT:
            if self.letter == "":
                if self.text[-1] == "" and len(self.text) > 1:
                    self.text.pop(-1)
                else:
                    self.text[-1] = str(self.text[-1])[:-1]
            self.letter = ""
            self.text[-1] = "{}  ".format(self.text[-1])  # adds space, otherwise the screen will not be erased there
            self._update()
            self.text[-1] = str(self.text[-1])[:-2]  # removes space
        elif event[0] == wasp.EventType.RIGHT:
            if self.text[-1].endswith(" "):
                self.text.append("")
                self._draw()
            else:
                self._add_letter(" ")
        else:
            if len(self.letter) < _MAXINPUT:
                self.letter += "-" if event[0] == wasp.EventType.UP else "."
                self._update()

    def touch(self, event):
        self._add_letter(self._lookup(self.letter))

    def _add_letter(self, addition):
        merged = self.text[-1] + addition
        # Check if the new text overflows the screen and add a new line if that's the case
        split = wasp.watch.drawable.wrap(merged, _WIDTH)
        if len(split) > 2:
            self.text.append(self.text[-1][split[1]:split[2]] + addition)
            self.text[-2] = self.text[-2][split[0]:split[1]]
            if len(self.text) > _MAXLINES:
                self.text.pop(0)
            # Ideally a full refresh should be done only when we exceed
            # _MAXLINES, but this should be fast enough
            self._draw()
        else:
            self.text[-1] = merged
        self.letter = ""
        self._update()

    def _draw(self):
        """Draw the display from scratch"""
        draw = wasp.watch.drawable
        draw.fill()
        i = 0
        for line in self.text:
            draw.string(line, 0, _LINEH * i)
            i += 1
        self._update()

    def _update(self):
        """Update the dynamic parts of the application display, specifically the
        input line and last line of the text.
        The full text area is updated in _draw() instead."""
        draw = wasp.watch.drawable
        draw.string(self.text[-1], 0, _LINEH*(len(self.text)-1))
        guess = self._lookup(self.letter)
        draw.string("{} {}".format(self.letter, guess), 0, _HEIGHT - _FONTH, width=_WIDTH)

    def _lookup(self, s):
        i = 0 # start of the subtree (current node)
        l = len(_CODE) # length of the subtree

        for c in s:
            # first discard the head, which represent the previous guess
            i += 1
            l -= 1

            # Check if we can no longer bisect while there are still dots/lines
            if l <= 0: return "?"

            # Update the bounds to the appropriate subtree
            # (left or right of the tail).
            # The length will always be half:
            l //= 2
            # The index will be either at the beginning of the tail,
            # or at its half, in which case we subtract the current length,
            # which is half of the old length:
            if c == "-": i += l
        return _CODE[i]
