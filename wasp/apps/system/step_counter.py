# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Step counter
~~~~~~~~~~~~~~~

Provide a daily step count.

The first page shows today's count on a card with a bar filling towards the
daily goal. Swipe up for a graph of each earlier day.

    .. figure:: res/screenshots/StepCounterApp.png
        :width: 179

The step counts automatically reset at midnight.
"""

import wasp

import cards
import fonts
import icons
import time
import watch

from micropython import const
from widgets.page import draw_indicator

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

class StepCounterApp():
    """Step counter application."""
    NAME = 'Steps'
    ICON = icons.steps

    def __init__(self):
        # The sensor is started when the app is registered, not here: a
        # reset zeroes the step count, and this runs every time the app is
        # opened.
        self._wake = 0

    def foreground(self):
        """Cancel the alarm and draw the application.

        Cancelling the alarm has two effects. Firstly it ensures the
        step count won't change whilst we are watching it and, secondly
        it ensures that if the time of day has been set to a value in
        the past that we reconfigure the alarm.

        This does in the side effect that if the application of open at
        midnight then the reset doesn't happen for that day.
        """
        wasp.system.cancel_alarm(self._wake, self._reset)
        self._page = -1
        self._draw()
        wasp.system.request_event(wasp.EventMask.SWIPE_UPDOWN)
        wasp.system.request_tick(1000)

    def background(self):
        """Set an alarm to trigger at midnight and reset the counter."""
        now = watch.rtc.get_localtime()
        yyyy = now[0]
        mm = now[1]
        dd = now[2]
        then = (yyyy, mm, dd+1, 0, 0, 0, 0, 0, 0)

        self._wake = time.mktime(then)
        wasp.system.set_alarm(self._wake, self._reset)

    def _reset(self):
        """"Reset the step counter and re-arm the alarm."""
        watch.accel.steps = 0
        self._wake += 24 * 60 * 60
        wasp.system.set_alarm(self._wake, self._reset)

    def swipe(self, event):
        if event[0] == wasp.EventType.DOWN:
            if self._page == -1:
                return
            self._page -= 1
        else:
            self._page += 1

        mute = wasp.watch.display.mute
        mute(True)
        self._draw()
        mute(False)

    def tick(self, ticks):
        if self._page == -1:
            self._update()

    def _draw(self):
        """Draw the display from scratch."""
        draw = wasp.watch.drawable
        draw.fill(0)

        if self._page == -1:
            draw.rounded_rect(cards.MARGIN, cards.MARGIN, cards.SPAN,
                              _COUNT_H, cards.COLOR)
            draw.rleblit(icons.steps, (104, 20), wasp.system.theme('bright'),
                         cards.COLOR)
            draw.rounded_rect(cards.MARGIN, _GOAL_Y, cards.SPAN, _ROW_H,
                              cards.COLOR)
            draw.set_color(wasp.system.theme('mid'), cards.COLOR)
            draw.set_font(fonts.sans24)
            draw.string('Goal {}'.format(wasp.system.step_goal),
                        cards.MARGIN, _GOAL_Y + (_ROW_H - 24) // 2,
                        width=cards.SPAN)
            self._update()
        else:
            self._update_graph()

    def _update(self):
        draw = wasp.watch.drawable

        # Update the step count
        count = watch.accel.steps
        draw.set_font(fonts.sans36)
        draw.set_color(draw.lighten(wasp.system.theme('spot1'),
                                    wasp.system.theme('contrast')),
                       cards.COLOR)
        draw.string(str(count), _BAR_X, 72, width=_BAR_W)

        # A bar that fills towards the goal, in the accent once it is met.
        goal = wasp.system.step_goal
        done = min(count, goal) * _BAR_W // goal
        if done:
            colour = wasp.system.theme('ui') if count >= goal else wasp.system.theme('spot1')
            draw.fill(colour, _BAR_X, _BAR_Y, done, 8)
        if done < _BAR_W:
            draw.fill(0, _BAR_X + done, _BAR_Y, _BAR_W - done, 8)

        draw_indicator(0, 2)

    def _update_graph(self):
        draw = watch.drawable
        draw.rounded_rect(cards.MARGIN, cards.MARGIN, cards.SPAN, _ROW_H,
                          cards.COLOR)
        draw.set_font(fonts.sans24)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        text_y = cards.MARGIN + (_ROW_H - 24) // 2

        # Draw the date
        now = int(watch.rtc.time())
        then = now - ((24*60*60) * self._page)
        walltime = time.localtime(then)
        draw.string('{:02d}-{:02d}'.format(walltime[2], walltime[1]),
                    16, text_y)
        draw_indicator(1, 2)

        # Get the iterable step data for the currently selected date. A
        # watch whose step counter did not start has no logger at all.
        logger = getattr(wasp.system, 'steps', None)
        data = logger.data(then) if logger else None

        # Bail if there is no data
        if not data:
            draw.string('No data', 100, text_y, 124, right=True)
            return

        color = wasp.system.theme('spot2')

        # Draw the frame
        bottom = _GRAPH_TOP + _GRAPH_H
        draw.fill(cards.COLOR, 0, _GRAPH_TOP, 240, 1)
        draw.fill(cards.COLOR, 0, bottom, 240, 1)
        for i in (0, 60, 90, 120, 150, 180, 239):
            draw.fill(cards.COLOR, i, _GRAPH_TOP, 1, _GRAPH_H)

        total = 0
        for x, d in enumerate(data):
            if d == 0 or x < 2:
                # TODO: the x < 2 conceals BUGZ
                continue
            total += d
            d = d // 4
            if d >= _GRAPH_H:
                draw.fill(0xffff, x, bottom - _GRAPH_H + 1, 1, _GRAPH_H - 1)
            else:
                draw.fill(color, x, bottom - d, 1, d)

        draw.string(str(total), 100, text_y, 124, right=True)
