# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson
"""The complete set of wasp-os application entry points are documented
below as part of a template application. Note that the template does
not rely on any specific parent class. This is because applications in
wasp-os can rely on *duck typing* making a class hierarchy pointless.

The template draws its page the way every wasp-os app does: grey cards on a
black background, laid out from the numbers in ``cards``. It shows its name on
one card and the last event it received on a second card below it.
"""

import wasp
import cards
import fonts
import icons
from micropython import const

# Two cards stacked down the screen, worked out once when the module loads.
_CARD_H = cards.size(2)
_TOPS = cards.edges((_CARD_H, _CARD_H))
# Inset that keeps padded text clear of the card's rounded corners.
_INSET = const(12)

class TemplateApp():
    """Template application.

    The template application includes every application entry point. It
    is used as a reference guide and can also be used as a template for
    creating new applications.

    .. data:: NAME = 'Template'

       Applications must provide a short ``NAME`` that is used by the
       launcher to describe the application. Names that are longer than
       8 characters are likely to be abridged by the launcher in order
       to fit on the screen.

    .. data:: ICON = RLE2DATA

       Applications can optionally provide an icon for display by the
       launcher. Applications that expect to be installed on the quick
       ring will not be listed by the launcher and need not provide any
       icon. When no icon is provided the system will use a default
       icon.

       The icon is an opportunity to differentiate your application from others
       so supplying an icon is strongly recommended. The icon, when provided,
       must not be larger than 96x64.

    .. data:: PERSIST = False

       An application is dropped from memory when it is left and built
       again when it is next opened. One that hands the scheduler a callback
       of its own, such as a timer that is counting down, sets ``PERSIST`` to
       keep its one instance instead. It may be a property, true only while
       something is running.

    """
    NAME = 'Template'
    ICON = icons.app

    def __init__(self):
        """Initialize the application."""
        pass

    def foreground(self):
        """Activate the application."""
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.SWIPE_UPDOWN |
                                  wasp.EventMask.BUTTON)
        wasp.system.request_tick(1000)

    def background(self):
        """De-activate the application."""
        pass

    def save(self):
        """Return the values to keep while the application is not loaded.

        Called as the application is left and dropped. Keep raw values, such
        as when something started rather than how long it has run, so that
        restore can carry on from them.
        """
        return None

    def restore(self, saved):
        """Take back what save returned, before foreground is called."""
        pass

    def sleep(self):
        """Notify the application the device is about to sleep."""
        return False

    def wake(self):
        """Notify the application the device is waking up."""
        pass

    def preview(self):
        """Provide a preview for the watch face selection.

        preview() must be implemented by watch face applications because it
        is called by the watch face selector. When called the application should
        redraw the screen as through it was the foreground() application. The
        application will not be active after the preview.

        Other applications should not implement this entry point.
        """
        pass

    def press(self, button, state):
        """Notify the application of a button-press event."""
        self._update('Button')

    def swipe(self, event):
        """Notify the application of a touchscreen swipe event."""
        if event[0] == wasp.EventType.UP:
            self._update('Swipe up')
        else:
            self._update('Swipe down')

    def tick(self, ticks):
        """Notify the application that its periodic tick is due."""
        pass

    def touch(self, event):
        """Notify the application of a touchscreen touch event."""
        self._update('({}, {})'.format(event[1], event[2]))

    def _draw(self):
        """Draw the display from scratch."""
        draw = wasp.watch.drawable
        draw.fill(0)
        for y in _TOPS:
            draw.rounded_rect(cards.MARGIN, y, cards.SPAN, _CARD_H, cards.COLOR)
        self._label(self.NAME, _TOPS[0])
        self._update('')

    def _update(self, text):
        """Show text on the lower card."""
        self._label(text, _TOPS[1])

    def _label(self, text, y):
        """Draw text in white, centred on the card whose top edge is at y."""
        draw = wasp.watch.drawable
        # Matching the card colour keeps the glyph background invisible.
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans24)
        # Padding with width= stays inside the straight part of the card.
        draw.string(text, cards.MARGIN + _INSET,
                    y + (_CARD_H - fonts.sans24.height()) // 2,
                    width=cards.SPAN - 2 * _INSET)
