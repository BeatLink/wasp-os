# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Sitronix ST7789 display driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

    Although the ST7789 supports a variety of communication protocols currently
    this driver only has support for SPI interfaces. However it is structured
    such that other serial protocols can easily be added.
"""

import micropython

from micropython import const
from time import sleep_ms

# register definitions
_SWRESET            = const(0x01)
_SLPIN              = const(0x10)
_SLPOUT             = const(0x11)
_NORON              = const(0x13)
_INVOFF             = const(0x20)
_INVON              = const(0x21)
_DISPOFF            = const(0x28)
_DISPON             = const(0x29)
_CASET              = const(0x2a)
_RASET              = const(0x2b)
_RAMWR              = const(0x2c)
_COLMOD             = const(0x3a)
_MADCTL             = const(0x36)
_VSCRDEF            = const(0x33)
_VSCSAD             = const(0x37)

# The controller always has 320 rows of memory, whatever the panel shows.
_GRAM_HEIGHT        = const(320)

class ST7789(object):
    """Sitronix ST7789 display driver

    .. automethod:: __init__
    """
    def __init__(self, width, height):
        """Configure the size of the display.

        :param int width: Display width, in pixels
        :param int height: Display height in pixels
        """
        self.width = width
        self.height = height
        self.linebuffer = memoryview(bytearray(2 * width))
        self.window = bytearray(4)
        self.scroll_window = bytearray(6)
        self.scroll_addr = bytearray(2)
        self.top_fixed = 0
        self.scrolling = _GRAM_HEIGHT
        self.scroll_offset = 0
        self.seam = 0
        self.seam_rows = 0
        self.seam_x = 0
        self.seam_width = 0
        self.init_display()

    def init_display(self):
        """Reset and initialize the display."""
        self.reset()

        self.write_cmd(_SLPOUT)
        sleep_ms(10)

        for cmd in (
            (_COLMOD,   b'\x05'), # MCU will send 16-bit RGB565
            (_MADCTL,   b'\x00'), # Left to right, top to bottom
            #(_INVOFF,   None), # Results in odd palette
            (_INVON,   None),
            (_NORON,   None),
        ):
            self.write_cmd(cmd[0])
            if cmd[1]:
                self.write_data(cmd[1])
        self.fill(0)
        self.write_cmd(_DISPON)

        # From the point we sent the SLPOUT there must be a
        # 120ms gap before any subsequent SLPIN. In most cases
        # (i.e. when the SPI baud rate is slower than 8M then
        # that time already elapsed as we zeroed the RAM).
        #sleep_ms(125)

    def poweroff(self):
        """Put the display into sleep mode."""
        self.write_cmd(_SLPIN)
        sleep_ms(125)

    def poweron(self):
        """Wake the display and leave sleep mode."""
        self.write_cmd(_SLPOUT)
        sleep_ms(125)

    def invert(self, invert):
        """Invert the display.

        :param bool invert: True to invert the display, False for normal mode.
        """
        if invert:
            self.write_cmd(_INVON)
        else:
            self.write_cmd(_INVOFF)

    def mute(self, mute):
        """Mute the display.

        When muted the display will be entirely black.

        :param bool mute: True to mute the display, False for normal mode.
        """
        if mute:
            self.write_cmd(_DISPOFF)
        else:
            self.write_cmd(_DISPON)

    @micropython.native
    def set_window(self, x, y, width, height):
        """Set the clipping rectangle.

        All writes to the display will be wrapped at the edges of the rectangle.

        Y counts down the panel as the viewer sees it, so a scrolled display
        moves the rectangle to wherever that row currently lives in memory.
        Rows past the bottom of the panel address the memory waiting to be
        scrolled into view. A rectangle that runs off the end of that memory
        wraps onto the rows at the start of it, which are not next to each
        other, so the driver breaks the pixels into two sends.

        :param x:  X coordinate of the left-most pixels of the rectangle
        :param y:  Y coordinate of the top-most pixels of the rectangle
        :param w:  Width of the rectangle, defaults to None (which means select
                   the right-most pixel of the display)
        :param h:  Height of the rectangle, defaults to None (which means select
                   the bottom-most pixel of the display)
        """
        offset = self.scroll_offset
        if offset:
            top = self.top_fixed
            if y >= top:
                y = top + (y - top + offset) % self.scrolling

        bottom = y + height
        if bottom > _GRAM_HEIGHT:
            # The rectangle runs off the end of display memory. Send what fits
            # and remember where to break the stream for the rest.
            self.seam = (_GRAM_HEIGHT - y) * width * 2
            self.seam_rows = bottom - _GRAM_HEIGHT
            self.seam_x = x
            self.seam_width = width
            bottom = _GRAM_HEIGHT
        else:
            self.seam = 0

        self.emit_window(x, x + width - 1, y, bottom - 1)

    @micropython.native
    def emit_window(self, x, xp, y, yp):
        """Send a rectangle of display memory and open it for writing.

        Coordinates are rows and columns of memory, with no scrolling applied.
        """
        write_cmd = self.write_cmd
        window = self.window
        write_data = self.write_data

        write_cmd(_CASET)
        window[0] = x >> 8
        window[1] = x & 0xff
        window[2] = xp >> 8
        window[3] = xp & 0xff
        write_data(window)

        write_cmd(_RASET)
        window[0] = y >> 8
        window[1] = y & 0xff
        window[2] = yp >> 8
        window[3] = yp & 0xff
        write_data(window)

        write_cmd(_RAMWR)

    def set_scroll_area(self, top_fixed=0, bottom_fixed=0):
        """Split the display memory into fixed and scrolling areas.

        The fixed areas stay put while :py:meth:`scroll` moves everything
        between them. Rows are counted in display memory, of which there are
        320 whatever the panel shows.

        :param top_fixed:     Height of the fixed area at the top, in rows
        :param bottom_fixed:  Height of the fixed area at the bottom, in rows
        """
        scrolling = _GRAM_HEIGHT - top_fixed - bottom_fixed
        window = self.scroll_window

        self.top_fixed = top_fixed
        self.scrolling = scrolling
        self.scroll_offset = 0

        window[0] = top_fixed >> 8
        window[1] = top_fixed & 0xff
        window[2] = scrolling >> 8
        window[3] = scrolling & 0xff
        window[4] = bottom_fixed >> 8
        window[5] = bottom_fixed & 0xff

        self.write_cmd(_VSCRDEF)
        self.write_data(window)

    @micropython.native
    def scroll(self, y):
        """Choose which row of display memory appears first in the scrolling area.

        This is the whole of an animation frame: the panel does the shifting,
        so the only pixels that have to be sent are the ones arriving at the
        edge.

        :param y:  Row of display memory to show at the top of the scrolling
                   area, which must lie inside that area
        """
        addr = self.scroll_addr

        self.scroll_offset = y - self.top_fixed

        addr[0] = y >> 8
        addr[1] = y & 0xff

        self.write_cmd(_VSCSAD)
        self.write_data(addr)

    def rawblit(self, buf, x, y, width, height):
        """Blit raw pixels to the display.

        :param buf: Pixel buffer
        :param x:  X coordinate of the left-most pixels of the rectangle
        :param y:  Y coordinate of the top-most pixels of the rectangle
        :param w:  Width of the rectangle, defaults to None (which means select
                   the right-most pixel of the display)
        :param h:  Height of the rectangle, defaults to None (which means select
                   the bottom-most pixel of the display)
        """
        self.set_window(x, y, width, height)
        self.quick_start()
        self.quick_write(buf)
        self.quick_end()

    def fill(self, bg, x=0, y=0, w=None, h=None):
        """Draw a solid colour rectangle.

        If no arguments a provided the whole display will be filled with
        the background colour (typically black).

        :param bg: Background colour (in RGB565 format)
        :param x:  X coordinate of the left-most pixels of the rectangle
        :param y:  Y coordinate of the top-most pixels of the rectangle
        :param w:  Width of the rectangle, defaults to None (which means select
                   the right-most pixel of the display)
        :param h:  Height of the rectangle, defaults to None (which means select
                   the bottom-most pixel of the display)
        """
        if not w:
            w = self.width - x
        if not h:
            h = self.height - y
        self.set_window(x, y, w, h)

        # Populate the line buffer
        buf = self.linebuffer[0:2*w]
        for xi in range(0, 2*w, 2):
            buf[xi] = bg >> 8
            buf[xi+1] = bg & 0xff

        # Do the fill
        self.quick_start()
        for yi in range(h):
            self.quick_write(buf)
        self.quick_end()

class ST7789_SPI(ST7789):
    def __init__(self, width, height, spi, cs, dc, res=None, rate=8000000):
        """Configure the display.

        :param int width: Width of the display
        :param int height: Height of the display
        :param machine.SPI spi: SPI controller
        :param machine.Pin cs: Pin (or signal) to use as the chip select
        :param machine.Pin dc: Pin (or signal) to use to switch between data
                               and command mode.
        :param machine.Pin res: Pin (or signal) to, optionally, use to reset
                                the display.
        :param int rate: SPI bus frequency
        """
        self._write = spi.write
        self.cs = cs.value
        self.dc = dc.value
        self.res = res
        self.rate = rate
        self.cmd = bytearray(1)

        #spi.init(baudrate=self.rate, polarity=1, phase=1)
        cs.init(cs.OUT, value=1)
        dc.init(dc.OUT, value=0)
        if res:
            res.init(res.OUT, value=0)

        super().__init__(width, height)

    def reset(self):
        """Reset the display.

        Uses the hardware reset pin if there is one, otherwise it will issue
        a software reset command.
        """
        if self.res:
            self.res(0)
            sleep_ms(10)
            self.res(1)
        else:
            self.write_cmd(_SWRESET)
        sleep_ms(125)

    @micropython.native
    def write_cmd(self, cmd):
        """Send a command opcode to the display.

        :param sequence cmd: Command, will be automatically converted so it can
                             be issued to the SPI bus.
        """
        dc = self.dc
        cs = self.cs
        c = self.cmd

        dc(0)
        cs(0)
        c[0] = cmd
        self._write(c)
        cs(1)
        dc(1)

    @micropython.native
    def write_data(self, buf):
        """Send data to the display.

        :param bytearray buf: Data, must be in a form that can be directly
                              consumed by the SPI bus.
        """
        cs = self.cs
        cs(0)
        self._write(buf)
        cs(1)

    @micropython.native
    def quick_write(self, buf):
        """Send pixels to the display as part of an optimized write sequence.

        Where the open rectangle runs off the end of display memory the
        pixels are cut in two and the remainder is sent to the rows it wraps
        onto.

        :param bytes-like buf: Data, must be in a form that can be directly
                               consumed by the SPI bus.
        """
        seam = self.seam
        if not seam:
            self._write(buf)
            return

        n = len(buf)
        if n < seam:
            self.seam = seam - n
            self._write(buf)
            return

        mv = memoryview(buf)
        self.seam = 0
        if seam:
            self._write(mv[0:seam])

        # Reopen at the start of memory, then carry on where we left off.
        self.emit_window(self.seam_x, self.seam_x + self.seam_width - 1,
                         0, self.seam_rows - 1)
        self.cs(0)

        if n > seam:
            self._write(mv[seam:])

    def quick_start(self):
        """Prepare for an optimized write sequence.

        Optimized write sequences allow applications to produce data in chunks
        without having any overhead managing the chip select.
        """
        self.cs(0)

    def quick_end(self):
        """Complete an optimized write sequence."""
        self.cs(1)
