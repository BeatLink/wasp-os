# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

import os, sys

sys.path.append(os.path.dirname(os.getcwd()))
sys.path.append(os.getcwd())
import manifest_romfs

freeze('.', 'watch.py', opt=3)
# The rest of wasp-os goes in the ROMFS image; see manifest_romfs.py.
freeze('../..', manifest_romfs.frozen, opt=3)
freeze('../../drivers/flash',
    (
        'bdevice.py',
        'flash/flash_spi.py'
    ), opt=3
)
