# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2021 Daniel Thompson
"""Example of any automatically discovered application.

Any python file (``.py`` or ``.mpy``) discovered in the ``apps/``
directory will be automatically added to the Software application.
"""

import wasp

# 1-bit RLE, 48x48, generated from apps/read_me/icon.png, 95 bytes
icon = (
    48, 48,
    b'\xf7\t\x10\t\x0b\x0f\n\x0f\x05\x14\x06\x14\x01\x16\x04-'
    b'\x02.\x02.\x02.\x02.\x02.\x02.\x02.\x02.'
    b'\x02.\x02.\x02.\x02.\x02.\x02.\x02.\x02.'
    b'\x02.\x02.\x02.\x02.\x02.\x02.\x02.\x02.'
    b'\x02.\x02.\x02.\x02.\x02.\x02.\x02\x1e\t\x07'
    b'\x02\x07\t\x07\x01\x02\x11\x02\x04\x02\x11\x02\xff\x00"'
)

class ReadMeApp():
    NAME = "ReadMe"
    ICON = icon

    def foreground(self):
        draw = wasp.watch.drawable
        draw.fill()
        draw.string('Autoloaded from', 0, 96, width=240)
        draw.string('apps/read_me.py', 0, 96+32, width=240)
