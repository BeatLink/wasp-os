# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Widget library
~~~~~~~~~~~~~~~~~

The widget library allows common fragments of logic and drawing code to be
shared between applications.

Each widget lives in its own module, and the package imports a module only
when one of its names is first used, so widgets nobody uses stay out of RAM.
"""

# Each public name and the module that defines it.
_NAMES = (
    ('BatteryMeter', 'battery_meter'),
    ('Clock', 'clock'),
    ('NotificationBar', 'notification_bar'),
    ('StatusBar', 'status_bar'),
    ('ScrollIndicator', 'scroll_indicator'),
    ('Button', 'button'),
    ('ToggleButton', 'togglebutton'),
    ('Checkbox', 'checkbox'),
    ('GfxButton', 'gfxbutton'),
    ('Slider', 'slider'),
    ('Spinner', 'spinner'),
    ('Stopwatch', 'stopwatch'),
    ('ConfirmationView', 'confirmation_view'),
)

def __getattr__(name):
    """Import a widget's module the first time its name is used."""
    for (n, m) in _NAMES:
        if n == name:
            value = getattr(__import__('widgets.' + m, None, None, (n,)), n)
            globals()[name] = value
            return value
    raise AttributeError(name)
