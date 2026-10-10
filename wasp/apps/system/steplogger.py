# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Step logger
~~~~~~~~~~~~~~

Capture and record data from the step counter
"""

import array
import os
import time
import wasp

from micropython import const

TICK_PERIOD = const(6 * 60)
DUMP_LENGTH = const(30)
DUMP_PERIOD = const(DUMP_LENGTH * TICK_PERIOD)
# Tick periods in a day.
_SLOTS = const(24 * 60 * 60 // TICK_PERIOD)


def _midnight(walltime):
    """The time the day holding walltime, a time.localtime() tuple, began."""
    return int(time.mktime((walltime[0], walltime[1], walltime[2],
                            0, 0, 0, 0, 0, 0)))

class StepIterator:
    """Step counts for one day, one per tick period, from the log and from RAM.

    :param fname: The day's log file, or None if nothing is saved yet
    :param data:  Counts still held in RAM, or None
    :param start: The tick of the day the counts in RAM begin at
    """
    def __init__(self, fname, data=None, start=0):
        self._fname = fname
        self._f = None
        self._d = data
        self._start = start

    def __del__(self):
        self.close()

    def __iter__(self):
        self.close()
        if self._fname:
            self._f = open(self._fname, 'rb')
        self._c = 0
        return self

    def __next__(self):
        c = self._c
        if c >= _SLOTS:
            raise StopIteration
        self._c = c + 1

        # The file holds the dumps already written, and RAM the one after them.
        d = self._d
        if self._f and (d is None or c < self._start):
            spl = self._f.read(2)
            if len(spl) == 2:
                return spl[0] + (spl[1] << 8)
            self.close()

        if d and self._start <= c < self._start + len(d):
            return d[c - self._start]

        return 0

    def close(self):
        if self._f:
            self._f.close()
            self._f = None

class StepLogger:
    def __init__(self, manager):
        self._data = array.array('H', (0,) * DUMP_LENGTH)
        self._steps = wasp.watch.accel.steps

        try:
            os.mkdir('logs')
        except:
            pass

        # Queue a tick
        self._t = int(wasp.watch.rtc.time()) // TICK_PERIOD * TICK_PERIOD
        manager.set_alarm(self._t + TICK_PERIOD, self._tick)

    def _tick(self):
        """Capture the current step count in N minute intervals.

        The samples are queued in a small RAM buffer in order to reduce
        the number of flash access. The data is written out every few hours
        in a binary format ready to be reloaded and graphed when it is
        needed.
        """
        t = self._t

        # Work out which period of the day this is, and where that falls in
        # the dump period. Both count from midnight.
        walltime = time.localtime(t)
        yyyy = walltime[0]
        mm = walltime[1]
        dd = walltime[2]
        slot = (t - _midnight(walltime)) // TICK_PERIOD
        i = slot % DUMP_LENGTH

        # Get the current step count and record it
        steps = wasp.watch.accel.steps
        # A count lower than the last means the counter was reset, so every step it holds is new.
        delta = steps - self._steps
        self._data[i] = delta if delta >= 0 else steps
        self._steps = steps

        # The next period starts a new day, so the count starts again from zero.
        if slot >= _SLOTS - 1:
            wasp.watch.accel.steps = 0
            self._steps = 0

        # Queue the next tick
        wasp.system.set_alarm(t + TICK_PERIOD, self._tick)
        self._t += TICK_PERIOD

        if i < (DUMP_LENGTH-1):
            return

        # Work out how dumps we expect to find in today's dumpfile
        dump_num = slot // DUMP_LENGTH

        # Update the log data
        try:
            os.mkdir('logs/' + str(yyyy))
        except:
            pass
        fname = 'logs/{}/{:02d}-{:02d}.steps'.format(yyyy, mm, dd)
        offset = dump_num * DUMP_LENGTH * 2
        try:
            sz = os.stat(fname)[6]
            # Not append mode, which would ignore the seek and add a dump
            # written again after a restart to the end of the file.
            f = open(fname, 'r+b')
        except:
            sz = 0
            f = open(fname, 'wb')
        # This is a portable (between real Python and MicroPython) way to
        # grow the file to the right size.
        f.seek(min(sz, offset))
        for _ in range(sz, offset, 2):
            f.write(b'\x00\x00')
        f.write(self._data)
        f.close()

        # Wipe the data
        data = self._data
        for i in range(DUMP_LENGTH):
            data[i] = 0

    def data(self, t):
        """Return the step counts for the day holding t, or None if there are none.

        :param t: A time, as seconds or as a time.localtime() tuple
        """
        try:
            yyyy = t[0]
        except:
            t = time.localtime(t)
            yyyy = t[0]
        mm = t[1]
        dd = t[2]

        fname = 'logs/{}/{:02d}-{:02d}.steps'.format(yyyy, mm, dd)
        try:
            os.stat(fname)
        except:
            fname = None

        now = time.localtime(self._t)
        if now[:3] != t[:3]:
            return StepIterator(fname) if fname else None

        # Today also has the counts still in RAM, with the period in progress
        # filled in from the counter. A copy is taken, so the next tick is
        # not disturbed.
        latest = array.array('H', self._data)
        slot = (self._t - _midnight(now)) // TICK_PERIOD
        i = slot % DUMP_LENGTH
        steps = wasp.watch.accel.steps
        delta = steps - self._steps
        latest[i] = delta if delta >= 0 else steps
        return StepIterator(fname, latest, slot - i)
