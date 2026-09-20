# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2021 Daniel Thompson
"""Example of any automatically discovered application.

Any python file (``.py`` or ``.mpy``) discovered in the ``apps/``
directory will be automatically added to the Software application.
"""

import wasp

# 1-bit RLE, 32x32, generated from apps/read_me/icon.png, 61 bytes
icon = (
    32, 32,
    b'd\x07\n\x07\x05\r\x04\r\x01\x0f\x02\x1e\x02\x1e\x02\x1e'
    b'\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e'
    b'\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e\x02\x1e'
    b'\x02\x1e\x02\x1e\x02\x12\n\x02\x02\x02\n\x03\x80'
)

class ReadMeApp():
    NAME = "ReadMe"
    ICON = icon

    def foreground(self):
        draw = wasp.watch.drawable
        draw.fill()
        draw.string('Autoloaded from', 0, 96, width=240)
        draw.string('apps/read_me.py', 0, 96+32, width=240)
