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
#          1 = keep, 0 = negate      │││
#          X sign ───────────────────┘││
#          Y sign ────────────────────┘│
#          Z sign ─────────────────────┘

_ADDR = const(0x18)
_PWR_CONF = const(0x7c)
_FEATURE_CONFIG = const(0x5e)
_FEATURE_SIZE = const(70)
_AXES_REMAP = const(0x44)

# The chip's own motion features see the PineTime upside down unless x and z are reversed.
_PINETIME_REMAP = b'\x8c\x01'

class BMA421:
    """BMA421 driver

    .. automethod:: __init__
    """
    def __init__(self, i2c, orientation=_DEFAULT_ORIENTATION, remap=_PINETIME_REMAP):
        """Configure the driver.

        :param machine.I2C i2c: I2C bus used to access the sensor.
        :param bytes remap: The two axis remap bytes the chip's motion
                            features use, as laid out in its feature memory.
        """
        self._dev = bma42x.BMA42X(i2c)
        self._i2c = i2c
        self._orientation = orientation
        self._remap = remap

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
        try:
            self._set_remap()
        except OSError:
            # Step counting does not depend on the mounting, so it carries on without it.
            pass

    def _set_remap(self):
        """Tell the chip's motion features how it is mounted.

        The bma42x module has no call for this, so the feature memory is
        read, changed and written back whole, which the chip only accepts
        with advanced power saving off.
        """
        i2c = self._i2c
        power = i2c.readfrom_mem(_ADDR, _PWR_CONF, 1)
        i2c.writeto_mem(_ADDR, _PWR_CONF, b'\x02')
        time.sleep_ms(1)
        config = bytearray(i2c.readfrom_mem(_ADDR, _FEATURE_CONFIG, _FEATURE_SIZE))
        config[_AXES_REMAP:_AXES_REMAP + 2] = self._remap
        i2c.writeto_mem(_ADDR, _FEATURE_CONFIG, config)
        i2c.writeto_mem(_ADDR, _PWR_CONF, power)

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
