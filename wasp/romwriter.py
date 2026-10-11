# SPDX-License-Identifier: LGPL-3.0-or-later
"""ROMFS writer
~~~~~~~~~~~~~~~

Copies a ROMFS image from the filesystem into the internal flash partition
that is mounted at /rom, then resets the watch so the new image is used.

This module is frozen into the firmware rather than kept in the image, because
code loaded from /rom stops existing the moment the partition is erased. For the
same reason it stops the system tick before erasing and never returns after it.
The reply is a single JSON object tagged ``rom``, like the package manager's.
"""

import json
import machine
import os
import sys
import time
import vfs

HEADER = b'\xd2\xcd\x31'

# The nRF52's flash page, the smallest piece that can be erased.
PAGE = 4096

# Bytes copied at a time.
CHUNK = 256


def _reply(**kwargs):
    kwargs['t'] = 'rom'
    json.dump(kwargs, sys.stdout)
    sys.stdout.write('\r\n')


def install(path='romfs.img'):
    """Write the image at path into the partition and reset; reply with an error instead if it cannot."""
    try:
        size = os.stat(path)[6]
        with open(path, 'rb') as f:
            header = f.read(len(HEADER))
    except OSError:
        _reply(ok=False, err='not found')
        return
    if header != HEADER:
        _reply(ok=False, err='not a ROMFS image')
        return
    if size > len(vfs.rom_ioctl(2, 0)):
        _reply(ok=False, err='too big')
        return

    # Nothing loaded from the old image may run once its flash starts changing.
    import watch
    watch.schedule = watch.nop
    try:
        vfs.umount('/rom')
    except OSError:
        pass

    buf = bytearray(CHUNK)
    view = memoryview(buf)
    vfs.rom_ioctl(3, 0, 0, (size + PAGE - 1) // PAGE * PAGE)
    offset = 0
    with open(path, 'rb') as f:
        while offset < size:
            n = f.readinto(buf)
            if not n:
                break
            vfs.rom_ioctl(4, 0, offset, view[:n])
            offset += n
    vfs.rom_ioctl(5, 0)

    rom = vfs.rom_ioctl(2, 0)
    ok = offset == size
    with open(path, 'rb') as f:
        at = 0
        while ok and at < size:
            n = f.readinto(buf)
            ok = bytes(rom[at:at + n]) == bytes(view[:n])
            at += n

    _reply(ok=ok, size=size)
    if ok:
        os.remove(path)
    # Let the reply reach the radio before the link drops.
    time.sleep_ms(500)
    machine.reset()
