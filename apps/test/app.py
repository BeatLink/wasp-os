# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Self Tests
~~~~~~~~~~~~~

A collection of tests used to develop features or provide useful metrics such
as performance indicators or memory usage.

Swipe up and down to move between tests. Each test names itself on a card at
the top. Benchmarks draw in the space below it and show their time on a card
at the bottom; the other tests put their text on one large card.

.. figure:: apps/test/screenshot.png
    :width: 179
"""

import wasp

import cards
import gc
import fonts
import icons
import machine
import widgets

from apps.system.pager import PagerApp
from micropython import const
from widgets.page import draw_indicator

# 1-bit RLE, 32x32, generated from apps/test/icon.png, 97 bytes
icon = (
    32, 32,
    b'\t\x0e\x11\x10\x10\x10\x11\x0e\x13\x04\x04\x04\x14\x04\x04\x04'
    b'\x14\x04\x04\x04\x14\x04\x04\x04\x14\x04\x04\x04\x14\x04\x04\x04'
    b'\x14\x04\x04\x04\x14\x04\x04\x04\x14\x04\x04\x04\x14\x04\x04\x04'
    b'\x13\x05\x04\x05\x12\x04\x06\x04\x11\x05\x06\x05\x10\x04\x08\x05'
    b'\x0e\x05\x08\x05\r\x05\n\x05\x0c\x14\x0b\x16\t\x18\x08\x18'
    b'\x07\x1a\x06\x1a\x05\x1c\x04\x1c\x04\x1c\x04\x1c\x05\x1a\x07\x18'
    b'\x04'
)

# Five rows: the title, three for the test itself, then the result.
_ROW_H = cards.size(5)
_ROWS = cards.edges((_ROW_H,) * 5)
_BODY_Y = _ROWS[1]
_BODY_H = _ROWS[3] + _ROW_H - _BODY_Y
_FOOT_Y = _ROWS[4]
# The large card runs from the body to the bottom margin.
_PANEL_H = _FOOT_Y + _ROW_H - _BODY_Y
# Inset that keeps text clear of the card's rounded corners.
_INSET = const(12)
_TEXT_X = const(16)
_TEXT_W = const(208)

# Tests that time a drawing primitive and report it on the bottom card.
_BENCHMARKS = ('Fill', 'Fill-H', 'Fill-V', 'Line', 'RLE', 'String', 'Wrap')

class TestApp():
    """Self test application."""
    NAME = 'Self Test'
    ICON = icon

    def __init__(self):
        self.tests = ('Alarm', 'Button', 'Checkbox', 'Crash', 'Colours', 'Fill', 'Fill-H', 'Fill-V', 'Free Mem', 'Line', 'Notifications', 'RLE', 'String', 'Touch', 'Wrap')
        self.test = self.tests[0]

        self._checkbox = widgets.Checkbox(200, _BODY_Y + 6)
        self._sliders = (
                widgets.Slider(32, 10, _ROWS[2] + 2, 0xf800),
                widgets.Slider(64, 10, _ROWS[3] + 2, 0x27e4),
                widgets.Slider(32, 10, _ROWS[4] + 2, 0x211f),
        )
        self._spinner = widgets.Spinner(cards.edges((75,) * 3)[1], _BODY_Y,
                                        0, 99, w=75, h=_PANEL_H)

    def foreground(self):
        """Activate the application."""
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.SWIPE_UPDOWN |
                                  wasp.EventMask.BUTTON)

    def press(self, button, state):
        if self.test == 'Alarm':
            self._test_alarm()
        elif self.test == 'Button':
            self._message('{}: {}'.format(button, state))
        elif self.test == 'Crash':
            self.crash()
        elif self.test == 'String':
            self._benchmark_string()
        elif self.test == 'Touch':
            self._message('Button')

    def crash(self):
        """Throw an exception, so the crash handler can be tested."""
        raise RuntimeError('Deliberate crash')

    def swipe(self, event):
        tests = self.tests
        i = tests.index(self.test)

        if event[0] == wasp.EventType.UP:
            i += 1
            if i >= len(tests):
                i = 0
        else:
            i -= 1
            if i < 0:
                i = len(tests) - 1
        self.test = tests[i]
        self._draw()

    def touch(self, event):
        if self.test == 'Checkbox':
            # The whole card toggles the checkbox.
            if _BODY_Y <= event[2] < _BODY_Y + _ROW_H:
                self._checkbox.state = not self._checkbox.state
                self._checkbox.update()
        elif self.test == 'Colours':
            if event[2] >= _ROWS[2]:
                i = (event[2] - _ROWS[2]) // (_ROWS[3] - _ROWS[2])
                s = self._sliders[min(i, 2)]
                s.touch(event)
                s.update()
                self._update_colours()
        elif self.test.startswith('Fill'):
            self._benchmark_fill()
        elif self.test == 'Notifications':
            if self._spinner.touch(event):
                notifications = wasp.system.notifications

                if len(notifications) > self._spinner.value:
                    wasp.system.unnotify(
                            next(iter(notifications.keys())))
                else:
                    wasp.system.notify(wasp.watch.rtc.get_uptime_ms(),
                        {
                            "src":"Hangouts",
                            "title":"A Name",
                            "body":"message contents"
                        })
        elif self.test == 'RLE':
            self._benchmark_rle()
        elif self.test == 'String':
            self._benchmark_string()
        elif self.test == 'Touch':
            self._message('({}, {})'.format(event[1], event[2]))
        elif self.test == 'Wrap':
            self._benchmark_wrap()
        elif self.test == 'Line':
            self._benchmark_line()

    def _alarm(self):
        wasp.system.wake()
        wasp.system.switch(PagerApp('Alarm triggered'))

    def _test_alarm(self):
        def nop():
            pass
        now = wasp.watch.rtc.time()
        wasp.system.set_alarm(now + 30, self._alarm)
        wasp.system.set_alarm(now + 30, nop)
        if not wasp.system.cancel_alarm(now + 30, nop):
            raise AssertionError('cancel_alarm did not find the alarm')
        self._message('Done.')

    def _clear_body(self, card=False):
        """Blank the space between the title and result cards."""
        draw = wasp.watch.drawable
        draw.fill(0, 0, _BODY_Y, cards.SCROLLBAR_X, _BODY_H)
        if card:
            draw.rounded_rect(cards.MARGIN, _BODY_Y, cards.SPAN, _BODY_H,
                              cards.COLOR)

    def _result(self, text):
        """Show text on the result card along the bottom."""
        draw = wasp.watch.drawable
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans24)
        draw.string(text, _TEXT_X, _FOOT_Y + 10, width=_TEXT_W)

    def _message(self, text):
        """Show text across the middle of the large card."""
        draw = wasp.watch.drawable
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans24)
        draw.string(text, _TEXT_X, 132, width=_TEXT_W)

    def _benchmark_rle(self):
        draw = wasp.watch.drawable
        self._clear_body()
        t = machine.Timer(id=1, period=8000000)
        t.start()
        for i in range(0, 128, 16):
            draw.blit(icons.software, i+40, _BODY_Y + 5 + i // 2)
        elapsed = t.time()
        t.stop()
        del t
        self._result('{}s'.format(elapsed / 1000000))

    def _benchmark_fill(self):
        draw = wasp.watch.drawable
        self._clear_body()
        y = _BODY_Y + 9
        t = machine.Timer(id=1, period=8000000)
        if self.test == 'Fill':
            t.start()
            draw.fill(0xffff, 60, y, 120, 120)
            elapsed = t.time()
        elif self.test == 'Fill-H':
            t.start()
            for i in range(y, y + 120, 2):
                draw.fill(0xffff, 60, i, 120, 1)
            elapsed = t.time()
        elif self.test == 'Fill-V':
            t.start()
            for i in range(60, 180, 2):
                draw.fill(0xffff, i, y, 1, 120)
            elapsed = t.time()

        t.stop()
        del t
        self._result('{}s'.format(elapsed / 1000000))

    def _benchmark_string(self):
        draw = wasp.watch.drawable
        self._clear_body(True)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans24)
        y = _BODY_Y + 9
        t = machine.Timer(id=1, period=8000000)
        t.start()
        draw.string("The quick brown", _TEXT_X, y)
        draw.string("fox jumped over", _TEXT_X, y+24)
        draw.string("the lazy dog.", _TEXT_X, y+48)
        draw.string("0123456789", _TEXT_X, y+72, width=_TEXT_W)
        draw.string('!"£$%^&*()', _TEXT_X, y+96, width=_TEXT_W)
        elapsed = t.time()
        t.stop()
        del t
        self._result('{}s'.format(elapsed / 1000000))

    def _benchmark_line(self):
        draw = wasp.watch.drawable
        # instead of calculating by trig functions, use LUT
        points = (0, 50), (19, 46), (35, 35), (46, 19),
        cy = _BODY_Y + _BODY_H // 2

        self._clear_body()
        t = machine.Timer(id=1, period=8000000)
        t.start()
        for x, y in points:
            draw.line(120, cy, 120+x, cy+y, 4, 0xfb00)  # red
            draw.line(120, cy, 120+y, cy-x, 3, 0x07c0)  # green
            draw.line(120, cy, 120-x, cy-y, 5, 0x6b3f)  # blue
            draw.line(120, cy, 120-y, cy+x, 2, 0xffe0)  # yellow
        elapsed = t.time()
        t.stop()
        del t
        self._result('{}s'.format(elapsed / 1000000))

    def _benchmark_wrap(self):
        draw = wasp.watch.drawable
        self._clear_body(True)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        # The smaller font fits the wrapped lines on the card.
        draw.set_font(fonts.sans18)
        t = machine.Timer(id=1, period=8000000)
        t.start()
        s = 'This\nis a very long string that will need to be wrappedinmultipledifferentways!'
        chunks = draw.wrap(s, _TEXT_W)

        for i in range(len(chunks)-1):
            sub = s[chunks[i]:chunks[i+1]].rstrip()
            draw.string(sub, _TEXT_X, _BODY_Y + 9 + 20*i)
        elapsed = t.time()
        t.stop()
        del t
        self._result('{}s'.format(elapsed / 1000000))

    def _draw(self):
        """Redraw the display from scratch."""
        wasp.watch.display.mute(True)
        draw = wasp.watch.drawable
        draw.fill(0)
        draw.rounded_rect(cards.MARGIN, cards.MARGIN, cards.SPAN, _ROW_H,
                          cards.COLOR)
        bright = wasp.system.theme('bright')
        draw.set_color(bright, cards.COLOR)
        draw.set_font(fonts.sans24)
        draw.string(self.test, _TEXT_X, cards.MARGIN + 10, width=_TEXT_W)

        test = self.test
        if test in _BENCHMARKS:
            draw.rounded_rect(cards.MARGIN, _FOOT_Y, cards.SPAN, _ROW_H,
                              cards.COLOR)
            draw.set_color(wasp.system.theme('mid'), cards.COLOR)
            draw.string('Tap to run', _TEXT_X, _FOOT_Y + 10, width=_TEXT_W)
            if test == 'RLE':
                draw.blit(self.ICON, 120-16, _BODY_Y + _BODY_H // 2 - 16)
        elif test == 'Checkbox':
            draw.rounded_rect(cards.MARGIN, _BODY_Y, cards.SPAN, _ROW_H,
                              cards.COLOR)
            draw.string('Check me', _TEXT_X, _BODY_Y + 10)
            self._checkbox.draw()
        elif test == 'Colours':
            for s in self._sliders:
                s.draw()
            self._update_colours()
        elif test == 'Notifications':
            self._spinner.value = len(wasp.system.notifications)
            self._spinner.draw()
        else:
            # The remaining tests show text on one large card.
            draw.rounded_rect(cards.MARGIN, _BODY_Y, cards.SPAN, _PANEL_H,
                              cards.COLOR)
            y = _BODY_Y + 12
            if test == 'Alarm':
                draw.string("Press button to", _TEXT_X, y)
                draw.string("set alarm.", _TEXT_X, y+24)
            elif test == 'Crash':
                draw.string("Press button to", _TEXT_X, y)
                draw.string("throw exception.", _TEXT_X, y+24)
            elif test == 'Free Mem':
                if wasp.watch.free:
                    draw.string("Boot: {}".format(wasp.watch.free), _TEXT_X, y)
                    draw.string("Init: {}".format(wasp.free), _TEXT_X, y+24)
                    draw.string("Now: {}".format(gc.mem_free()), _TEXT_X, y+48)
                    gc.collect()
                    draw.string("GC: {}".format(gc.mem_free()), _TEXT_X, y+72)
                else:
                    draw.string("Not supported", _TEXT_X, y)
            elif test in ('Button', 'Touch'):
                draw.set_color(wasp.system.theme('mid'), cards.COLOR)
                draw.string('Press or tap', _TEXT_X, y)

        draw_indicator(self.tests.index(test), len(self.tests))
        wasp.watch.display.mute(False)

    def _update_colours(self):
        draw = wasp.watch.drawable
        r = self._sliders[0].value
        g = self._sliders[1].value
        b = self._sliders[2].value
        rgb = (r << 11) + (g << 5) + b

        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans24)
        draw.string('RGB565 #{:04x}'.format(rgb), _TEXT_X, cards.MARGIN + 10,
                    width=_TEXT_W)
        draw.rounded_rect(cards.MARGIN, _BODY_Y, cards.SPAN, _ROW_H, rgb)
