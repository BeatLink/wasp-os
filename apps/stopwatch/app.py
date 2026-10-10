# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Stopwatch
~~~~~~~~~~~~

Simple stop/start watch with support for split times.

The time sits on the top card and the latest splits on the one below it.
The bottom row holds a card that takes a split, or clears a stopped watch,
and one that starts and stops it, as the button also does.

.. figure:: apps/stopwatch/screenshot.png
    :width: 179
"""
import wasp
import cards
import fonts

# 1-bit RLE, 32x32, generated from apps/stopwatch/icon.png, 89 bytes
icon = (
    32, 32,
    b'\x0c\x08\x17\n\x16\n\x17\x08\x1a\x04\x1c\x04\x1a\x08\x16\x0c'
    b'\x04\x02\x0c\x10\x01\x04\n\x16\t\x16\t\n\x02\n\n\t'
    b'\x04\t\t\x0b\x02\x0b\x08\x0b\x02\x0b\x07\x0c\x02\x0c\x06\x0c'
    b'\x02\x0c\x06\x0c\x02\x0c\x06\x0c\x02\x0c\x06\x0b\x04\x0b\x06\x0c'
    b'\x02\x0c\x06\x1a\x06\x1a\x07\x18\x08\x18\t\x16\n\x16\x0b\x14'
    b'\r\x12\x0f\x10\x12\x0c\x16\x08\x0c'
)

# Three rows of cards: the time, the splits, and the two actions.
_ROW_H = cards.size(3)
_TIME_Y, _SPLITS_Y, _ACTION_Y = cards.edges((_ROW_H,) * 3)
_ACTION_W = cards.size(2)
_ACTION_X = cards.edges((_ACTION_W, _ACTION_W))
# How many splits fit on their card, one line each.
_SPLITS = 3
_SPLIT_PITCH = 20

class StopwatchApp():
    """Stopwatch application."""
    # Stopwatch requires too many pixels to fit into the launcher

    NAME = 'Stopclock'
    ICON = icon

    def __init__(self):
        self._timer = wasp.widgets.Stopwatch(_TIME_Y + (_ROW_H - 36) // 2,
                                             cards.COLOR)
        self._reset()

    def foreground(self):
        """Activate the application."""
        self._draw()
        wasp.system.request_tick(97)
        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.BUTTON |
                                  wasp.EventMask.NEXT)

    def sleep(self):
        return True

    def wake(self):
        self._update()

    def swipe(self, event):
        """Handle NEXT events by augmenting the default processing by resetting
        the count if we are not currently timing something.

        No other swipe event is possible for this application.
        """
        if not self._timer._started_at:
            self._reset()
        return True     # Request system default handling

    def press(self, button, state):
        if not state:
            return

        self._start_stop()

    def _start_stop(self):
        if self._timer.started:
            self._timer.stop()
        else:
            self._timer.start()
        self._draw_actions()

    def touch(self, event):
        if event[2] >= _ACTION_Y and event[1] >= _ACTION_X[1]:
            self._start_stop()
            self._update()
            return

        if self._timer.started:
            self._splits.insert(0, self._timer.count)
            del self._splits[_SPLITS:]
            self._nsplits += 1
        else:
            self._reset()
            self._draw_actions()

        self._update()
        self._draw_splits()

    def tick(self, ticks):
        self._update()

    def save(self):
        """Keep the count and the splits for when the app is opened again."""
        return (self._timer.save(), self._splits, self._nsplits)

    def restore(self, saved):
        (timer, self._splits, self._nsplits) = saved
        self._timer.restore(timer)

    def _reset(self):
        self._timer.reset()
        self._splits = []
        self._nsplits = 0

    def _draw_splits(self):
        draw = wasp.watch.drawable
        draw.rounded_rect(cards.MARGIN, _SPLITS_Y, cards.SPAN, _ROW_H,
                          cards.COLOR)
        splits = self._splits
        if 0 == len(splits):
            return

        draw.set_font(fonts.sans18)
        draw.set_color(wasp.system.theme('mid'), cards.COLOR)
        y = _SPLITS_Y + (_ROW_H - _SPLITS * _SPLIT_PITCH) // 2 + 1

        n = self._nsplits
        for i, s in enumerate(splits):
            centisecs = s
            secs = centisecs // 100
            centisecs %= 100
            minutes = secs // 60
            secs %= 60

            t = '# {}   {:02}:{:02}.{:02}'.format(n, minutes, secs, centisecs)
            n -= 1

            draw.string(t, cards.MARGIN + 12, y + (i*_SPLIT_PITCH),
                        cards.SPAN - 24)

    def _draw_actions(self):
        """Draw the split or clear card and the start or stop card."""
        draw = wasp.watch.drawable
        bright = wasp.system.theme('bright')
        for x in _ACTION_X:
            draw.rounded_rect(x, _ACTION_Y, _ACTION_W, _ROW_H, cards.COLOR)
        draw.set_color(bright, cards.COLOR)
        draw.set_font(fonts.sans24)
        started = self._timer.started
        draw.string('Split' if started else 'Clear', _ACTION_X[0],
                    _ACTION_Y + (_ROW_H - 24) // 2, width=_ACTION_W)

        x = _ACTION_X[1] + _ACTION_W // 2
        y = _ACTION_Y + _ROW_H // 2
        if started:
            # A pause symbol: two bars.
            draw.fill(bright, x - 12, y - 15, 9, 30)
            draw.fill(bright, x + 3, y - 15, 9, 30)
        else:
            for i in range(0, 18):
                draw.fill(bright, x - 8 + i, y - 18 + i, 1, 36 - 2*i)

    def _draw(self):
        """Draw the display from scratch."""
        draw = wasp.watch.drawable
        draw.fill(0)

        draw.rounded_rect(cards.MARGIN, _TIME_Y, cards.SPAN, _ROW_H,
                          cards.COLOR)
        self._timer.draw()
        self._draw_splits()
        self._draw_actions()

    def _update(self):
        self._timer.update()
