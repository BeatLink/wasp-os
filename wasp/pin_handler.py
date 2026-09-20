# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Pin event generator
~~~~~~~~~~~~~~~~~~~~
"""

class PinHandler():
    """Pin (and Signal) event generator.

    TODO: Currently this driver doesn't actually implement any
    debounce but it will!
    """

    def __init__(self, pin):
        """
        :param Pin pin: The pin to generate events from
        """
        self._pin = pin
        self._value = pin.value()

    def get_event(self):
        """Receive a pin change event.

        Check for a pending pin change event and, if an event is pending,
        return it.

        :return: boolean of the pin state if an event is received, None
                 otherwise.
        """
        new_value = self._pin.value()
        if self._value == new_value:
            return None

        self._value = new_value
        return new_value
