# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Haiku viewer
~~~~~~~~~~~~~~~

These three lines poems are fun to write and fit nicely on a tiny screen.

.. figure:: apps/haiku/screenshot.png
    :width: 179

If there is a file called haiku.txt in the flash filesystem then this app
allows it to be displayed three lines at a time using the pager.

This application also (optionally) loads an icon from the filesystem allowing
to be customized to match whether theme your verses are based around.
"""

import wasp
import icons

import io
import sys

from apps.system.pager import PagerApp

# 1-bit RLE, 32x32, generated from apps/haiku/icon.png, 89 bytes
icon = (
    32, 32,
    b'\x19\x05\x17\n\x12\x0e\x10\x10\x0e\x12\x0c\x14\x0b\x14\n\x16'
    b'\t\x17\x08\x18\x08\x17\x08\x18\x07\x0b\x01\r\x07\n\x02\r'
    b'\x07\t\x02\r\x07\t\x02\r\x08\x08\x02\x0b\x0b\x07\x02\n'
    b'\r\x06\x02\x0f\t\x05\x02\x10\t\x04\x02\x10\n\x03\x02\x0f'
    b'\r\x01\x02\r\x12\x0c\x13\x0f\x10\x10\x0f\x0f\x10\x05\x02\x07'
    b'\x11\x05\x1a\x05\x1b\x04\x1c\x03\x1d'
)

class HaikuApp(PagerApp):
    NAME = 'Haiku'
    ICON = icon

    def __init__(self):
        # Throw an exception if there is no poetry for us to read...
        open('haiku.txt').close()

        try:
            with open('haiku.rle', 'rb') as f:
                self.ICON = f.read()
        except:
            # Leave the default app icon if none is present
            pass

        super().__init__('')
        self._counter = -4

    def foreground(self):
        lines = []
        self._counter += 4

        with open('haiku.txt') as f:
            for i in range(self._counter):
                _ = f.readline()

            lines = [ '', ]
            for i in range(3):
                lines.append(f.readline())

            if len(lines[2]) == 0:
                self._counter = 0
                f.seek(0)
                lines = [ '', ]
                for i in range(3):
                    lines.append(f.readline())

        self._msg = '\n'.join(lines)

        super().foreground()
