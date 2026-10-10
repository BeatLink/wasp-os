# SPDX-License-Identifier: LGPL-3.0-or-later

"""Wrist raise detection
~~~~~~~~~~~~~~~~~~~~~~~~

Spots the wrist being turned towards the face, from accelerometer readings
taken about ten times a second. The rules and thresholds are those of
InfiniTime's ``MotionController::ShouldRaiseWake``, so the two watches agree
on what a raise is.

The newest pair of readings is compared with the pair from seven readings
before. A raise is a roll of more than ``ROLL`` degrees towards the user
that ends with the arm level, the screen tilted up and the watch steady
enough that the readings are gravity rather than movement.
"""

import math

from micropython import const

# How many degrees the wrist must roll, which sets how easily a raise is seen.
ROLL = const(45)

_HISTORY = const(8)
_LEVEL = const(384)
_TILTED = const(-64)
_UPRIGHT = const(-724)
_STEADY = const(56 * 56)


def _angle(v):
    """The angle in degrees whose sine is ``v`` thousandths of gravity."""
    s = v / 1024
    if s > 1:
        s = 1
    elif s < -1:
        s = -1
    return math.asin(s) * 57.296


def _rolled(y, z, prev_y, prev_z):
    """Degrees rolled from one reading of gravity to another, carried past 90 degrees by the sign of z."""
    a = _angle(y)
    prev_a = _angle(prev_y)
    if z < 0 and prev_z < 0:
        return a - prev_a
    if prev_z < 0:
        return -prev_a - a + (-180 if y < 0 else 180)
    if z < 0:
        return prev_a + a + (180 if y < 0 else -180)
    return prev_a - a


class WristRaise:
    """Watches readings for a raise of the wrist."""

    def __init__(self):
        self._x = [0] * _HISTORY
        self._y = [0] * _HISTORY
        self._z = [0] * _HISTORY
        self._i = 0

    def sample(self, x, y, z):
        """Record a reading and tell whether it completes a raise.

        The axes are InfiniTime's: x along the arm, y across it and z out of
        the back of the watch, each in thousandths of gravity.

        :returns: True if the wrist has just been raised
        """
        i = (self._i + 1) % _HISTORY
        self._i = i
        self._x[i] = x
        self._y[i] = y
        self._z[i] = z

        last = (i - 1) % _HISTORY
        if abs(self._x[i] + self._x[last]) > 2 * _LEVEL:
            return False

        ys = self._y
        zs = self._z
        y_mean = (ys[i] + ys[last]) / 2
        z_mean = (zs[i] + zs[last]) / 2
        y_spread = ((ys[i] - ys[last]) / 2) ** 2
        z_spread = ((zs[i] - zs[last]) / 2) ** 2
        if y_spread > _STEADY or y_mean > _TILTED or \
                (y_mean < _UPRIGHT and z_spread > _STEADY):
            return False

        # The two oldest readings, which are the next two slots round the ring.
        a = (i + 1) % _HISTORY
        b = (i + 2) % _HISTORY
        prev_y = (ys[a] + ys[b]) / 2
        prev_z = (zs[a] + zs[b]) / 2
        return _rolled(y_mean, z_mean, prev_y, prev_z) < -ROLL
