# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2022 github user thiswillbeyourgithub
"""Pomodoro Application
~~~~~~~~~~~~~~~~~~~~~~~

A pomodoro app, forked from timer.py. Swipe laterally to load presets and vertically
to change number of vibration. Vibration patterns are randomized if vibrating
more than 4 times to make sure you notice.

.. figure:: apps/pomodoro/screenshot.png
    :width: 179
"""

import wasp
import cards
import fonts
import widgets
import math
import random
from micropython import const

# 1-bit RLE, 32x32, generated from apps/pomodoro/icon.png, 83 bytes
icon = (
    32, 32,
    b'\x05\x16\t\x18\x08\x18\t\x16\x0b\x04\x0c\x04\x0c\x04\x0c\x04'
    b'\x0c\x04\x0c\x04\x0c\x05\n\x05\r\x12\x0e\x12\x0f\x10\x11\x0e'
    b'\x13\x0c\x15\n\x17\x08\x19\x06\x1a\x06\x19\x08\x17\n\x15\x05'
    b'\x02\x05\x13\x05\x04\x05\x11\x05\x06\x05\x0f\x05\x08\x05\x0e\x04'
    b'\n\x04\r\x14\x0c\x14\x0c\x14\x0c\x14\x0b\x16\t\x18\x08\x18'
    b'\t\x16\x05'
)


_STOPPED = const(0)
_RUNNING = const(1)
_RINGING = const(2)
_REPEAT_MAX = const(99)  # auto stop repeat after 99 runs
_FIELDS = const(1234567890)
_MAX_VIB = const(15)  # max number of second the watch you vibrate

# you can add your own presets here:
_PRESETS = ['2,10', '10,2', '20,5']
_TIME_MODE = const(1)  # if 0: duration of vibration will be discounted
# from timer. if 1: not discounted


# Four rows of cards: a header, two rows of digits, then the actions.
_ROW_H = cards.size(4)
_TOPS = cards.edges((_ROW_H,) * 4)
_KEY_W = cards.size(5)
_KEYS = cards.edges((_KEY_W,) * 5)
_ACTION_W = cards.size(3)
_ACTIONS = cards.edges((_ACTION_W,) * 3)
# While running, a wide stop card sits beside a narrow +1 card.
_ADD_W = _ACTION_W
_STOP_W = cards.SPAN - _ADD_W - cards.GAP - 1
_STOP_X, _ADD_X = cards.edges((_STOP_W, _ADD_W))
_TIME_H = _TOPS[2] + _ROW_H - _TOPS[1]
_TEXT_Y = (_ROW_H - 24) // 2

