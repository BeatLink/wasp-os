# SPDX-License-Identifier: LGPL-3.0-or-later
"""Call screen
~~~~~~~~~~~~~~

Shows an incoming phone call: who is calling, with a Reject and an Accept
tile. A tile tells the phone to reject or answer the call, and the button
silences the watch while leaving the phone ringing.

Gadgetbridge opens this screen when a call arrives and closes it when the
call is answered or ends, importing it only while a call is showing.
"""

import wasp
import cards
import fonts

from gadgetbridge import send

# How many seconds the watch keeps buzzing for before it gives up.
_RING_SECONDS = 30

_TILE_COLOR = cards.COLOR
_MARGIN = cards.MARGIN

# One tall tile for the caller over a Reject and an Accept tile.
_ACTION_H = cards.size(3)
_ACTION_W = cards.size(2)
_CALLER_H = cards.SPAN - _ACTION_H - cards.GAP
_CALLER_Y, _ACTION_Y = cards.edges((_CALLER_H, _ACTION_H))
_ACTION_X = cards.edges((_ACTION_W, _ACTION_W))

_RED = 0xf800
_GREEN = 0x07e0


class CallApp():
    """Show an incoming call and answer it from the watch."""
    NAME = 'Call'

    def __init__(self, name, number):
        self._name = name or number or 'Unknown'
        self._number = number if name else ''
        self._rings = 0

    def foreground(self):
        """Activate the application."""
        self._rings = _RING_SECONDS
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH | wasp.EventMask.BUTTON)
        wasp.system.request_tick(1000)
        self._buzz()

    def tick(self, ticks):
        """Buzz once a second until the call is answered or the time runs out."""
        if self._rings > 0:
            self._rings -= 1
            self._buzz()

    def press(self, button, state):
        """Silence the watch and leave the phone ringing."""
        if state:
            self._answer('IGNORE')

    def touch(self, event):
        """Reject or accept the call from its tile."""
        if event[2] < _ACTION_Y:
            return
        self._answer('ACCEPT' if event[1] >= 120 else 'REJECT')

    def _buzz(self):
        wasp.watch.vibrator.pulse(duty=50, ms=200)
        wasp.system.keep_awake()

    def _answer(self, answer):
        """Tell the phone what to do with the call, then go back to the watch face."""
        self._rings = 0
        send({'t': 'call', 'n': answer})
        wasp.system.navigate(wasp.EventType.HOME)

    def _draw(self):
        draw = wasp.watch.drawable
        draw.fill(0)
        draw.rounded_rect(_MARGIN, _CALLER_Y, cards.SPAN, _CALLER_H, _TILE_COLOR)
        for x in _ACTION_X:
            draw.rounded_rect(x, _ACTION_Y, _ACTION_W, _ACTION_H, _TILE_COLOR)

        draw.set_color(wasp.system.theme('mid'), _TILE_COLOR)
        draw.set_font(fonts.sans18)
        draw.string('Incoming call', _MARGIN, _CALLER_Y + 16, width=cards.SPAN)

        draw.set_color(wasp.system.theme('bright'), _TILE_COLOR)
        draw.set_font(fonts.sans24)
        # A long name is cut to what fits on the tile.
        name = self._name
        end = draw.wrap(name, cards.SPAN - 16)[1]
        draw.string(name[:end].rstrip(), _MARGIN, _CALLER_Y + 56, width=cards.SPAN)
        if self._number:
            draw.set_font(fonts.sans18)
            draw.string(self._number, _MARGIN, _CALLER_Y + 92, width=cards.SPAN)

        draw.set_font(fonts.sans24)
        y = _ACTION_Y + (_ACTION_H - fonts.sans24.height()) // 2
        draw.set_color(_RED, _TILE_COLOR)
        draw.string('Reject', _ACTION_X[0], y, width=_ACTION_W)
        draw.set_color(_GREEN, _TILE_COLOR)
        draw.string('Accept', _ACTION_X[1], y, width=_ACTION_W)
