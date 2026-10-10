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

from widgets.page import clip, scroll_in, draw_indicator, clear_around

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
        self._subscribe()

    def sliding(self):
        """Activate the application as it slides up into view."""
        self._page = 0
        scroll_in(self.draw_rows)
        self._subscribe()

    def _subscribe(self):
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
        scroll_in(self.draw_rows, up=event[0] == wasp.EventType.UP)

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

    def _draw_app(self, app, x, tile, top, height, sy):
        """Draw the part of one tile that falls inside a band.

        :param x:      Left edge of the tile
        :param tile:   Top edge of the tile, in page rows
        :param top:    First page row of the band
        :param height: How many rows the band covers
        :param sy:     Add a page row to this to get its screen row
        """
        draw = wasp.watch.drawable
        (first, rows) = clip(top, height, tile, _TILE)
        if not rows:
            return
        y = sy + tile

        if not app:
            # An empty slot gets no tile, but it still has to be cleared:
            # only the gaps around the tiles are blanked before this runs,
            # so whatever the last page left here would otherwise show.
            draw.fill(0, x, y + first, _TILE, rows)
            return

        draw.rounded_rect(x, y, _TILE, _TILE, _TILE_COLOR,
                          first=first, rows=rows)
        icon = getattr(app, 'ICON', None)
        if not icon:
            icon = icons.app
        (ifirst, irows) = clip(top, height, tile + _INSET,
                               icon[1] if len(icon) == 3 else icon[2])
        if irows:
            if len(icon) == 3:
                draw.rleblit(icon, (x + _INSET, y + _INSET + ifirst),
                             wasp.system.theme('bright'), _TILE_COLOR, ifirst, irows)
            else:
                draw.blit(icon, x + _INSET, y + _INSET + ifirst,
                          wasp.system.theme('bright'), first=ifirst, rows=irows)

    def draw_rows(self, top, y, height):
        """Draw the page rows from top to top+height at screen row y."""
        clear_around(y, height, top, _EDGES, _TILE, _EDGES, _TILE)

        page = self._get_page(self._page)
        sy = y - top
        for i in range(9):
            self._draw_app(page[i], _EDGES[i % 3], _EDGES[i // 3],
                           top, height, sy)

        draw_indicator(self._page, self._num_pages, top, y, height)

    def _draw(self):
        """Redraw the display from scratch."""
        self.draw_rows(0, 0, 240)