class PomodoroApp():
    """Allows the user to set a periodic vibration alarm, Pomodoro style."""
    NAME = 'Pomodoro'

    @property
    def PERSIST(self):
        """Stay resident while running, because the alarm callback holds this instance."""
        return self.state != _STOPPED
    ICON = icon

    def __init__(self):
        self._already_initialized = False

    def _actual_init(self):
        self.current_alarm = None
        self.nb_vibrat_total = _STOPPED  # number of time it vibrated
        self.last_preset = _STOPPED
        self.last_run = -1  # to keep track of where in the queue we are
        self.state = _STOPPED

        # reloading last value
        try:
            last_val = wasp.system.get("pomodoro")
            self.nb_vibrat_per_alarm = int(last_val[0])
            self.queue = last_val[1]
        except:
            self.queue = _PRESETS[0]
            self.nb_vibrat_per_alarm = 10 # number of times to vibrate each time
        return True

    def foreground(self):
        if not self._already_initialized:
            self._already_initialized = self._actual_init()
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.SWIPE_LEFTRIGHT |
                                  wasp.EventMask.SWIPE_UPDOWN)
        wasp.system.request_tick(1000)

    def background(self):
        if self.state == _RINGING:
            self._start()
        elif self.state == _STOPPED:
            self.__init__()

    def sleep(self):
        """don't exit when screen turns off"""
        return True

    def tick(self, ticks):
        if self.state == _RINGING:
            if self.nb_vibrat_per_alarm <= 3:
                wasp.watch.vibrator.pulse(duty=50, ms=650)
            else:
                if random.random() > 0.7:  # one very long vibration
                    wasp.watch.vibrator.pulse(duty=random.randint(3, 60),
                                              ms=900)
                else:  # burst of vibration
                    max_dur = 900
                    done = 0
                    while done <= max_dur:
                        new_vibr = random.randint(20, 200)
                        new_sleep = random.randint(0, 300)
                        while done + new_vibr + new_sleep > max_dur * 1.1:
                            new_vibr = random.randint(20, 200)
                            new_sleep = random.randint(0, 300)
                        wasp.watch.vibrator.pulse(duty=3, ms=new_vibr)
                        wasp.watch.time.sleep(new_sleep * 0.001)
                        done += new_vibr + new_sleep
            wasp.system.keep_awake()
            self.nb_vibrat_total += 1
            if self.nb_vibrat_total % self.nb_vibrat_per_alarm == 0:
                # vibrated self.nb_vibrat_per_alarm times so
                # no more repeat needed
                if self.nb_vibrat_total // self.nb_vibrat_per_alarm // len(self.squeue) < _REPEAT_MAX:
                    # restart another
                    self._start()
                else:  # avoid running for days if forgotten
                    self._stop()

        else:
            self._update()

    def swipe(self, event):
        if self.state == _STOPPED:
            if event[0] == wasp.EventType.UP:
                self.nb_vibrat_per_alarm = max(1, (self.nb_vibrat_per_alarm + 1) % (_MAX_VIB + 1))
            elif event[0] == wasp.EventType.DOWN:
                self.nb_vibrat_per_alarm -= 1
                if self.nb_vibrat_per_alarm == 0:
                    self.nb_vibrat_per_alarm = _MAX_VIB
            else:
                if event[0] == wasp.EventType.RIGHT:
                    self.last_preset += 1
                elif event[0] == wasp.EventType.LEFT:
                    self.last_preset -= 1
                self.last_preset %= len(_PRESETS)
                self.queue = _PRESETS[self.last_preset]
            self._draw_header()

    def touch(self, event):
        if self.state == _RINGING:
            mute = wasp.watch.display.mute
            mute(False)
        elif self.state == _RUNNING:
            if self.btn_stop.touch(event):
                self._stop()
            elif self.btn_add.touch(event):
                wasp.system.cancel_alarm(self.current_alarm, self._alert)
                self.current_alarm += 60
                wasp.system.set_alarm(self.current_alarm, self._alert)
                wasp.watch.vibrator.pulse(duty=25, ms=50)
                self._update()
        elif self.state == _STOPPED:
            if self.btn_del.touch(event):
                if len(self.queue) > 1:
                    self.queue = self.queue[:-1]
                else:
                    self.queue = ""
            elif self.btn_start.touch(event):
                if self.queue != "" and not self.queue.endswith(","):
                    self.squeue = [int(x) for x in self.queue.split(",")]
                    self._start(first_run=True)
                    return
            elif len(self.queue) < 13:
                if self.btn_add.touch(event):
                    if len(self.queue) >= 1 and self.queue[-1] != ",":
                        self.queue += ","
                else:
                    for i, b in enumerate(self.btns):
                        if b.touch(event):
                            self.queue += str((i + 1) % 10)
                            break
            self._draw_header()

    def _start(self, first_run=False):
        if self.btns is not None:  # save some memory
            for b in self.btns:
                b = None
                del b
            self.btns = None
        wasp.gc.collect()

        self.state = _RUNNING
        now = wasp.watch.rtc.time()
        self.last_run += 1
        if self.last_run >= len(self.squeue):
            self.last_run = 0
        m = self.squeue[self.last_run]

        # reduce by one second if repeating, to avoid growing offset
        if first_run or _TIME_MODE == 1:
            self.current_alarm = now + max(m * 60, 1)
        else:
            self.current_alarm = now + max(m * 60 - self.nb_vibrat_per_alarm, 1)
        wasp.system.set_alarm(self.current_alarm, self._alert)
        self._draw()
        if hasattr(wasp.system, "set") and callable(wasp.system.set):
            wasp.system.set("pomodoro", [self.nb_vibrat_per_alarm, self.queue])

    def _stop(self):
        self.state = _STOPPED
        wasp.system.cancel_alarm(self.current_alarm, self._alert)
        self.last_run = -1
        self.nb_vibrat_total = 0
        self._draw()

    def _draw(self):
        """Draw the display from scratch."""
        draw = wasp.watch.drawable
        draw.fill(0)
        draw.set_font(fonts.sans24)
        Button = widgets.Button

        if self.state == _RINGING:
            draw.rounded_rect(cards.MARGIN, cards.MARGIN, cards.SPAN,
                              cards.SPAN, cards.COLOR)
            draw.set_color(wasp.system.theme('bright'), cards.COLOR)
            draw.string(self.NAME, cards.MARGIN, 150, width=cards.SPAN)
            draw.rleblit(icon, (104, 80), wasp.system.theme('bright'),
                         cards.COLOR)
        elif self.state == _RUNNING:
            self.btn_stop = Button(_STOP_X, _TOPS[3], _STOP_W, _ROW_H, "Stop")
            self.btn_stop.draw()
            self.btn_add = Button(_ADD_X, _TOPS[3], _ADD_W, _ROW_H, "+1")
            self.btn_add.draw()
            draw.rounded_rect(cards.MARGIN, _TOPS[0], cards.SPAN, _ROW_H,
                              cards.COLOR)
            draw.rounded_rect(cards.MARGIN, _TOPS[1], cards.SPAN, _TIME_H,
                              cards.COLOR)
            t = "Timer #{}/{}  ({})".format(self.last_run + 1,
                                            len(self.squeue),
                                            self.nb_vibrat_total // self.nb_vibrat_per_alarm // len(self.squeue))
            draw.set_font(fonts.sans24)
            draw.set_color(wasp.system.theme('mid'), cards.COLOR)
            draw.string(t, cards.MARGIN, _TOPS[0] + _TEXT_Y, width=cards.SPAN)
            self._update()
        elif self.state == _STOPPED:
            self.btns = []
            fields = str(_FIELDS)
            for y in range(2):
                for x in range(5):
                    btn = Button(_KEYS[x], _TOPS[1 + y], _KEY_W, _ROW_H,
                                 fields[x + 5*y])
                    btn.draw()
                    self.btns.append(btn)
            self.btn_del = Button(_ACTIONS[0], _TOPS[3], _ACTION_W, _ROW_H,
                                  "Del.")
            self.btn_del.draw()
            self.btn_add = Button(_ACTIONS[1], _TOPS[3], _ACTION_W, _ROW_H,
                                  "Then")
            self.btn_add.draw()
            self.btn_start = Button(_ACTIONS[2], _TOPS[3], _ACTION_W, _ROW_H,
                                    "Go")
            self.btn_start.update(wasp.system.theme('ui'), None,
                                  wasp.system.theme('bright'))
            self._draw_header()

    def _draw_header(self):
        """Draw the header card: vibrations on the left, the queue on the right."""
        draw = wasp.watch.drawable
        draw.rounded_rect(cards.MARGIN, _TOPS[0], cards.SPAN, _ROW_H,
                          cards.COLOR)
        draw.set_font(fonts.sans24)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.string(self.queue, 80, _TOPS[0] + _TEXT_Y, width=140, right=True)
        draw.set_color(wasp.system.theme('mid'), cards.COLOR)
        draw.string("V{}".format(self.nb_vibrat_per_alarm), 16,
                    _TOPS[0] + _TEXT_Y)

    def _update(self):
        draw = wasp.watch.drawable
        if self.state == _RUNNING:
            now = wasp.watch.rtc.time()
            s = max(self.current_alarm - now, 0)
            m = math.floor(s // 60)
            s = math.floor(s) % 60
            if len(str(m)) > 5:
                prefix = "+"
                m = int(str(m)[-4:])
            else:
                prefix = ""
            draw.set_font(fonts.sans36)
            draw.set_color(wasp.system.theme('bright'), cards.COLOR)
            # Keep the padding inside the straight part of the card.
            draw.string("{}{:02d}:{:02d}".format(prefix, m, s),
                        cards.MARGIN + 12, _TOPS[1] + (_TIME_H - 36) // 2,
                        width=cards.SPAN - 24)

    def _alert(self):
        self.state = _RINGING
        wasp.system.wake()
        wasp.system.switch(self)
        self._draw()
