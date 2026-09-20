# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson
# Copyright (C) 2020 Joris Warmbier
# Copyright (C) 2021 Adam Blair
"""Alarm Application
~~~~~~~~~~~~~~~~~~~~

An application to set a vibration alarm. All settings can be accessed from the
Watch UI. Press the button to turn off ringing alarms.

The alarm list shows four tiles per page, one per alarm, with an add tile after
the last one. Swipe up and down to reach the other pages. Tapping an alarm opens
a three page editor: the time, then the days it repeats on, then a summary with
a delete and a save button.

    .. figure:: apps/alarm/screenshot.png
        :width: 179

        Screenshot of the Alarm Application

"""
import wasp
import cards
import fonts
import time
import widgets
import array
from micropython import const

# 1-bit RLE, 32x32, generated from apps/alarm/icon.png, 61 bytes
icon = (
    32, 32,
    b'\x0f\x02\x1d\x04\x1c\x04\x1b\x06\x18\n\x14\x0e\x11\x10\x10\x10'
    b'\x0f\x12\x0e\x12\r\x14\x0c\x14\x0c\x14\x0c\x14\x0c\x14\x0c\x14'
    b'\x0c\x14\x0c\x14\x0b\x16\n\x16\t\x18\x07\x1a\x06\x1a\x05\x1c'
    b'\x04\x1c\x05\x1aO\x08\x18\x08\x19\x06\x1b\x04\x0e'
)

# 1-bit RLE, 32x32, generated from apps/alarm/plus.png, 59 bytes
plus_icon = (
    32, 32,
    b'\x0f\x03\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1c\x04'
    b'\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1b\x06\r\x80\r\x06'
    b'\x1b\x04\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1c\x04'
    b'\x1c\x04\x1c\x04\x1c\x04\x1c\x04\x1d\x03\x0e'
)

# 1-bit RLE, 32x32, generated from apps/alarm/trash.png, 157 bytes
trash_icon = (
    32, 32,
    b'\x0b\n\x15\x0c\r\x1a\x05\x1c\x04\x1c\x05\x1aG\x18\x08\x18'
    b'\x08\x18\x08\x18\x08\x05\x02\x04\x02\x04\x02\x05\x08\x05\x02\x04'
    b'\x02\x04\x02\x05\x08\x05\x02\x04\x02\x04\x02\x05\x08\x05\x02\x04'
    b'\x02\x04\x02\x05\x08\x05\x02\x04\x02\x04\x02\x05\x08\x05\x02\x04'
    b'\x02\x04\x02\x05\x08\x05\x02\x04\x02\x04\x02\x05\x08\x05\x02\x04'
    b'\x02\x04\x02\x05\x08\x05\x02\x04\x02\x04\x02\x05\x08\x05\x02\x04'
    b'\x02\x04\x02\x05\x08\x05\x02\x04\x02\x04\x02\x05\x08\x05\x02\x04'
    b'\x02\x04\x02\x05\x08\x05\x02\x04\x02\x04\x02\x05\x08\x05\x02\x04'
    b'\x02\x04\x02\x05\x08\x05\x02\x04\x02\x04\x02\x05\x08\x05\x02\x04'
    b'\x02\x04\x02\x05\x08\x18\x08\x18\t\x16\x0b\x14\x06'
)

# 1-bit RLE, 32x32, generated from apps/alarm/save.png, 63 bytes
save_icon = (
    32, 32,
    b'\x9c\x03\x1c\x05\x1a\x06\x19\x07\x18\x07\x18\x07\x18\x07\x18\x07'
    b'\x18\x07\x06\x02\x10\x07\x06\x05\r\x07\x07\x06\x0b\x07\x08\x07'
    b'\t\x07\n\x07\x07\x07\x0c\x07\x05\x07\x0e\x06\x04\x07\x10\x06'
    b'\x02\x07\x12\r\x14\x0b\x16\t\x18\x07\x1a\x05\x1c\x03\xb3'
)





# Enabled masks
_MONDAY = const(0x01)
_TUESDAY = const(0x02)
_WEDNESDAY = const(0x04)
_THURSDAY = const(0x08)
_FRIDAY = const(0x10)
_SATURDAY = const(0x20)
_SUNDAY = const(0x40)
_WEEKDAYS = const(0x1F)
_WEEKENDS = const(0x60)
_EVERY_DAY = const(0x7F)
_IS_ACTIVE = const(0x80)

