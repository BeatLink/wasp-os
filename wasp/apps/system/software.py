# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson
"""Software
~~~~~~~~~~~

A tool to enable/disable applications.

Applications are listed four to a page, each on a card with its name and a
checkbox. Tap a card to add the application to the launcher or take it away,
and swipe up and down to reach the other pages.

.. figure:: res/screenshots/SoftwareApp.png
    :width: 179

Most applications are disabled by default at boot in order to conserve
RAM (which is in short supply and very useful to anyone wanting to
write an application). This tools allows us to boot and conserve RAM
whilst still allowing users to activate so many awesome applications!
"""

import wasp
import cards
import fonts
import icons
import os
import gc
import appregistry

from widgets.page import clip, scroll_in, draw_indicator, clear_around

from micropython import const

_ROWS = const(4)
# Height, top edge and spacing of each row, as in the list launcher.
_HEIGHT = cards.size(_ROWS)
_TOPS = cards.edges((_HEIGHT,) * _ROWS)
_PITCH = _TOPS[1] - _TOPS[0]
_MARGIN = cards.MARGIN
_WIDTH = cards.SPAN
# Where the name and the checkbox sit within a row.
_NAME_X = const(16)
_NAME_Y = const(16)
_CHECK_X = const(200)
_CHECK_Y = const(11)


class SoftwareApp():
    """Enable and disable applications."""
    NAME = 'Software'
    ICON = icons.software

    def foreground(self):
        """Activate the application."""
        db = []
        for app in appregistry.software_list:
            db.append([app[0], app[1], False])

        # Handle user-loaded applications
        try:
            for app in os.listdir('apps'):
                name = None
                if app.endswith('.py'):
                    name = app[:-3]
                if app.endswith('.mpy'):
                    name = app[:-4]
                if name:
                    # Don't add apps that already exist (prioritize frozen apps)
                    load = True
                    for db_app in db:
                        if db_app[0][db_app[0].rindex('.') + 1:] == name:
                           load = False
                           break
                    if load:
                        db.append(['apps.' + name,
                                   self._snake_case_to_pascal_case(name), False])
        except OSError:
            # apps does not exist...
            pass

        # Get the initial state for the checkboxes
        for entry in db:
            label = entry[1].replace(' ', '')
            for app in wasp.system.launcher_ring:
                if app.NAME.replace(' ', '').startswith(label):
                    entry[2] = True
                    break

        self.check = wasp.widgets.Checkbox(_CHECK_X, 0)
        self.page = 0
        self.db = db

        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.SWIPE_UPDOWN)

    def background(self):
        self.check = None
        del self.check
        self.page = None
        del self.page
        self.db = None
        del self.db

    @property
    def _num_pages(self):
        return (len(self.db) + _ROWS - 1) // _ROWS

    def get_page(self):
        i = self.page * _ROWS
        return self.db[i:i+_ROWS]

    def swipe(self, event):
        """Notify the application of a touchscreen swipe event."""
        page = self.page
        up = event[0] == wasp.EventType.UP
        page += 1 if up else -1
        if page < 0 or page >= self._num_pages:
            wasp.watch.vibrator.pulse()
            return
        self.page = page
        scroll_in(self.draw_rows, up=up)

    def touch(self, event):
        """Notify the application of a touchscreen touch event."""
        row = min(event[2] // _PITCH, _ROWS - 1)
        page = self.get_page()
        if row >= len(page):
            return
        entry = page[row]
        (module, name, state) = entry
        label = name.replace(' ', '')
        entry[2] = not state
        if entry[2]:
            gc.collect()
            # The class is named after the file, which can differ from the listed name (Calc).
            cls = self._snake_case_to_pascal_case(module[module.rindex('.') + 1:])
            wasp.system.register('{}.{}App'.format(module, cls), name=name)
        else:
            for app in wasp.system.launcher_ring:
                if app.NAME.replace(' ', '').startswith(label):
                    wasp.system.launcher_ring.remove(app)
                    break
        tile = _TOPS[row]
        self._draw_entry(entry, tile, tile, _HEIGHT, 0)

    def _draw_entry(self, entry, tile, top, height, sy):
        """Draw the part of one row that falls inside a band.

        :param tile:   Top edge of the row, in page rows
        :param top:    First page row of the band
        :param height: How many rows the band covers
        :param sy:     Add a page row to this to get its screen row
        """
        draw = wasp.watch.drawable
        (first, rows) = clip(top, height, tile, _HEIGHT)
        if not rows:
            return
        y = sy + tile
        if not entry:
            # An empty row still has to be cleared: only the gaps around
            # the rows are blanked before this runs.
            draw.fill(0, _MARGIN, y + first, _WIDTH, rows)
            return

        draw.rounded_rect(_MARGIN, y, _WIDTH, _HEIGHT, cards.COLOR,
                          first=first, rows=rows)
        on = entry[2]
        (nfirst, nrows) = clip(top, height, tile + _NAME_Y,
                               fonts.sans24.height())
        if nrows:
            draw.set_font(fonts.sans24)
            draw.set_color(wasp.system.theme('bright') if on
                           else wasp.system.theme('mid'), cards.COLOR)
            draw.string(entry[1], _NAME_X, y + _NAME_Y,
                        first=nfirst, rows=nrows)
        (cfirst, crows) = clip(top, height, tile + _CHECK_Y,
                               icons.checkbox[2])
        if crows:
            self.check.state = on
            self.check.draw(y + _CHECK_Y, cfirst, crows)

    def draw_rows(self, top, y, height):
        """Draw the page rows from top to top+height at screen row y."""
        clear_around(y, height, top, _TOPS, _HEIGHT, (_MARGIN,), _WIDTH)
        page = self.get_page()
        sy = y - top
        for i in range(_ROWS):
            entry = page[i] if i < len(page) else None
            self._draw_entry(entry, _TOPS[i], top, height, sy)
        draw_indicator(self.page, self._num_pages, top, y, height)

    def _draw(self):
        """Draw the display from scratch."""
        self.draw_rows(0, 0, 240)

    @staticmethod
    def _snake_case_to_pascal_case(s):
        out = ''
        for word in s.split('_'):
            out = out + word[:1].upper() + word[1:]
        return out