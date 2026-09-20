# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Event types and masks
~~~~~~~~~~~~~~~~~~~~~~

Shared by the system manager and every application that handles input.
"""

class EventType():
    """Enumerated interface actions.

    MicroPython does not implement the enum module so EventType
    is simply a regular object which acts as a namespace.
    """
    DOWN = 1
    UP = 2
    LEFT = 3
    RIGHT = 4
    TOUCH = 5

    HOME = 255
    BACK = 254
    NEXT = 253

class EventMask():
    """Enumerated event masks.
    """
    TOUCH = 0x0001
    SWIPE_LEFTRIGHT = 0x0002
    SWIPE_UPDOWN = 0x0004
    BUTTON = 0x0008
    NEXT = 0x0010
