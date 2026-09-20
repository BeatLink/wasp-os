# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""List application launcher
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. figure:: res/screenshots/ListLauncherApp.png
    :width: 179

An alternative to the grid launcher that lists application names five to a
page. Select it from main.py after the system has started::

    from apps.system.list_launcher import ListLauncherApp
    wasp.system.launcher = ListLauncherApp()
"""

import wasp
import fonts
import icons

from micropython import const

_ROWS = const(5)
_ROW_HEIGHT = const(48)

class ListLauncherApp():
    """An application launcher showing a list of names."""
    NAME = 'Launcher'
    ICON = icons.app

    def __init__(self):
        self._scroll = wasp.widgets.ScrollIndicator(y=6)

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
        app = page[event[2] // _ROW_HEIGHT]
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

    def _draw(self):
        """Redraw the display from scratch."""
        draw = wasp.watch.drawable
        page_num = self._page
        page = self._get_page(page_num)

        draw.fill()
        draw.set_font(fonts.sans24)
        for i, app in enumerate(page):
            if not app:
                break
            y = i * _ROW_HEIGHT
            draw.set_color(wasp.system.theme('bright'))
            draw.string(app.NAME, 16, y + 12)
            draw.fill(wasp.system.theme('mid'), 0, y + _ROW_HEIGHT - 1, 216, 1)

        scroll = self._scroll
        scroll.up = page_num > 0
        scroll.down = page_num < (self._num_pages-1)
        scroll.draw()