# Alarm data indices
_HOUR_IDX = const(0)
_MIN_IDX = const(1)
_ENABLED_IDX = const(2)

# Pages
_HOME_PAGE = const(-1)
_RINGING_PAGE = const(-2)

# Steps within the editor
_TIME_STEP = const(0)
_DAYS_STEP = const(1)
_SAVE_STEP = const(2)

# How many alarms are held, and how many tiles a list page shows.
_MAX_ALARMS = const(12)
_ROWS = const(4)

# Colour of a tile, matching the launcher. The accent marks a selected day.
_TILE_COLOR = cards.COLOR
_MARGIN = cards.MARGIN

# The list page: four rows across the full width.
_ROW_W = cards.SPAN
_ROW_H = cards.size(_ROWS)
_ROW_TOPS = cards.edges((_ROW_H,) * _ROWS)
_ROW_PITCH = _ROW_TOPS[1] - _ROW_TOPS[0]

# The time page: two columns of four. The day page: four columns of two,
# each tile as tall as two of the time page's rows.
_CELL_W = cards.size(2)
_CELL_LEFTS = cards.edges((_CELL_W,) * 2)
_CELL_PITCH = _CELL_LEFTS[1] - _CELL_LEFTS[0]
_DAY_W = cards.size(4)
_DAY_LEFTS = cards.edges((_DAY_W,) * 4)
_DAY_PITCH = _DAY_LEFTS[1] - _DAY_LEFTS[0]
_DAY_H = _CELL_W

# The summary page: one tall tile over a delete and a save tile.
_ACTION_H = cards.size(3)
_SUMMARY_H = cards.SPAN - _ACTION_H - cards.MARGIN
_SUMMARY_Y, _ACTION_Y = cards.edges((_SUMMARY_H, _ACTION_H))

# Days as they are laid out on the picker, Sunday first, with the bit each one
# sets. The bits run Monday to Sunday to match time.localtime().
_DAY_LABELS = ('S', 'M', 'T', 'W', 'T', 'F', 'S')
_DAY_BITS = (6, 0, 1, 2, 3, 4, 5)


