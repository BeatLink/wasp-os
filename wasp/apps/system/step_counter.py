# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Step counter
~~~~~~~~~~~~~~~

Provide a daily step count.

The first page shows today's count on a card with a bar filling towards the
daily goal. Swipe up for a graph of each earlier day. Pages slide in with
the panel's hardware scrolling; a graph's bars are drawn once it has arrived.

    .. figure:: res/screenshots/StepCounterApp.png
        :width: 179

The step counts automatically reset at midnight.
"""

import wasp

import array
import cards
import fonts
import icons
import time
import watch

from micropython import const
from widgets.page import clip, clear_around, draw_indicator, scroll_in

# The today page: a tall card with the count over a card with the goal.
_ROW_H = cards.size(4)
_ROW_TOPS = cards.edges((_ROW_H,) * 4)
_COUNT_H = _ROW_TOPS[2] + _ROW_H - cards.MARGIN
_GOAL_Y = _ROW_TOPS[3]
# The progress bar, kept inside the straight part of the count card.
_BAR_X = const(20)
_BAR_W = const(200)
_BAR_Y = _ROW_TOPS[2] + 20
# The history pages: a card with the date and total over the graph.
_GRAPH_TOP = _ROW_TOPS[1]
_GRAPH_H = 240 - _GRAPH_TOP - 1
_GRAPH_BOTTOM = _GRAPH_TOP + _GRAPH_H
_GRAPH_LINES = (0, 60, 90, 120, 150, 180, 239)
_TEXT_Y = cards.MARGIN + (_ROW_H - 24) // 2

class StepCounterApp():
    """Step counter application."""
    NAME = 'Steps'
    ICON = icons.steps

    def foreground(self):
        """Draw the application.

        The count is reset at midnight by the step logger, which runs
        whether or not this app has been opened.
        """
        self._page = -1
        self._draw()
        wasp.system.request_event(wasp.EventMask.SWIPE_UPDOWN)
        wasp.system.request_tick(1000)

    def background(self):
        """Let go of the counts a history page holds."""
        self._data = None

    def swipe(self, event):
        up =event[0] != wasp.EventType.DOWN
        if not up:
            if self._page == -1:
                return
            self._page -= 1
        else:
            self._page += 1

        self._load()
        scroll_in(self.draw_rows, up=up)
        self._draw_bars()

    def tick(self, ticks):
        if self._page == -1:
            self._update()

    def _load(self):
        """Read the step counts of the day a history page shows."""
        self._data = None
        self._total = 0
        # Read once, so every band of a sliding page shows the same count.
        self._count = watch.accel.steps
        if self._page < 0:
            return
        then = int(watch.rtc.time()) - ((24*60*60) * self._page)
        walltime = time.localtime(then)
        self._date = '{:02d}-{:02d}'.format(walltime[2], walltime[1])

        # A watch whose step counter did not start has no logger at all.
        logger = getattr(wasp.system, 'steps', None)
        data = logger.data(then) if logger else None
        if data:
            self._data = array.array('H', data)
            self._total = sum(self._data)

    def _draw(self):
        """Draw the display from scratch."""
        display = wasp.watch.display
        display.mute(True)
        # A page that slid in left the display scrolled, so put it back first.
        display.scroll(0)
        self._load()
        self.draw_rows(0, 0, 240)
        self._draw_bars()
        display.mute(False)

    def draw_rows(self, top, y, height):
        """Draw the page rows from top to top+height at screen row y."""
        if self._page == -1:
            self._today_rows(top, y, height)
        else:
            self._graph_rows(top, y, height)

    def _today_rows(self, top, y, height):
        """Draw rows of today's page: the count card over the goal card."""
        draw = wasp.watch.drawable
        clear_around(y, height, top, _ROW_TOPS, _ROW_H, (cards.MARGIN,),
                     cards.SPAN)
        sy = y - top

        (first, rows) = clip(top, height, cards.MARGIN, _COUNT_H)
        if rows:
            draw.rounded_rect(cards.MARGIN, sy + cards.MARGIN, cards.SPAN,
                              _COUNT_H, cards.COLOR, first=first, rows=rows)
            (ifirst, irows) = clip(top, height, 20, icons.steps[1])
            if irows:
                draw.rleblit(icons.steps, (104, sy + 20 + ifirst),
                             wasp.system.theme('bright'), cards.COLOR,
                             ifirst, irows)
            self._update(top, height, sy, self._count)

        (first, rows) = clip(top, height, _GOAL_Y, _ROW_H)
        if rows:
            draw.rounded_rect(cards.MARGIN, sy + _GOAL_Y, cards.SPAN, _ROW_H,
                              cards.COLOR, first=first, rows=rows)
            (tfirst, trows) = clip(top, height, _GOAL_Y + (_ROW_H - 24) // 2,
                                   fonts.sans24.height())
            if trows:
                draw.set_color(wasp.system.theme('mid'), cards.COLOR)
                draw.set_font(fonts.sans24)
                draw.string('Goal {}'.format(wasp.system.step_goal),
                            cards.MARGIN, sy + _GOAL_Y + (_ROW_H - 24) // 2,
                            width=cards.SPAN, first=tfirst, rows=trows)

        draw_indicator(0, 2, top, y, height)

    def _update(self, top=0, height=240, sy=0, count=None):
        """Draw the step count and the bar towards the goal.

        Called with no band it draws them where they sit, as the tick does.
        """
        draw = wasp.watch.drawable

        # Update the step count
        if count is None:
            count = watch.accel.steps
        (first, rows) = clip(top, height, 72, fonts.sans36.height())
        if rows:
            draw.set_font(fonts.sans36)
            draw.set_color(draw.lighten(wasp.system.theme('spot1'),
                                        wasp.system.theme('contrast')),
                           cards.COLOR)
            draw.string(str(count), _BAR_X, sy + 72, width=_BAR_W,
                        first=first, rows=rows)

        # A bar that fills towards the goal, in the accent once it is met.
        (first, rows) = clip(top, height, _BAR_Y, 8)
        if rows:
            goal = wasp.system.step_goal
            done = min(count, goal) * _BAR_W // goal
            y = sy + _BAR_Y + first
            if done:
                colour = wasp.system.theme('ui') if count >= goal else wasp.system.theme('spot1')
                draw.fill(colour, _BAR_X, y, done, rows)
            if done < _BAR_W:
                draw.fill(0, _BAR_X + done, y, _BAR_W - done, rows)

    def _graph_rows(self, top, y, height):
        """Draw rows of a history page: the date card and the graph's frame."""
        draw = wasp.watch.drawable
        clear_around(y, height, top, (cards.MARGIN,), _ROW_H, (cards.MARGIN,),
                     cards.SPAN)
        sy = y - top

        (first, rows) = clip(top, height, cards.MARGIN, _ROW_H)
        if rows:
            draw.rounded_rect(cards.MARGIN, sy + cards.MARGIN, cards.SPAN,
                              _ROW_H, cards.COLOR, first=first, rows=rows)
            (tfirst, trows) = clip(top, height, _TEXT_Y, fonts.sans24.height())
            if trows:
                draw.set_font(fonts.sans24)
                draw.set_color(wasp.system.theme('bright'), cards.COLOR)
                ty = sy + _TEXT_Y
                draw.string(self._date, 16, ty, first=tfirst, rows=trows)
                total = str(self._total) if self._data else 'No data'
                draw.string(total, 100, ty, 124, right=True,
                            first=tfirst, rows=trows)

        draw_indicator(1, 2, top, y, height)
        if not self._data:
            return

        # The frame: a line along the top and the bottom, and a few hours.
        for row in (_GRAPH_TOP, _GRAPH_BOTTOM):
            if top <= row < top + height:
                draw.fill(cards.COLOR, 0, sy + row, 240, 1)
        (first, rows) = clip(top, height, _GRAPH_TOP, _GRAPH_H)
        if rows:
            for x in _GRAPH_LINES:
                draw.fill(cards.COLOR, x, sy + _GRAPH_TOP + first, 1, rows)

    def _draw_bars(self):
        """Draw a graph's bars, one per period, once its page is in place."""
        data = self._data
        if self._page < 0 or not data:
            return
        draw = wasp.watch.drawable
        color = wasp.system.theme('spot2')
        for x, d in enumerate(data):
            if d == 0:
                continue
            d = d // 4
            if d >= _GRAPH_H:
                draw.fill(0xffff, x, _GRAPH_BOTTOM - _GRAPH_H + 1, 1, _GRAPH_H - 1)
            else:
                draw.fill(color, x, _GRAPH_BOTTOM - d, 1, d)
