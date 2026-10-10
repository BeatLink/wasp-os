# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2021 Francesco Gazzetta

"""Morse translator and notepad
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This app is a simple morse translator that also doubles as a notepad.
Swipe up for a line, swipe down for a dot, tap for end letter, double tap for
end word. Swipe right for space, twice for newline. Swipe left to delete
character.
Up to 6 lines of translation are shown on the top card, and old lines are
deleted. The card below previews the dots and lines entered so far and the
letter they make.


.. figure:: apps/morse/screenshot.png
    :width: 179
"""

import wasp
import cards
import fonts
from micropython import const


# The text card fills the screen above a short card for the letter being keyed.
_INPUT_H = cards.size(4)
_TEXT_H = cards.SPAN - _INPUT_H - cards.GAP
_TEXT_Y, _INPUT_Y = cards.edges((_TEXT_H, _INPUT_H))
# Text keeps clear of the rounded corners of its card.
_TEXT_X = const(16)
_WIDTH = const(208)
# The longest run of dots and lines the preview has room for.
_MAXINPUT = const(16)

_FONTH = const(24)
_LINEH = const(26)
_MAXLINES = const(6)
_TOP = _TEXT_Y + (_TEXT_H - _LINEH * _MAXLINES) // 2 + 1

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
    # 1-bit RLE, 32x32, generated from apps/morse/icon.png, 153 bytes
    ICON = (
        32, 32,
        b'"\x02\x18\x02\x03\x04\x16\x04\x02\x03\x03\x02\x0e\x02\x03\x03'
        b'\x01\x04\x02\x03\x0e\x03\x02\x08\x02\x03\x05\x04\x05\x03\x02\x08'
        b'\x02\x03\x04\x06\x04\x03\x02\x08\x02\x02\x05\x06\x05\x02\x02\x08'
        b'\x02\x02\x04\x08\x04\x02\x02\x08\x02\x03\x04\x06\x04\x03\x02\x08'
        b'\x02\x03\x04\x06\x04\x03\x02\x08\x02\x03\x04\x06\x04\x03\x02\x04'
        b'\x01\x03\x03\x02\x03\x08\x03\x02\x03\x03\x02\x04\x07\x03\x02\x03'
        b'\x07\x04\x02\x03\x07\x04\x02\x04\x07\x03\x0c\x04\x02\x04\x15\x04'
        b'\x04\x04\x14\x0c\x13\x0e\x12\x0e\x12\x0e\x11\x04\x08\x04\x10\x04'
        b'\x08\x04\x0f\x12\x0e\x12\r\x14\x0c\x04\x0c\x04\x0b\x04\x0e\x04'
        b'\n\x04\x0e\x04\x0b\x02\x10\x02F'
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
            self._update()
        elif event[0] == wasp.EventType.RIGHT:
            if self.text[-1].endswith(" "):
                self.text.append("")
                if len(self.text) > _MAXLINES:
                    self.text.pop(0)
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
        draw.fill(0)
        draw.rounded_rect(cards.MARGIN, _TEXT_Y, cards.SPAN, _TEXT_H,
                          cards.COLOR)
        draw.rounded_rect(cards.MARGIN, _INPUT_Y, cards.SPAN, _INPUT_H,
                          cards.COLOR)
        draw.set_font(fonts.sans24)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        for i, line in enumerate(self.text[:-1]):
            draw.string(self._fit(line), _TEXT_X, _TOP + _LINEH * i)
        self._update()

    def _update(self):
        """Update the dynamic parts of the application display, specifically the
        input line and last line of the text.
        The full text area is updated in _draw() instead."""
        draw = wasp.watch.drawable
        draw.set_font(fonts.sans24)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        self._left(self._fit(self.text[-1]),
                   _TOP + _LINEH*(len(self.text)-1), _WIDTH)
        y = _INPUT_Y + (_INPUT_H - _FONTH) // 2
        draw.string(self._lookup(self.letter), _TEXT_X + _WIDTH - 40, y,
                    width=40, right=True)
        draw.set_color(wasp.system.theme('mid'), cards.COLOR)
        self._left(self.letter, y, _WIDTH - 40)

    def _left(self, s, y, width):
        """Draw a string at the left of the card and blank the rest of its row."""
        draw = wasp.watch.drawable
        w = fonts.width(fonts.sans24, s) if s else 0
        draw.string(s, _TEXT_X, y)
        draw.fill(cards.COLOR, _TEXT_X + w, y, width - w, _FONTH)

    def _fit(self, line):
        """Cut a line saved by a wider layout down to what fits on the card."""
        chunks = wasp.watch.drawable.wrap(line, _WIDTH)
        return line[:chunks[1]] if len(chunks) > 1 else line

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