class AlarmApp:
    """Allows the user to set a vibration alarm.
    """
    NAME = 'Alarm'
    ICON = icon

    def __init__(self):
        """Initialize the application."""

        self.page = _HOME_PAGE
        self.step = _TIME_STEP
        self.scroll = 0
        # True while the alarm being edited has not been added to the list yet.
        self.draft = False
        self.alarms = tuple([bytearray(3) for _ in range(_MAX_ALARMS)])
        self.pending_alarms = array.array('d', [0.0] * _MAX_ALARMS)

        self.num_alarms = 0
        try:
            with open("alarms.txt", "r") as f:
                alarms = f.readlines()[0].split(";")
            if "" in alarms:
                alarms.remove("")
            for alarm in alarms:
                n = self.num_alarms
                if n >= _MAX_ALARMS:
                    break
                h, m, st = map(int, alarm.split(","))
                self.alarms[n][0] = h
                self.alarms[n][1] = m
                self.alarms[n][2] = st
                self.num_alarms += 1
        except Exception:
            pass
        self._set_pending_alarms()

    def foreground(self):
        """Activate the application."""

        self.alarm_checks = tuple([widgets.Checkbox(200, _MARGIN + i * _ROW_PITCH + 11)
                                   for i in range(_ROWS)])

        self._deactivate_pending_alarms()
        self._draw()

        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.SWIPE_LEFTRIGHT |
                                  wasp.EventMask.SWIPE_UPDOWN |
                                  wasp.EventMask.BUTTON)
        wasp.system.request_tick(1000)

    def background(self):
        """De-activate the application."""
        # An unfinished alarm is thrown away rather than half added.
        self.draft = False
        self.page = _HOME_PAGE
        self.step = _TIME_STEP

        self.alarm_checks = None
        del self.alarm_checks

        self._set_pending_alarms()
        try:
            if self.num_alarms == 0:
                return
            with open("alarms.txt", "w") as f:
                for n in range(self.num_alarms):
                    al = self.alarms[n]
                    f.write(",".join(map(str, al)) + ";")
        except Exception:
            pass

    def tick(self, ticks):
        """Notify the application that its periodic tick is due."""
        if self.page == _RINGING_PAGE:
            wasp.watch.vibrator.pulse(duty=50, ms=500)
            wasp.system.keep_awake()

    def press(self, button, state):
        """"Notify the application of a button press event."""
        wasp.system.navigate(wasp.EventType.HOME)

    def swipe(self, event):
        """"Notify the application of a swipe event."""
        if self.page == _RINGING_PAGE:
            self._snooze()
        elif self.page > _HOME_PAGE:
            # The editor moves on the vertical axis only. Left and right are
            # swallowed so an edit in progress cannot be swiped away.
            if event[0] == wasp.EventType.UP:
                self._step(1)
            elif event[0] == wasp.EventType.DOWN:
                self._step(-1)
        elif event[0] == wasp.EventType.UP:
            self._scroll_list(1)
        elif event[0] == wasp.EventType.DOWN:
            self._scroll_list(-1)
        else:
            wasp.system.navigate(event[0])

    def touch(self, event):
        """Notify the application of a touchscreen touch event."""
        if self.page == _RINGING_PAGE:
            self._snooze()
        elif self.page > _HOME_PAGE:
            if self.step == _TIME_STEP:
                self._touch_time(event)
            elif self.step == _DAYS_STEP:
                self._touch_days(event)
            else:
                self._touch_save(event)
        else:
            self._touch_list(event)

    # Navigation

    def _scroll_list(self, direction):
        """Move the list one page up or down, if there is one."""
        page = self.scroll + direction
        if page < 0 or page >= self._num_pages:
            wasp.watch.vibrator.pulse()
            return
        self.scroll = page
        self._draw()

    def _step(self, direction):
        """Walk the editor one page on, or one page back.

        Swiping up moves on, matching the way the list scrolls, and swiping
        down past the first page leaves the editor.

        :param direction: 1 to move on, -1 to go back
        """
        if direction > 0:
            if self.step < _SAVE_STEP:
                self.step += 1
                self._draw()
            else:
                wasp.watch.vibrator.pulse()
        elif self.step > _TIME_STEP:
            self.step -= 1
            self._draw()
        else:
            self._close_editor()

    def _open_editor(self, index, draft=False):
        self.page = index
        self.step = _TIME_STEP
        self.draft = draft
        self._draw()

    def _close_editor(self):
        """Leave the editor without keeping an unfinished alarm."""
        self.draft = False
        self.page = _HOME_PAGE
        self.step = _TIME_STEP
        self._draw()

    @property
    def _num_pages(self):
        """Pages needed for every alarm plus the add tile."""
        tiles = min(self.num_alarms + 1, _MAX_ALARMS)
        return (tiles + _ROWS - 1) // _ROWS

    # Touch handling

    def _touch_list(self, event):
        row = (event[2] - _MARGIN) // _ROW_PITCH
        if row < 0 or row >= _ROWS:
            return
        index = self.scroll * _ROWS + row

        if index < self.num_alarms:
            checkbox = self.alarm_checks[row]
            if checkbox.touch(event):
                if checkbox.state:
                    self.alarms[index][_ENABLED_IDX] |= _IS_ACTIVE
                else:
                    self.alarms[index][_ENABLED_IDX] &= ~_IS_ACTIVE
                self._draw(row)
                return
            self._open_editor(index)
        elif index == self.num_alarms and index < _MAX_ALARMS:
            # The add tile starts a fresh alarm at a sensible hour.
            alarm = self.alarms[index]
            alarm[_HOUR_IDX] = 8
            alarm[_MIN_IDX] = 0
            alarm[_ENABLED_IDX] = _IS_ACTIVE
            self._open_editor(index, True)

    def _touch_time(self, event):
        col = 0 if event[1] < 120 else 1
        row = (event[2] - _MARGIN) // _ROW_PITCH
        if row != 1 and row != 3:
            return
        alarm = self.alarms[self.page]
        step = 1 if row == 1 else -1
        if col == 0:
            alarm[_HOUR_IDX] = (alarm[_HOUR_IDX] + step) % 24
        else:
            alarm[_MIN_IDX] = (alarm[_MIN_IDX] + 5 * step) % 60
        self._draw_time_values()

    def _touch_days(self, event):
        col = (event[1] - _MARGIN) // _DAY_PITCH
        row = (event[2] - _MARGIN) // _CELL_PITCH
        if col < 0 or col >= 4 or row < 0 or row >= 2:
            return
        i = row * 4 + col
        if i >= len(_DAY_LABELS):
            return
        alarm = self.alarms[self.page]
        alarm[_ENABLED_IDX] ^= 1 << _DAY_BITS[i]
        self._draw_day(i)

    def _touch_save(self, event):
        if event[2] < _ACTION_Y:
            return
        if event[1] < 120:
            self._remove_alarm(self.page)
        else:
            self._save_alarm()

    # Alarm list

    def _remove_alarm(self, alarm_index):
        if self.draft:
            self._close_editor()
            return

        # Shift alarm indices
        for index in range(alarm_index, _MAX_ALARMS - 1):
            self.alarms[index][_HOUR_IDX] = self.alarms[index + 1][_HOUR_IDX]
            self.alarms[index][_MIN_IDX] = self.alarms[index + 1][_MIN_IDX]
            self.alarms[index][_ENABLED_IDX] = self.alarms[index + 1][_ENABLED_IDX]
            self.pending_alarms[index] = self.pending_alarms[index + 1]

        # Set last alarm to default
        last = self.alarms[_MAX_ALARMS - 1]
        last[_HOUR_IDX] = 8
        last[_MIN_IDX] = 0
        last[_ENABLED_IDX] = 0

        self.num_alarms -= 1
        self._close_editor()

    def _save_alarm(self):
        if self.draft:
            self.num_alarms += 1
            self.draft = False
        self.page = _HOME_PAGE
        self.step = _TIME_STEP
        self.scroll = min(self.scroll, self._num_pages - 1)
        self._draw()

    # Drawing

    def _draw(self, update_alarm_row=-1):
        if self.page == _RINGING_PAGE:
            self._draw_ringing_page()
        elif self.page > _HOME_PAGE:
            if self.step == _TIME_STEP:
                self._draw_time_page()
            elif self.step == _DAYS_STEP:
                self._draw_days_page()
            else:
                self._draw_save_page()
        else:
            self._draw_home_page(update_alarm_row)

    def _draw_ringing_page(self):
        draw = wasp.watch.drawable

        draw.set_color(wasp.system.theme('bright'))
        draw.fill()
        draw.set_font(fonts.sans24)
        draw.string("Alarm", 0, 150, width=240)
        draw.string("Touch to snooze", 0, 180, width=240)
        draw.blit(icon, 104, 70)
        draw.line(35, 1, 35, 239)
        draw.string('S', 10, 65)
        draw.string('t', 10, 95)
        draw.string('o', 10, 125)
        draw.string('p', 10, 155)

    def _draw_home_page(self, update_alarm_row=-1):
        draw = wasp.watch.drawable

        if update_alarm_row >= 0:
            self._draw_alarm_row(update_alarm_row)
            return

        # Clear to black explicitly: fill() would otherwise reuse whatever
        # background colour the last set_color left behind.
        draw.fill(0)
        for row in range(_ROWS):
            index = self.scroll * _ROWS + row
            if index > self.num_alarms or index >= _MAX_ALARMS:
                # A slot past the add row gets no tile at all.
                continue
            draw.rounded_rect(_MARGIN, _MARGIN + row * _ROW_PITCH,
                              _ROW_W, _ROW_H, _TILE_COLOR)
            if index < self.num_alarms:
                self._draw_alarm_row(row)
            else:
                self._draw_add_row(row)
        self._draw_indicator()

    def _draw_indicator(self):
        """Draw the list's page indicator down the right hand edge."""
        cards.scrollbar(wasp.watch.drawable, self.scroll, self._num_pages,
                        wasp.system.theme('scroll-indicator'))

    def _draw_step_indicator(self):
        """Show which of the editor's three pages is on screen."""
        cards.scrollbar(wasp.watch.drawable, self.step, _SAVE_STEP + 1,
                        wasp.system.theme('scroll-indicator'))

    def _draw_alarm_row(self, row):
        draw = wasp.watch.drawable
        index = self.scroll * _ROWS + row
        alarm = self.alarms[index]
        y = _MARGIN + row * _ROW_PITCH

        checkbox = self.alarm_checks[row]
        checkbox.state = alarm[_ENABLED_IDX] & _IS_ACTIVE
        checkbox.draw()

        if checkbox.state:
            fg = wasp.system.theme('bright')
        else:
            fg = wasp.system.theme('mid')
        draw.set_color(fg, _TILE_COLOR)

        draw.set_font(fonts.sans28)
        draw.string("{:02d}:{:02d}".format(alarm[_HOUR_IDX], alarm[_MIN_IDX]),
                    12, y + 13, width=110)

        draw.set_font(fonts.sans18)
        draw.string(self._get_repeat_code(alarm[_ENABLED_IDX]),
                    126, y + 19, width=66)

    def _draw_add_row(self, row):
        draw = wasp.watch.drawable
        y = _MARGIN + row * _ROW_PITCH
        draw.rleblit(plus_icon, (104, y + 11),
                     wasp.system.theme('bright'), _TILE_COLOR)

    def _draw_time_page(self):
        draw = wasp.watch.drawable

        # Clear to black explicitly: fill() would otherwise reuse whatever
        # background colour the last set_color left behind.
        draw.fill(0)
        for row in range(4):
            for col in range(2):
                draw.rounded_rect(_MARGIN + col * _CELL_PITCH,
                                  _MARGIN + row * _ROW_PITCH,
                                  _CELL_W, _ROW_H, _TILE_COLOR)
        draw.set_color(wasp.system.theme('bright'), _TILE_COLOR)

        draw.set_font(fonts.sans24)
        draw.string('H', _MARGIN, _MARGIN + 15, width=_CELL_W)
        draw.string('M', _MARGIN + _CELL_PITCH, _MARGIN + 15, width=_CELL_W)

        draw.set_font(fonts.sans28)
        for col in range(2):
            x = _MARGIN + col * _CELL_PITCH
            draw.string('+', x, _MARGIN + _ROW_PITCH + 13, width=_CELL_W)
            draw.string('-', x, _MARGIN + 3 * _ROW_PITCH + 13, width=_CELL_W)

        self._draw_time_values()
        self._draw_step_indicator()

    def _draw_time_values(self):
        draw = wasp.watch.drawable
        alarm = self.alarms[self.page]
        y = _MARGIN + 2 * _ROW_PITCH + 13

        draw.set_color(wasp.system.theme('bright'), _TILE_COLOR)
        draw.set_font(fonts.sans28)
        draw.string('{:02d}'.format(alarm[_HOUR_IDX]), _MARGIN, y, width=_CELL_W)
        draw.string('{:02d}'.format(alarm[_MIN_IDX]),
                    _MARGIN + _CELL_PITCH, y, width=_CELL_W)

    def _draw_days_page(self):
        draw = wasp.watch.drawable

        # Clear to black explicitly: fill() would otherwise reuse whatever
        # background colour the last set_color left behind.
        draw.fill(0)
        for i in range(len(_DAY_LABELS)):
            draw.rounded_rect(_MARGIN + (i % 4) * _DAY_PITCH,
                              _MARGIN + (i // 4) * _CELL_PITCH,
                              _DAY_W, _DAY_H, _TILE_COLOR)
        for i in range(len(_DAY_LABELS)):
            self._draw_day(i)
        self._draw_step_indicator()

    def _draw_day(self, i):
        """Draw one day tile, underlined when the alarm repeats on that day."""
        draw = wasp.watch.drawable
        alarm = self.alarms[self.page]
        x = _MARGIN + (i % 4) * _DAY_PITCH
        y = _MARGIN + (i // 4) * _CELL_PITCH
        on = alarm[_ENABLED_IDX] & (1 << _DAY_BITS[i])

        draw.set_color(wasp.system.theme('bright') if on
                       else wasp.system.theme('mid'), _TILE_COLOR)
        draw.set_font(fonts.sans24)
        draw.string(_DAY_LABELS[i], x, y + 36, width=_DAY_W)

        # A bar under the letter, well inside the tile's rounded corners.
        draw.fill(wasp.system.theme('ui') if on else _TILE_COLOR,
                  x + 15, y + 70, 25, 5)

    def _draw_save_page(self):
        draw = wasp.watch.drawable
        alarm = self.alarms[self.page]

        # Clear to black explicitly: fill() would otherwise reuse whatever
        # background colour the last set_color left behind.
        draw.fill(0)
        draw.rounded_rect(_MARGIN, _SUMMARY_Y, _ROW_W, _SUMMARY_H, _TILE_COLOR)
        for col in range(2):
            draw.rounded_rect(_MARGIN + col * _CELL_PITCH, _ACTION_Y,
                              _CELL_W, _ACTION_H, _TILE_COLOR)

        draw.set_color(wasp.system.theme('bright'), _TILE_COLOR)
        draw.set_font(fonts.sans28)
        draw.string("{:02d}:{:02d}".format(alarm[_HOUR_IDX], alarm[_MIN_IDX]),
                    _MARGIN, 55, width=_ROW_W)
        draw.set_font(fonts.sans24)
        draw.string(self._get_repeat_name(alarm[_ENABLED_IDX]),
                    _MARGIN, 105, width=_ROW_W)

        bright = wasp.system.theme('bright')
        draw.rleblit(trash_icon, (45, _ACTION_Y + 21), bright, _TILE_COLOR)
        draw.rleblit(save_icon, (163, _ACTION_Y + 21), bright, _TILE_COLOR)
        self._draw_step_indicator()

    # Alarm scheduling

    def _alert(self):
        self.page = _RINGING_PAGE
        wasp.system.wake()
        wasp.system.switch(self)

    def _snooze(self):
        now = wasp.watch.rtc.get_localtime()
        alarm = (now[0], now[1], now[2], now[3], now[4] + 10, now[5], 0, 0, 0)
        wasp.system.set_alarm(time.mktime(alarm), self._alert)
        wasp.system.navigate(wasp.EventType.HOME)

    def _set_pending_alarms(self):
        now = wasp.watch.rtc.get_localtime()
        for index, alarm in enumerate(self.alarms):
            if index < self.num_alarms and alarm[_ENABLED_IDX] & _IS_ACTIVE:
                yyyy = now[0]
                mm = now[1]
                dd = now[2]
                HH = alarm[_HOUR_IDX]
                MM = alarm[_MIN_IDX]

                # If next alarm is tomorrow increment the day
                if HH < now[3] or (HH == now[3] and MM <= now[4]):
                    dd += 1

                pending_time = time.mktime((yyyy, mm, dd, HH, MM, 0, 0, 0, 0))

                # If this is not a one time alarm find the next day of the week that is enabled
                if alarm[_ENABLED_IDX] & ~_IS_ACTIVE != 0:
                    for _i in range(7):
                        if (1 << time.localtime(pending_time)[6]) & alarm[_ENABLED_IDX] == 0:
                            dd += 1
                            pending_time = time.mktime((yyyy, mm, dd, HH, MM, 0, 0, 0, 0))
                        else:
                            break

                self.pending_alarms[index] = pending_time
                wasp.system.set_alarm(pending_time, self._alert)
            else:
                self.pending_alarms[index] = 0.0

    def _deactivate_pending_alarms(self):
        now = wasp.watch.rtc.get_localtime()
        now = time.mktime((now[0], now[1], now[2], now[3], now[4], now[5], 0, 0, 0))
        for index, alarm in enumerate(self.alarms):
            pending_alarm = self.pending_alarms[index]
            if not pending_alarm == 0.0:
                wasp.system.cancel_alarm(pending_alarm, self._alert)
                # If this is a one time alarm and in the past disable it
                if alarm[_ENABLED_IDX] & ~_IS_ACTIVE == 0 and pending_alarm <= now:
                    alarm[_ENABLED_IDX] = 0

    @staticmethod
    def _get_repeat_code(days):
        # Ignore the is_active bit
        days = days & ~_IS_ACTIVE

        if days == _WEEKDAYS:
            return "wkds"
        elif days == _WEEKENDS:
            return "wkns"
        elif days == _EVERY_DAY:
            return "evry"
        elif days == 0:
            return "once"
        else:
            return "cust"

    @staticmethod
    def _get_repeat_name(days):
        days = days & ~_IS_ACTIVE

        if days == _WEEKDAYS:
            return "Weekdays"
        elif days == _WEEKENDS:
            return "Weekends"
        elif days == _EVERY_DAY:
            return "Every day"
        elif days == 0:
            return "Once"
        else:
            return "Custom"
