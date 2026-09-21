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
import cards
import fonts
import icons

from widgets.page import bounds, scroll_in, draw_indicator, clear_around

from micropython import const

_ROWS = const(4)
# Height, top edge and spacing of each row.
_HEIGHT = cards.size(_ROWS)
_TOPS = cards.edges((_HEIGHT,) * _ROWS)
_PITCH = _TOPS[1] - _TOPS[0]
_MARGIN = cards.MARGIN
_WIDTH = cards.SPAN
# Where the 32x32 icon and the name sit within a tile.
_ICON_X = const(12)
_ICON_Y = const(11)
_NAME_X = const(54)
# Colour of a tile, a dark grey that lets the white icons carry the page.
_TILE_COLOR = cards.COLOR
# Where a sliding page may be cut into bands.
_BANDS = bounds(_TOPS, _HEIGHT)


class ListLauncherApp():
    """An application launcher showing a list of names."""
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

    def _draw_app(self, app, y):
        """Draw one tile with its top edge at screen row y."""
        draw = wasp.watch.drawable
        if not app:
            # An empty row still has to be cleared: only the gaps around
            # the tiles are blanked before this runs.
            draw.fill(0, _MARGIN, y, _WIDTH, _HEIGHT)
            return
        bright = wasp.system.theme('bright')

        draw.rounded_rect(_MARGIN, y, _WIDTH, _HEIGHT, _TILE_COLOR)
        icon = getattr(app, 'ICON', None)
        if not icon:
            icon = icons.app
        if len(icon) == 3:
            draw.rleblit(icon, (_ICON_X, y + _ICON_Y), bright, _TILE_COLOR)
        else:
            draw.blit(icon, _ICON_X, y + _ICON_Y)
        draw.set_color(bright, _TILE_COLOR)
        draw.string(app.NAME, _NAME_X, y + 16, _MARGIN + _WIDTH - _NAME_X)

    def draw_band(self, top, y, height):
        """Draw the page rows from top to top+height at screen row y."""
        draw = wasp.watch.drawable
        draw.set_font(fonts.sans24)
        clear_around(y, height, top, _TOPS, _HEIGHT, (_MARGIN,), _WIDTH)

        page = self._get_page(self._page)
        for (i, app) in enumerate(page):
            tile = _MARGIN + i * _PITCH
            if top <= tile < top + height:
                self._draw_app(app, y + tile - top)

        draw_indicator(self._page, self._num_pages, top, y, height)

    def _draw(self):
        """Redraw the display from scratch."""
        self.draw_band(0, 0, 240)
