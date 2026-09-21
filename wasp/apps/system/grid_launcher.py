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
import cards
import icons

# Width, height and position of each of the nine tiles.
_TILE = cards.size(3)
_EDGES = cards.edges((_TILE,) * 3)
# Offset from the tile to the 32x32 icon centred on it.
_INSET = (_TILE - 32) // 2
_TILE_COLOR = cards.COLOR


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
        """Draw the page indicator down the right hand edge."""
        cards.scrollbar(wasp.watch.drawable, self._page, self._num_pages,
                        wasp.system.theme('scroll-indicator'))

    def _draw(self):
        """Redraw the display from scratch."""
        draw = wasp.watch.drawable
        tile = _TILE_COLOR

        def draw_app(app, x, y):
            if not app:
                # An empty slot gets no tile at all.
                return
            draw.rounded_rect(x, y, _TILE, _TILE, tile)
            icon = app.ICON if 'ICON' in dir(app) else icons.app
            if len(icon) == 3:
                draw.rleblit(icon, (x + _INSET, y + _INSET),
                             wasp.system.theme('bright'), tile)
            else:
                draw.blit(icon, x + _INSET, y + _INSET)

        # Clear to black explicitly: fill() would otherwise reuse whatever
        # background colour the last set_color left behind.
        draw.fill(0)

        page = self._get_page(self._page)
        for i in range(9):
            draw_app(page[i], _EDGES[i % 3], _EDGES[i // 3])

        self._draw_indicator()
