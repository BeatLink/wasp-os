# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Bosch BMA421 accelerometer driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import bma42x
import time

# Sensor orientation definition.
# The 6 most significant bits define the indexes of the x, y, and z values
# in the acceleration tuple returned by the sensor, while the 3 least
# significant bits define their sign (1 = keep original sign, 0 = negate).
#
#         Z index ─────────────────┐
#         Y index ───────────────┐ │
#         X index ─────────────┐ │ │
#                              ├┐├┐├┐
_DEFAULT_ORIENTATION = const(0b010010101)

# Feature interrupts the bma42x module does not export, from BMA42X-Sensor-API/bma42x.h.
_WRIST_WEAR_INT = const(0x08)
_DOUBLE_TAP_INT = const(0x10)

# INT1 pin control and the interrupt latch, from the BMA42x datasheet.
_INT1_IO_CTRL = const(0x53)
_INT_LATCH = const(0x55)
#          1 = keep, 0 = negate      │││
#          X sign ───────────────────┘││
#          Y sign ────────────────────┘│
#          Z sign ─────────────────────┘

class BMA421:
    """BMA421 driver

    .. automethod:: __init__
    """
    def __init__(self, i2c, orientation=_DEFAULT_ORIENTATION, int_pin=None):
        """Configure the driver.

        :param machine.I2C i2c: I2C bus used to access the sensor.
        :param machine.Pin int_pin: The sensor's INT1 line, if the board wires it.
        """
        self._dev = bma42x.BMA42X(i2c)
        self._orientation = orientation
        self._int = int_pin
        self._wake_mask = 0

    def reset(self):
        """Reset and reinitialize the sensor."""
        dev = self._dev

        # Init, reset, wait for reset, enable I2C watchdog
        dev.init()
        dev.set_command_register(0xb6)
        time.sleep(0.05)
        dev.set_reg(bma42x.NV_CONFIG_ADDR, 6);

        # Configure the sensor for basic step counting
        dev.write_config_file()
        dev.set_accel_enable(True)
        dev.set_accel_config(odr=bma42x.OUTPUT_DATA_RATE_100HZ,
                               range=bma42x.ACCEL_RANGE_2G,
                               bandwidth=bma42x.ACCEL_NORMAL_AVG4,
                               perf_mode=bma42x.CIC_AVG_MODE)
        dev.feature_enable(bma42x.STEP_CNTR, True)

    def enable_wake(self, raise_=False, tap=False):
        """Let a wrist raise, a double tap, both or neither raise INT1.

        The interrupt is latched until :py:meth:`woken` reads it, so a short
        pulse cannot fall between two checks. A reset clears all of this, so
        call it again afterwards.
        """
        dev = self._dev
        dev.feature_enable(bma42x.WRIST_WEAR, raise_)
        dev.feature_enable(bma42x.DOUBLE_TAP, tap)
        mask = (_WRIST_WEAR_INT if raise_ else 0) | (_DOUBLE_TAP_INT if tap else 0)
        dev.map_interrupt(bma42x.INTR1_MAP, _WRIST_WEAR_INT | _DOUBLE_TAP_INT, False)
        if mask:
            dev.map_interrupt(bma42x.INTR1_MAP, mask, True)
            # Output enabled, push-pull, active high.
            dev.set_reg(_INT1_IO_CTRL, 0x0a)
            dev.set_reg(_INT_LATCH, 1)
        self._wake_mask = mask

    def woken(self):
        """Tell whether a gesture enabled by :py:meth:`enable_wake` has happened.

        Only the pin is read while nothing has happened; the sensor is asked,
        which also clears the latch, once the pin says there is something.
        """
        if not self._wake_mask or not self._int or not self._int.value():
            return False
        return bool(self._dev.read_int_status() & self._wake_mask)

    @property
    def steps(self):
        """Report the number of steps counted."""
        return self._dev.step_counter_output()

    @steps.setter
    def steps(self, value):
        if value != 0:
            raise ValueError()
        self._dev.reset_step_counter()

    def accel_xyz(self):
        """Return a triple with acceleration values"""
        raw = self._dev.read_accel_xyz()
        x = raw[self._orientation >> 7 & 0b11] * ((self._orientation >> 1 & 0b10) - 1)
        y = raw[self._orientation >> 5 & 0b11] * ((self._orientation      & 0b10) - 1)
        z = raw[self._orientation >> 3 & 0b11] * ((self._orientation << 1 & 0b10) - 1)
        return (x, y, z)
