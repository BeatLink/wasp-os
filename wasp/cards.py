# SPDX-License-Identifier: LGPL-3.0-or-later

"""Card layout
~~~~~~~~~~~~~~

Cards are the rounded rectangles that pages are built from: launcher tiles,
list rows, the keypads in the alarm app. They all come from the same few
numbers so that pages drawn by different apps line up with each other.

A card is drawn with :py:meth:`~.Draw565.rounded_rect`, which takes the corner
radius from ``res/ui/corner.svg`` rather than from here.
"""

from micropython import const

# Space left clear around the edge of the screen.
MARGIN = const(4)
# The smallest space allowed between two cards.
GAP = const(3)
# Width and height left for cards once both margins are taken off.
SPAN = const(232)
# Colour of a card: a dark grey that lets white content carry the page.
COLOR = const(0x3186)

# The scroll bar runs down the right hand edge, in the space between the
# cards and the screen. Cards reach x=236, so it sits clear of them.
SCROLLBAR = const(2)
SCROLLBAR_X = const(238)


def size(count):
    """Width or height of each card when count of them share the span.

    Cards are made as large as the span allows while keeping at least GAP
    between them.

    :param count: How many cards share the span
    """
    return (SPAN - (count - 1) * GAP) // count


def edges(sizes, start=MARGIN):
    """Left or top edge of each card in a row or column.

    Whatever space the cards do not use is shared out between them, so a row
    always reaches both margins however its sizes divide up. Pass a size per
    card, which lets a page mix them: the alarm summary is one tall card above
    two short ones.

    Call this once when the module loads rather than on every redraw.

    :param sizes: Width or height of each card, in order
    :param start: Edge the first card starts at
    """
    count = len(sizes)
    slack = SPAN - sum(sizes)
    placed = []
    run = 0
    for i in range(count):
        # Round the shared-out space up, so the last card lands on the margin.
        gap = 0 if i == 0 else -(-slack * i // (count - 1))
        placed.append(start + run + gap)
        run += sizes[i]
    return tuple(placed)


def scrollbar(draw, current, pages, on, off=COLOR):
    """Draw one segment per page down the right hand edge.

    Both colours are greys against the black background, so the bar marks
    where the page sits without competing with the cards.

    :param draw:    Drawable to render with
    :param current: Index of the page being shown
    :param pages:   How many pages there are
    :param on:      Colour of the current page, usually the scroll-indicator theme
    :param off:     Colour of the other pages
    """
    if pages < 2:
        return
    height = 240 // pages
    for i in range(pages):
        draw.fill(on if i == current else off,
                  SCROLLBAR_X, i * height + 2, SCROLLBAR, height - 4)
