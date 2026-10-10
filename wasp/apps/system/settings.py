# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020-21 Daniel Thompson

"""Settings application
~~~~~~~~~~~~~~~~~~~~~~~

Allows a very small set of user preferences (including the date and
time) to be set on the device itself.

Each setting has a page of its own; swipe up and down to move between them.
A setting with a few values shows them all as cards, with the chosen one
filled in the accent colour. Each wake gesture has a card of its own,
filled while it is switched on. The time and date are set with a column of
cards per field, and the step goal is stepped up and down.

.. figure:: res/screenshots/SettingsApp.png
    :width: 179

.. note::

    The settings tool is not expected to comprehensively present every
    user configurable preference. Some are better presented via a
    companion app and some particular exotic ones are perhaps best
    managed with a user-provided ``main.py``.
"""


import wasp
import cards
import fonts
import icons

from widgets.page import clip, clear_around, draw_indicator, scroll_in

_MARGIN = cards.MARGIN
_WIDTH = cards.SPAN

# Four rows: the setting's name on the first, its controls on the others.
_ROW_H = cards.size(4)
_ROW_TOPS = cards.edges((_ROW_H,) * 4)
_PITCH = _ROW_TOPS[1] - _ROW_TOPS[0]
# The three rows under the name, taken together.
_BODY_Y = _ROW_TOPS[1]
_BODY_H = _ROW_TOPS[3] + _ROW_H - _BODY_Y

# Choices sit one to a row, or two to a row when there are more than three.
_HALF = cards.size(2)
_HALVES = cards.edges((_HALF, _HALF))
_THIRD = cards.size(3)
_THIRDS = cards.edges((_THIRD,) * 3)

# The step goal: a tall card showing the goal over a minus and a plus card.
_VALUE_H = _ROW_TOPS[2] + _ROW_H - _BODY_Y

# Where text sits within a row.
_TEXT_Y = (_ROW_H - 24) // 2

_SETTINGS = ('Brightness', 'Notification Level', 'Screen Timeout', 'Wake',
             'Time', 'Time Format', 'Date', 'Units', 'Step Goal')
# The wake gestures, each switched on and off by its own card.
_WAKES = ('Raise to wake', 'Tap to wake')
_LEVELS = ('Low', 'Mid', 'High')
_NOTIFY_LEVELS = ('Silent', 'Mid', 'High')
_UNITS = ('Metric', 'Imperial')
_FORMATS = ('12 hour', '24 hour')
# A band covering the whole screen, for drawing outside a slide.
_WHOLE = (0, 240, 0)

