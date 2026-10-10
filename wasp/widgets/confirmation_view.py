# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Confirmation view widget
~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import cards
import fonts
import wasp

from widgets.button import Button

# One tall card for the question over a row of two answers, as on the
# alarm summary page.
_ANSWER_W = cards.size(2)
_ANSWER_H = cards.size(3)
_QUESTION_H = cards.SPAN - _ANSWER_H - cards.MARGIN
_QUESTION_Y, _ANSWER_Y = cards.edges((_QUESTION_H, _ANSWER_H))
_YES_X, _NO_X = cards.edges((_ANSWER_W, _ANSWER_W))

class ConfirmationView:
    """Confirmation widget allowing user confirmation of a setting."""

    def __init__(self):
        self.active = False
        self.value = False
        self._yes = Button(_YES_X, _ANSWER_Y, _ANSWER_W, _ANSWER_H, 'Yes')
        self._no = Button(_NO_X, _ANSWER_Y, _ANSWER_W, _ANSWER_H, 'No')

    def draw(self, message):
        draw = wasp.watch.drawable
        mute = wasp.watch.display.mute

        mute(True)
        draw.fill(0)
        draw.rounded_rect(cards.MARGIN, _QUESTION_Y, cards.SPAN, _QUESTION_H,
                          cards.COLOR)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans24)
        width = cards.SPAN - 24
        chunks = draw.wrap(message, width)
        lines = len(chunks) - 1
        y = _QUESTION_Y + (_QUESTION_H - lines * 26) // 2
        for i in range(lines):
            draw.string(message[chunks[i]:chunks[i+1]].strip(),
                        cards.MARGIN + 12, y + i * 26, width=width)
        self._yes.draw()
        self._no.draw()
        mute(False)

        self.active = True

    def touch(self, event):
        if not self.active:
            return False

        if self._yes.touch(event):
            self.active = False
            self.value = True
            return True
        elif self._no.touch(event):
            self.active = False
            self.value = False
            return True

        return False
