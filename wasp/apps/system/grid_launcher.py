# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Grid application launcher
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. figure:: res/screenshots/GridLauncherApp.png
    :width: 179

The default launcher. It shows nine application icons per page, each on its
own tile, with a page indicator down the right hand edge.
"""

import wasp
import icons

# Left or top edge of each column and row of tiles.
_EDGES = (4, 83, 161)
# Width and height of a tile.
_TILE = 75
# Offset from the tile to the 48x48 icon centred on it.
_INSET = (_TILE - 48) // 2
# Colour of a tile, a dark grey that lets the white icons carry the page.
_TILE_COLOR = 0x3186

# 1-bit RLE, 240x240, generated from res/ui/backgrounds/3x3.svg, 1361 bytes
background = (
    240, 240,
    b'\xff\x00\xff\x00\xff\x00\xd33\x1b4\x1b3\x1b<\x13<'
    b'\x13<\x14@\x0f@\x0f@\x11B\rB\rB\x0fD'
    b'\x0bD\x0bD\rF\tF\tE\rG\x08F\x08G'
    b'\x0bH\x07H\x07H\nI\x06H\x06I\nI\x05J'
    b'\x05I\nI\x05J\x05I\nI\x05J\x05I\tJ'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\tI\x05J\x05I\nI\x05J\x05I\nI\x06H'
    b'\x06I\nH\x07H\x07H\x0bG\x07H\x07G\x0cG'
    b'\x08F\x08G\rE\tF\tE\x0fC\x0bD\x0bC'
    b'\x11A\rB\rA\x13?\x10>\x10?\x16:\x15:'
    b'\x15:\xff\x00\xff\x00\xff\x00\xff\x00\xcd8\x178\x178'
    b'\x18=\x11>\x11=\x14A\x0e@\x0eA\x11C\x0cB'
    b'\x0cC\x0fE\nD\nE\rF\tF\tF\x0cG'
    b'\x07H\x07G\x0bH\x07H\x07H\nI\x06H\x06I'
    b'\nI\x05J\x05I\nI\x05J\x05I\nI\x05J'
    b'\x05I\tJ\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\tI'
    b'\x05J\x05I\nI\x05J\x05I\nI\x05J\x05I'
    b'\nI\x06H\x06I\nH\x07H\x07H\x0bG\x07H'
    b'\x07G\x0cF\tF\tF\rE\nD\nE\x0fC'
    b'\x0cB\x0cC\x11A\x0e@\x0eA\x14=\x11>\x11='
    b'\x188\x178\x178\xff\x00\xff\x00\xff\x00\xff\x00\xcd:'
    b'\x15:\x15:\x16?\x10>\x10?\x13A\rB\rA'
    b'\x11C\x0bD\x0bC\x0fE\tF\tE\rG\x08F'
    b'\x08G\x0cG\x07H\x07G\x0bH\x07H\x07H\nI'
    b'\x06H\x06I\nI\x05J\x05I\nI\x05J\x05I'
    b'\tJ\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\x08J\x05J\x05J\x08J\x05J\x05J\x08J'
    b'\x05J\x05J\x08J\x05J\x05J\x08J\x05J\x05J'
    b'\x08J\x05J\x05J\x08J\x05J\x05J\x08J\x05J'
    b'\x05J\tI\x05J\x05I\nI\x05J\x05I\nI'
    b'\x05J\x05I\nI\x06H\x06I\nH\x07H\x07H'
    b'\x0bG\x08F\x08G\rE\tF\tE\x0eD\x0bD'
    b'\x0bD\x0fB\rB\rB\x12?\x0f@\x0f?\x15<'
    b'\x13<\x13<\x1b3\x1b4\x1b3\xff\x00\xff\x00\xff\x00'
    b'\xd3'
)

class GridLauncherApp():
    """An application launcher showing a grid of icons."""
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
        x = event[1]
        y = event[2]
        app = page[3 * (y // 80) + (x // 80)]
        if app:
            wasp.system.switch(app)
        else:
            wasp.watch.vibrator.pulse()

    @property
    def _num_pages(self):
        """Work out what the highest possible pages it."""
        num_apps = len(wasp.system.launcher_ring)
        return (num_apps + 8) // 9

    def _get_page(self, i):
        apps = wasp.system.launcher_ring
        page = apps[9*i: 9*(i+1)]
        while len(page) < 9:
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
        tile = _TILE_COLOR

        def draw_app(app, x, y):
            if not app:
                # Blank the tile so empty slots read as empty.
                draw.fill(0, x, y, _TILE, _TILE)
                return
            icon = app.ICON if 'ICON' in dir(app) else icons.app
            if len(icon) == 3:
                draw.rleblit(icon, (x + _INSET, y + _INSET),
                             wasp.system.theme('bright'), tile)
            else:
                draw.blit(icon, x + _INSET, y + _INSET)

        draw.rleblit(background, (0, 0), tile)

        page = self._get_page(self._page)
        for i in range(9):
            draw_app(page[i], _EDGES[i % 3], _EDGES[i // 3])

        self._draw_indicator()
