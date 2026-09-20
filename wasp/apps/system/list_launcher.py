# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""List application launcher
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. figure:: res/screenshots/ListLauncherApp.png
    :width: 179

An alternative to the grid launcher. It lists four applications per page, each
on a full width tile showing its icon and name. Select it from main.py after
the system has started::

    from apps.system.list_launcher import ListLauncherApp
    wasp.system.launcher = ListLauncherApp()
"""

import wasp
import fonts
import icons

from micropython import const

_ROWS = const(4)
# Top edge of each row, and the width and height of a tile.
_PITCH = const(59)
_MARGIN = const(4)
_WIDTH = const(232)
_HEIGHT = const(55)
# Where the 32x32 icon and the name sit within a tile.
_ICON_X = const(12)
_ICON_Y = const(11)
_NAME_X = const(54)
# Colour of a tile, a dark grey that lets the white icons carry the page.
_TILE_COLOR = const(0x3186)

# 1-bit RLE, 240x240, generated from res/ui/backgrounds/4x1.svg, 471 bytes
background = (
    240, 240,
    b'\xff\x00\xff\x00\xff\x00\xd3\xd0\x1b\xda\x14\xde\x11\xe0\x0f\xe2'
    b'\r\xe3\r\xe4\x0b\xe6\n\xe6\n\xe6\n\xe6\n\xe6\t\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\t\xe6\n\xe6'
    b'\n\xe6\n\xe6\n\xe6\x0b\xe4\r\xe2\x0e\xe2\x0f\xe0\x12\xdc'
    b'\x15\xda\x1b\xd0\xff\x00\xff\x00\xff\x00\xe3\xd0\x1b\xda\x14\xde'
    b'\x11\xe0\x0f\xe2\r\xe3\r\xe4\x0b\xe6\n\xe6\n\xe6\n\xe6'
    b'\n\xe6\t\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\t\xe6\n\xe6\n\xe6\n\xe6\n\xe6\x0b\xe4\r\xe2\x0e\xe2'
    b'\x0f\xe0\x12\xdc\x15\xda\x1b\xd0\xff\x00\xff\x00\xff\x00\xe3\xd0'
    b'\x1b\xda\x14\xde\x11\xe0\x0f\xe2\r\xe3\r\xe4\x0b\xe6\n\xe6'
    b'\n\xe6\n\xe6\n\xe6\t\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\t\xe6\n\xe6\n\xe6\n\xe6\n\xe6\x0b\xe4'
    b'\r\xe2\x0e\xe2\x0f\xe0\x12\xdc\x15\xda\x1b\xd0\xff\x00\xff\x00'
    b'\xff\x00\xe3\xd0\x1b\xda\x14\xde\x11\xe0\x0f\xe2\r\xe3\r\xe4'
    b'\x0b\xe6\n\xe6\n\xe6\n\xe6\n\xe6\t\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8\x08\xe8'
    b'\x08\xe8\x08\xe8\x08\xe8\x08\xe8\t\xe6\n\xe6\n\xe6\n\xe6'
    b'\n\xe6\x0b\xe4\r\xe2\x0e\xe2\x0f\xe0\x12\xdc\x15\xda\x1b\xd0'
    b'\xff\x00\xff\x00\xff\x00\xd3'
)

class ListLauncherApp():
    """An application launcher showing a list of names."""
    NAME = 'Launcher'
    ICON = icons.app

    def foreground(self):
        """Activate the application."""
        self._page = 0
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.SWIPE_UPDOWN)

    def swipe(self, event):
        i = self._page
        n = self._num_pages
        if event[0] == wasp.EventType.UP:
            i += 1
            if i >= n:
                i -= 1
                wasp.watch.vibrator.pulse()
                return
        else:
            i -= 1
            if i < 0:
                wasp.system.switch(wasp.system.quick_ring[0])
                return

        self._page = i
        wasp.watch.display.mute(True)
        self._draw()
        wasp.watch.display.mute(False)

    def touch(self, event):
        page = self._get_page(self._page)
        app = page[min(event[2] // _PITCH, _ROWS - 1)]
        if app:
            wasp.system.switch(app)
        else:
            wasp.watch.vibrator.pulse()

    @property
    def _num_pages(self):
        """Work out what the highest possible pages it."""
        num_apps = len(wasp.system.launcher_ring)
        return (num_apps + _ROWS - 1) // _ROWS

    def _get_page(self, i):
        apps = wasp.system.launcher_ring
        page = apps[_ROWS*i: _ROWS*(i+1)]
        while len(page) < _ROWS:
            page.append(None)
        return page

    def _draw_indicator(self):
        """Draw one bar per page in the margin to the right of the tiles."""
        draw = wasp.watch.drawable
        n = self._num_pages
        if n < 2:
            return
        h = 240 // n
        for i in range(n):
            color = wasp.system.theme('bright') if i == self._page \
                    else _TILE_COLOR
            draw.fill(color, 236, i*h + 2, 4, h - 4)

    def _draw(self):
        """Redraw the display from scratch."""
        draw = wasp.watch.drawable
        bright = wasp.system.theme('bright')

        def draw_app(app, y):
            if not app:
                # Blank the tile so empty slots read as empty.
                draw.fill(0, _MARGIN, y, _WIDTH, _HEIGHT)
                return
            icon = app.ICON if 'ICON' in dir(app) else icons.app
            if len(icon) == 3:
                draw.rleblit(icon, (_ICON_X, y + _ICON_Y), bright, _TILE_COLOR)
            else:
                draw.blit(icon, _ICON_X, y + _ICON_Y)
            draw.set_color(bright, _TILE_COLOR)
            draw.string(app.NAME, _NAME_X, y + 16,
                        _MARGIN + _WIDTH - _NAME_X)

        draw.rleblit(background, (0, 0), _TILE_COLOR)
        draw.set_font(fonts.sans24)

        page = self._get_page(self._page)
        for (i, app) in enumerate(page):
            draw_app(app, _MARGIN + i * _PITCH)

        self._draw_indicator()
