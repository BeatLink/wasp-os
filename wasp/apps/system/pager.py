# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Pager applications
~~~~~~~~~~~~~~~~~~~~~

The pager is used to present text based information to the user. It is
primarily intended for notifications but is also used to provide debugging
information when applications crash.
"""

import wasp
import cards
import fonts
import icons

import io
import sys

from micropython import const
from widgets.page import clip, draw_indicator, scroll_in

# The text sits on one card, inset from its rounded corners.
_TEXT_X = const(16)
_TEXT_W = const(208)
_TEXT_Y = const(14)
_LINE = const(24)
# Lines shown on a page, and lines moved by a page, keeping one line of overlap.
_LINES = const(9)
_STEP = const(8)

class PagerApp():
    """Show a long text message in a pager."""
    NAME = 'Pager'
    ICON = icons.app

    def __init__(self, msg):
        self._msg = msg

    def foreground(self):
        """Activate the application."""
        wasp.system.request_event(wasp.EventMask.SWIPE_UPDOWN)
        self._redraw()

    def background(self):
        """De-activate the application."""
        self._chunks = None
        self._numpages = None

    def swipe(self, event):
        """Swipe to page up/down."""
        if event[0] == wasp.EventType.UP:
            if self._page >= self._numpages:
                wasp.system.navigate(wasp.EventType.BACK)
                return
            self._page += 1
        else:
            if self._page <= 0:
                wasp.watch.vibrator.pulse()
                return
            self._page -= 1
        scroll_in(self.draw_rows, up=event[0] == wasp.EventType.UP)

    def _redraw(self):
        """Redraw from scratch (jump to the first page)"""
        draw = wasp.watch.drawable
        draw.set_font(fonts.sans24)
        self._page = 0
        self._chunks = draw.wrap(self._msg, _TEXT_W)
        self._numpages = max(0, len(self._chunks) - 2) // _STEP
        self._draw()

    def _draw(self):
        """Draw a page from scratch."""
        display = wasp.watch.display
        display.mute(True)
        # A page that slid in left the display scrolled, so put it back first.
        display.scroll(0)
        self.draw_rows(0, 0, 240)
        display.mute(False)

    def draw_rows(self, top, y, height):
        """Draw the page rows from top to top+height at screen row y."""
        draw = wasp.watch.drawable
        sy = y - top

        # The card fills the screen inside the margins, which are cleared here.
        bottom = top + height
        if top < cards.MARGIN:
            draw.fill(0, 0, y, 240, min(bottom, cards.MARGIN) - top)
        if bottom > cards.MARGIN + cards.SPAN:
            first = max(top, cards.MARGIN + cards.SPAN)
            draw.fill(0, 0, sy + first, 240, bottom - first)
        (first, rows) = clip(top, height, cards.MARGIN, cards.SPAN)
        if rows:
            draw.fill(0, 0, sy + cards.MARGIN + first, cards.MARGIN, rows)
            draw.fill(0, cards.MARGIN + cards.SPAN, sy + cards.MARGIN + first,
                      240 - cards.MARGIN - cards.SPAN, rows)
            draw.rounded_rect(cards.MARGIN, sy + cards.MARGIN, cards.SPAN,
                              cards.SPAN, cards.COLOR, first=first, rows=rows)

        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans24)
        page = self._page
        i = page * _STEP
        chunks = self._chunks[i:i + _LINES + 1]
        for n in range(len(chunks)-1):
            line = _TEXT_Y + _LINE*n
            (first, rows) = clip(top, height, line, fonts.sans24.height())
            if rows:
                sub = self._msg[chunks[n]:chunks[n+1]].rstrip()
                draw.string(sub, _TEXT_X, sy + line, first=first, rows=rows)

        draw_indicator(page, self._numpages + 1, top, y, height)

class NotificationApp(PagerApp):
    NAME = 'Notifications'

    def __init__(self):
        super().__init__('')
        self.confirmation_view = wasp.widgets.ConfirmationView()

    def foreground(self):
        notes = wasp.system.notifications
        note = notes.pop(next(iter(notes)))
        title = note['title'] if 'title' in note else 'Untitled'
        body = note['body'] if 'body' in note else ''
        self._msg = '{}\n\n{}'.format(title, body)

        wasp.system.request_event(wasp.EventMask.TOUCH)
        super().foreground()

    def background(self):
        self.confirmation_view.active = False
        super().background()

    def swipe(self, event):
        if self.confirmation_view.active:
            if event[0] == wasp.EventType.UP:
                self.confirmation_view.active = False
                self._draw()
                return
        else:
            if event[0] == wasp.EventType.DOWN and self._page == 0:
                self.confirmation_view.draw('Clear notifications?')
                return

        super().swipe(event)

    def touch(self, event):
        if self.confirmation_view.touch(event):
            if self.confirmation_view.value:
                wasp.system.notifications = {}
                wasp.system.navigate(wasp.EventType.BACK)
            else:
                self._draw()

class CrashApp():
    """Crash handler application.

    This application is launched automatically whenever another
    application crashes. Our main job it to indicate as loudly as
    possible that the system is no longer running correctly. This
    app deliberately enables inverted video mode in order to deliver
    that message as strongly as possible.
    """
    def __init__(self, exc):
        """Capture the exception information.

        This app does not actually display the exception information
        but we need to capture the exception info before we leave
        the except block.
        """
        msg = io.StringIO()
        sys.print_exception(exc, msg)
        self._msg = msg.getvalue()
        msg.close()

    def foreground(self):
        """Indicate the system has crashed by drawing a couple of bomb icons.

        If you owned an Atari ST back in the mid-eighties then I hope you
        recognise this as a tribute a long forgotten home computer!
        """
        wasp.watch.display.invert(False)
        draw = wasp.watch.drawable
        draw.blit(icons.bomb, 0, 104)
        draw.blit(icons.bomb, 32, 104)

        wasp.system.request_event(wasp.EventMask.SWIPE_UPDOWN |
                                  wasp.EventMask.SWIPE_LEFTRIGHT)

    def background(self):
        """Restore a normal display mode.

        Conceal the display before the transition otherwise the inverted
        bombs get noticed by the user.
        """
        wasp.watch.display.mute(True)
        wasp.watch.display.invert(True)

    def swipe(self, event):
        """Show the exception message in a pager."""
        wasp.system.switch(PagerApp(self._msg))
