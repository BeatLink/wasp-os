# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2021 Francesco Gazzetta

"""Image gallery
~~~~~~~~~~~~~~~~~~~~~~~~~

An application that shows images stored in the filesystem.

.. figure:: apps/gallery/screenshot.png
    :width: 179

The images have to be uploaded in the "gallery" directory.
The images have to be encoded as BMP RGB565 data in big endian byte order.
To encode them, you can use GIMP (File → Export, select the BMP format,
set "R5 G6 B5" in "Advanced Options"), or ImageMagick:

.. code-block:: sh

    convert -define bmp:subtype=RGB565 my_image.png my_image.bmp

And to upload:

.. code-block:: sh

    ./tools/wasptool --binary --upload my_image.bmp --as gallery/my_image
"""

import wasp
import icons
from apps.system.pager import PagerApp

class GalleryApp():
    NAME = 'Gallery'
    # 1-bit RLE, 32x32, generated from apps/gallery/icon.png, 55 bytes
    ICON = (
        32, 32,
        b'B\x1c\x03\x1e\x01F\x02\x1d\x04\x1b\x06\x1a\x06\x1a\x06\x1b'
        b'\x04)\x02\x1d\x04\x1c\x04\x1b\x06\x19\x08\x17\t\x11\x03\x03'
        b'\n\x10\x03\x02\x0c\x0e\x13\x0c\x14\x0b\x16\t\x18\x08\x18\x08'
        b'\x18D\x01\x1e\x03\x1cB'
    )

    def foreground(self):
        try:
            self.files = wasp.watch.os.listdir("gallery")
        except FileNotFoundError:
            self.files = []
        # In case some images were deleted, we reset the index every time
        self.index = 0
        self._draw()
        wasp.system.request_event(wasp.EventMask.SWIPE_LEFTRIGHT)

    def background(self):
        # We will read the contents of gallery again on foreground(),
        # so let's free some memory
        self.files = []

    def swipe(self, event):
        if event[0] == wasp.EventType.LEFT:
            increment = 1
        elif event[0] == wasp.EventType.RIGHT:
            increment = -1
        else:
            increment = 0
        self.index = (self.index + increment) % len(self.files)
        self._draw()

    def _invalid_file(self, filename):
        draw = wasp.watch.drawable
        draw.string('Invalid BMP file', 0, 10, width=240)
        draw.blit(self.ICON, 104, 104)
        draw.line(72,52, 168,148, 3, 0xf800)

    def _draw(self):
        draw = wasp.watch.drawable
        draw.fill()
        if not self.files:
            draw.string('No files', 0, 60, width=240)
            draw.string('in gallery/', 0, 98, width=240)
        else:
            filename = self.files[self.index]
            # The file name will only show until the image overwrites it,
            # so let's put it at the bottom so the user has a chance to see it
            draw.string(filename[:(draw.wrap(filename, 240)[1])], 0, 200)
            file = open("gallery/{}".format(filename), "rb")
            display = wasp.watch.display

            # check that we are reading a RGB565 BMP
            magic = file.read(2)
            if magic != b'BM': # check BMP magic number
                self._invalid_file(filename)
                return
            file.seek(0x0A)
            data_offset = int.from_bytes(file.read(4), 'little')
            file.seek(0x0E)
            dib_len = int.from_bytes(file.read(4), 'little')
            if dib_len != 124: # check header V5
                self._invalid_file(filename)
                return
            width = int.from_bytes(file.read(4), 'little')
            height = int.from_bytes(file.read(4), 'little')
            # width and height are signed, but only height can actually be negative
            if height >= 2147483648:
                height = 4294967296 - height
                bottom_up = False
            else: bottom_up = True
            if width > 240 or height > 240: # check size <= 240x240
                self._invalid_file(filename)
                return
            file.seek(0x1C)
            bit_count = int.from_bytes(file.read(2), 'little')
            if bit_count != 16: # check 16 bpp
                self._invalid_file(filename)
                return
            compression = int.from_bytes(file.read(4), 'little')
            if compression != 3: # check bitmask mode
                self._invalid_file(filename)
                return
            file.seek(0x36)
            bitmask = file.read(4), file.read(4), file.read(4)
            if bitmask != (b'\x00\xF8\x00\x00', b'\xE0\x07\x00\x00', b'\x1F\x00\x00\x00'): # check bitmask RGB565
                self._invalid_file(filename)
                return

            display.set_window((240 - width) // 2, 0, width, height)

            file.seek(data_offset)

            # We don't have enough memory to load the entire image at once, so
            # we stream it from flash memory to the display
            buf = display.linebuffer[:2*width]
            for y in reversed(range(0, height)):
                if bottom_up: file.seek(data_offset + y * width * 2)
                file.readinto(buf)
                for x in range(0, width):
                    buf[x*2], buf[x*2+1] = buf[x*2+1], buf[x*2]
                display.write_data(buf)

            file.close()
