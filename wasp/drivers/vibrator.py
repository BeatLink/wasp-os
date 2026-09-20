# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Generic PWM capable vibration motor driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import time
from machine import PWM

class Vibrator(object):
    """Vibration motor driver.

    .. automethod:: __init__
    """
    def __init__(self, pin, active_low=False):
        """Specify the pin and configuration used to operate the motor.

        :param machine.Pin pin: The PWM-capable pin used to driver the
                                vibration motor.
        :param bool active_low: Invert the resting state of the motor.
        """
        pin.value(active_low)
        self.pin = pin
        self.freq = 1000
        self.active_low = active_low
        self._pwm = None

    def pulse(self, duty=25, ms=40):
        """Briefly pulse the motor.

        Hold on to the PWM block rather than asking for one each time.
        Deinitialising a block stops it but does not hand it back, so a
        driver that took a fresh one per pulse would run the hardware out
        of them after a few buzzes.

        :param int duty: Duty cycle, in percent.
        :param int ms:   Duration, in milliseconds.
        """
        pwm = self._pwm
        if pwm is None:
            pwm = self._pwm = PWM(self.pin, freq=self.freq, duty=duty)
        else:
            pwm.init(freq=self.freq, duty=duty)
        try:
            time.sleep_ms(ms)
        finally:
            pwm.deinit()
            self.pin.value(self.active_low)
