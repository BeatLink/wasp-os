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

# 1-bit RLE, 48x48, generated from apps/haiku/icon.png, 131 bytes
icon = (
    48, 48,
    b')\x04&\x0b!\x10\x1d\x13\x1a\x16\x17\x19\x15\x1a\x14\x1c'
    b'\x13\x1d\x11\x1f\x10 \x0f!\r"\x0e"\r#\x0c$'
    b'\x0b$\x0c$\x0b\x10\x01\x14\n\x0f\x04\x12\x0b\x0e\x05\x12'
    b'\x0b\r\x05\x13\n\r\x05\x13\x0b\x0c\x05\x12\r\x0b\x05\x10'
    b'\x10\n\x05\x0e\x13\t\x05\x0e\x14\x08\x05\x15\x0e\x07\x05\x16'
    b'\x0e\x06\x05\x17\x0e\x05\x05\x17\x0f\x04\x05\x17\x10\x03\x05\x15'
    b'\x13\x02\x04\x14\x1b\x12\x1d\x12\x1d\x16\x19\x18\x17\x18\x17\x17'
    b'\x18\x16\x19\x07\x04\t\x1b\x07(\x07(\x07)\x06*\x05'
    b',\x03,'
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
