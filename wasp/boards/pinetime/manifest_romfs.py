# SPDX-License-Identifier: LGPL-3.0-or-later
"""Which modules the PineTime freezes into the firmware and which go in its ROMFS image.

The firmware keeps only what boots the watch, draws on the screen and rewrites
the image, so the watch still reaches its REPL when the image is missing or
broken. Everything else lives in the image, which can be replaced without a
firmware update. Paths are relative to the wasp directory.
"""

import manifest_240x240
import manifest_user_apps

# draw565 imports fonts.sans24, and a package cannot be split between the firmware and the image.
_FONTS = tuple(path for path in manifest_240x240.manifest if path.startswith('fonts/'))

frozen = _FONTS + (
    'boot.py',
    'draw565.py',
    'drivers/bma421.py',
    'drivers/battery.py',
    'drivers/cst816s.py',
    'drivers/hrs3300.py',
    'drivers/nrf_rtc.py',
    'drivers/signal.py',
    'drivers/st7789.py',
    'drivers/vibrator.py',
    'romwriter.py',
)

image = tuple(path for path in manifest_240x240.manifest if path not in _FONTS) + \
    manifest_user_apps.manifest + (
    'companion.py',
    'events.py',
    'gadgetbridge.py',
    'pin_handler.py',
    'pkgmgr.py',
    'ppg.py',
    'shell.py',
    'wasp.py',
)