class SettingsApp():
    """Settings application."""
    NAME = 'Settings'
    ICON = icons.settings

    def __init__(self):
        self._HH = wasp.widgets.Spinner(_HALVES[0], _BODY_Y, 0, 23, 2,
                                        w=_HALF, h=_BODY_H)
        self._MM = wasp.widgets.Spinner(_HALVES[1], _BODY_Y, 0, 59, 2,
                                        w=_HALF, h=_BODY_H)
        self._dd = wasp.widgets.Spinner(_THIRDS[0], _BODY_Y, 1, 31, 1,
                                        w=_THIRD, h=_BODY_H)
        self._mm = wasp.widgets.Spinner(_THIRDS[1], _BODY_Y, 1, 12, 1,
                                        w=_THIRD, h=_BODY_H)
        self._yy = wasp.widgets.Spinner(_THIRDS[2], _BODY_Y, 20, 60, 2,
                                        w=_THIRD, h=_BODY_H)
        self._settings = _SETTINGS
        self._sett_index = 0
        self._current_setting = self._settings[0]

    def foreground(self):
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH)
        wasp.system.request_event(wasp.EventMask.SWIPE_UPDOWN)

    def _choices(self):
        """The values the current setting offers, or None if it has none."""
        s = self._current_setting
        if s == 'Brightness':
            return _LEVELS
        if s == 'Notification Level':
            return _NOTIFY_LEVELS
        if s == 'Screen Timeout':
            return ['{} s'.format(t) for t in wasp.BLANK_AFTER]
        if s == 'Time Format':
            return _FORMATS
        if s == 'Units':
            return _UNITS
        return None

    def _chosen(self):
        """Index of the value the current setting has now."""
        s = self._current_setting
        if s == 'Brightness':
            return wasp.system.brightness - 1
        if s == 'Notification Level':
            return wasp.system.notify_level - 1
        if s == 'Screen Timeout':
            choices = wasp.BLANK_AFTER
            current = wasp.system.blank_after
            return choices.index(current) if current in choices else -1
        if s == 'Time Format':
            return 1 if wasp.system.clock_24h else 0
        return _UNITS.index(wasp.system.units)

    def _choose(self, i):
        """Give the current setting the value at index i."""
        s = self._current_setting
        if s == 'Brightness':
            wasp.system.brightness = i + 1
        elif s == 'Notification Level':
            wasp.system.notify_level = i + 1
        elif s == 'Screen Timeout':
            wasp.system.blank_after = wasp.BLANK_AFTER[i]
        elif s == 'Time Format':
            wasp.system.clock_24h = i == 1
        else:
            wasp.system.units = _UNITS[i]

    def _cell(self, i, count):
        """Position and size of the card for choice i of count."""
        if count <= 3:
            return (_MARGIN, _ROW_TOPS[1 + i], _WIDTH)
        return (_HALVES[i % 2], _ROW_TOPS[1 + i // 2], _HALF)

    def touch(self, event):
        x = event[1]
        y = event[2]
        s = self._current_setting
        choices = self._choices()
        if choices:
            count = len(choices)
            for i in range(count):
                (cx, cy, w) = self._cell(i, count)
                if cx <= x < cx + w and cy <= y < cy + _ROW_H:
                    if i != self._chosen():
                        self._choose(i)
                        self._draw_choices()
                    return
        elif s == 'Wake':
            for i in range(len(_WAKES)):
                if _ROW_TOPS[1 + i] <= y < _ROW_TOPS[1 + i] + _ROW_H:
                    if i == 0:
                        wasp.system.wake_on_raise = not wasp.system.wake_on_raise
                    else:
                        wasp.system.wake_on_tap = not wasp.system.wake_on_tap
                    self._draw_wakes()
        elif s == 'Step Goal':
            if y >= _ROW_TOPS[3]:
                goals = wasp.STEP_GOALS
                current = wasp.system.step_goal
                index = goals.index(current) if current in goals else 0
                index += 1 if x >= _HALVES[1] else -1
                wasp.system.step_goal = goals[index % len(goals)]
                self._draw_goal()
        elif s == 'Time':
            if self._HH.touch(event) or self._MM.touch(event):
                now = list(wasp.watch.rtc.get_localtime())
                now[3] = self._HH.value
                now[4] = self._MM.value
                wasp.watch.rtc.set_localtime(now)
        elif s == 'Date':
            if self._yy.touch(event) or self._mm.touch(event) \
                    or self._dd.touch(event):
                now = list(wasp.watch.rtc.get_localtime())
                now[0] = self._yy.value + 2000
                now[1] = self._mm.value
                now[2] = self._dd.value
                wasp.watch.rtc.set_localtime(now)

    def swipe(self, event):
        """Slide in the next setting, or the one before."""
        if event[0] == wasp.EventType.UP:
            self._sett_index += 1
        elif event[0] == wasp.EventType.DOWN:
            self._sett_index -= 1
        else:
            return
        self._enter()
        scroll_in(self.draw_rows, up=event[0] == wasp.EventType.UP)

    def _enter(self):
        """Make the setting at the current index the one shown."""
        s = self._settings[self._sett_index % len(self._settings)]
        self._current_setting = s
        if s == 'Time':
            now = wasp.watch.rtc.get_localtime()
            self._HH.value = now[3]
            self._MM.value = now[4]
        elif s == 'Date':
            now = wasp.watch.rtc.get_localtime()
            self._yy.value = now[0] - 2000
            self._mm.value = now[1]
            self._dd.value = now[2]

    def _label(self, text, x, y, w, color=None, band=_WHOLE):
        """Draw the part of a card holding one line of text inside a band.

        :param band: First page row, row count and screen offset of the band
        """
        (top, height, sy) = band
        (first, rows) = clip(top, height, y, _ROW_H)
        if not rows:
            return
        draw = wasp.watch.drawable
        if color is None:
            color = cards.COLOR
        draw.rounded_rect(x, sy + y, w, _ROW_H, color, first=first, rows=rows)
        (first, rows) = clip(top, height, y + _TEXT_Y,
                             draw.bounding_box(text)[1])
        if rows:
            draw.string(text, x, sy + y + _TEXT_Y, width=w,
                        first=first, rows=rows)

    def _blank(self, x, y, w, band):
        """Clear a row's worth of a cell that holds no card."""
        (top, height, sy) = band
        (first, rows) = clip(top, height, y, _ROW_H)
        if rows:
            wasp.watch.drawable.fill(0, x, sy + y + first, w, rows)

    def _draw(self):
        """Redraw the display from scratch."""
        display = wasp.watch.display
        display.mute(True)
        # A page that slid in left the display scrolled, so put it back first.
        display.scroll(0)
        self._enter()
        self.draw_rows(0, 0, 240)
        display.mute(False)

    def draw_rows(self, top, y, height):
        """Draw the page rows from top to top+height at screen row y."""
        draw = wasp.watch.drawable
        s = self._current_setting
        band = (top, height, y - top)
        choices = self._choices()

        # Blank the gaps around the narrowest columns the page uses; a wider
        # card drawn afterwards covers the gaps it spans.
        if s == 'Date':
            (lefts, width) = (_THIRDS, _THIRD)
        elif s in ('Time', 'Step Goal') or (choices and len(choices) > 3):
            (lefts, width) = (_HALVES, _HALF)
        else:
            (lefts, width) = ((_MARGIN,), _WIDTH)
        clear_around(y, height, top, _ROW_TOPS, _ROW_H, lefts, width)

        draw.set_font(fonts.sans24)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        if s == 'Time':
            self._label('Hour', _HALVES[0], _ROW_TOPS[0], _HALF, band=band)
            self._label('Minute', _HALVES[1], _ROW_TOPS[0], _HALF, band=band)
            self._HH.draw(*band)
            self._MM.draw(*band)
        elif s == 'Date':
            for (i, name) in enumerate(('Day', 'Month', 'Year')):
                self._label(name, _THIRDS[i], _ROW_TOPS[0], _THIRD, band=band)
            self._dd.draw(*band)
            self._mm.draw(*band)
            self._yy.draw(*band)
        else:
            self._label(s, _MARGIN, _ROW_TOPS[0], _WIDTH, band=band)
            if s == 'Step Goal':
                draw.set_font(fonts.sans28)
                self._label('-', _HALVES[0], _ROW_TOPS[3], _HALF, band=band)
                self._label('+', _HALVES[1], _ROW_TOPS[3], _HALF, band=band)
                self._draw_goal(band)
            elif s == 'Wake':
                self._draw_wakes(band)
                self._blank(_MARGIN, _ROW_TOPS[3], _WIDTH, band)
            else:
                self._draw_choices(band)
        draw_indicator(self._sett_index % len(self._settings),
                       len(self._settings), top, y, height)

    def _draw_choices(self, band=_WHOLE):
        """Draw a card per value, filling the chosen one with the accent."""
        draw = wasp.watch.drawable
        choices = self._choices()
        chosen = self._chosen()
        count = len(choices)
        draw.set_font(fonts.sans24)
        for (i, text) in enumerate(choices):
            (x, y, w) = self._cell(i, count)
            if i == chosen:
                color = wasp.system.theme('ui')
                draw.set_color(wasp.system.theme('bright'), color)
            else:
                color = cards.COLOR
                draw.set_color(wasp.system.theme('mid'), color)
            self._label(text, x, y, w, color, band)

        # Cells past the last value hold no card.
        cells = 3 if count <= 3 else 6
        for i in range(count, cells):
            (x, y, w) = self._cell(i, count)
            self._blank(x, y, w, band)

    def _draw_wakes(self, band=_WHOLE):
        """Draw a card per wake gesture, filled with the accent while it is on."""
        draw = wasp.watch.drawable
        draw.set_font(fonts.sans24)
        states = (wasp.system.wake_on_raise, wasp.system.wake_on_tap)
        for (i, text) in enumerate(_WAKES):
            if states[i]:
                color = wasp.system.theme('ui')
                draw.set_color(wasp.system.theme('bright'), color)
            else:
                color = cards.COLOR
                draw.set_color(wasp.system.theme('mid'), color)
            self._label(text, _MARGIN, _ROW_TOPS[1 + i], _WIDTH, color, band)

    def _draw_goal(self, band=_WHOLE):
        """Draw the card showing the step goal."""
        (top, height, sy) = band
        (first, rows) = clip(top, height, _BODY_Y, _VALUE_H)
        if not rows:
            return
        draw = wasp.watch.drawable
        draw.rounded_rect(_MARGIN, sy + _BODY_Y, _WIDTH, _VALUE_H, cards.COLOR,
                          first=first, rows=rows)
        for (text, font, ty, fg) in (
                ('{}'.format(wasp.system.step_goal), fonts.sans28,
                 _BODY_Y + _VALUE_H // 2 - 32, 'bright'),
                ('steps a day', fonts.sans18,
                 _BODY_Y + _VALUE_H // 2 + 10, 'mid')):
            (first, rows) = clip(top, height, ty, font.height())
            if rows:
                draw.set_color(wasp.system.theme(fg), cards.COLOR)
                draw.set_font(font)
                draw.string(text, _MARGIN, sy + ty, width=_WIDTH,
                            first=first, rows=rows)
