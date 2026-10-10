# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020-21 Daniel Thompson

"""Settings application
~~~~~~~~~~~~~~~~~~~~~~~

Allows a very small set of user preferences (including the date and
time) to be set on the device itself.

Each setting has a page of its own; swipe up and down to move between them.
A setting with a few values shows them all as cards, with the chosen one
filled in the accent colour. The time and date are set with a column of
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

from widgets.page import draw_indicator

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

_SETTINGS = ('Brightness', 'Notification Level', 'Screen Timeout', 'Time',
             'Time Format', 'Date', 'Units', 'Step Goal')
_LEVELS = ('Low', 'Mid', 'High')
_NOTIFY_LEVELS = ('Silent', 'Mid', 'High')
_UNITS = ('Metric', 'Imperial')
_FORMATS = ('12 hour', '24 hour')

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
        """Move to the next setting, or back to the one before."""
        if event[0] == wasp.EventType.UP:
            self._sett_index += 1
            self._draw()
        elif event[0] == wasp.EventType.DOWN:
            self._sett_index -= 1
            self._draw()

    def _label(self, text, x, y, w, color=None):
        """Draw a card holding one line of text."""
        draw = wasp.watch.drawable
        if color is None:
            color = cards.COLOR
        draw.rounded_rect(x, y, w, _ROW_H, color)
        draw.string(text, x, y + _TEXT_Y, width=w)

    def _draw(self):
        """Redraw the display from scratch."""
        draw = wasp.watch.drawable
        mute = wasp.watch.display.mute
        index = self._sett_index % len(self._settings)
        s = self._settings[index]
        self._current_setting = s
        mute(True)
        draw.fill(0)
        draw.set_font(fonts.sans24)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        if s == 'Time':
            now = wasp.watch.rtc.get_localtime()
            self._HH.value = now[3]
            self._MM.value = now[4]
            self._label('Hour', _HALVES[0], _ROW_TOPS[0], _HALF)
            self._label('Minute', _HALVES[1], _ROW_TOPS[0], _HALF)
            self._HH.draw()
            self._MM.draw()
        elif s == 'Date':
            now = wasp.watch.rtc.get_localtime()
            self._yy.value = now[0] - 2000
            self._mm.value = now[1]
            self._dd.value = now[2]
            for (i, name) in enumerate(('Day', 'Month', 'Year')):
                self._label(name, _THIRDS[i], _ROW_TOPS[0], _THIRD)
            self._dd.draw()
            self._mm.draw()
            self._yy.draw()
        else:
            self._label(s, _MARGIN, _ROW_TOPS[0], _WIDTH)
            if s == 'Step Goal':
                draw.set_font(fonts.sans28)
                self._label('-', _HALVES[0], _ROW_TOPS[3], _HALF)
                self._label('+', _HALVES[1], _ROW_TOPS[3], _HALF)
                self._draw_goal()
            else:
                self._draw_choices()
        draw_indicator(index, len(self._settings))
        mute(False)

    def _draw_choices(self):
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
            self._label(text, x, y, w, color)

    def _draw_goal(self):
        """Draw the card showing the step goal."""
        draw = wasp.watch.drawable
        draw.rounded_rect(_MARGIN, _BODY_Y, _WIDTH, _VALUE_H, cards.COLOR)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans28)
        draw.string('{}'.format(wasp.system.step_goal), _MARGIN,
                    _BODY_Y + _VALUE_H // 2 - 32, width=_WIDTH)
        draw.set_color(wasp.system.theme('mid'), cards.COLOR)
        draw.set_font(fonts.sans18)
        draw.string('steps a day', _MARGIN, _BODY_Y + _VALUE_H // 2 + 10,
                    width=_WIDTH)
