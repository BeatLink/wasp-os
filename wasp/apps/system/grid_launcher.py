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

from widgets.page import bounds, scroll_in, draw_indicator, clear_around

# Width, height and position of each of the nine tiles.
_TILE = cards.size(3)
_EDGES = cards.edges((_TILE,) * 3)
# Offset from the tile to the 32x32 icon centred on it.
_INSET = (_TILE - 32) // 2
_TILE_COLOR = cards.COLOR
# Where a sliding page may be cut into bands.
_BANDS = bounds(_EDGES, _TILE)


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
        scroll_in(self.draw_band, _BANDS)
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
        scroll_in(self.draw_band, _BANDS, up=event[0] == wasp.EventType.UP)

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

    def _draw_app(self, app, x, y):
        """Draw one tile with its top left corner at x, y."""
        draw = wasp.watch.drawable
        if not app:
            # An empty slot gets no tile, but it still has to be cleared:
            # only the gaps around the tiles are blanked before this runs,
            # so whatever the last page left here would otherwise show.
            draw.fill(0, x, y, _TILE, _TILE)
            return

        draw.rounded_rect(x, y, _TILE, _TILE, _TILE_COLOR)
        icon = getattr(app, 'ICON', None)
        if not icon:
            icon = icons.app
        if len(icon) == 3:
            draw.rleblit(icon, (x + _INSET, y + _INSET),
                         wasp.system.theme('bright'), _TILE_COLOR)
        else:
            draw.blit(icon, x + _INSET, y + _INSET)

    def draw_band(self, top, y, height):
        """Draw the page rows from top to top+height at screen row y."""
        clear_around(y, height, top, _EDGES, _TILE, _EDGES, _TILE)

        page = self._get_page(self._page)
        for i in range(9):
            row = _EDGES[i // 3]
            if top <= row < top + height:
                self._draw_app(page[i], _EDGES[i % 3], y + row - top)

        draw_indicator(self._page, self._num_pages, top, y, height)

    def _draw(self):
        """Redraw the display from scratch."""
        self.draw_band(0, 0, 240)
