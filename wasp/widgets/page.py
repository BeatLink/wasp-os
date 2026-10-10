# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2026 Daniel Thompson

"""Sliding pages
~~~~~~~~~~~~~~~~

Shared machinery for a screen made of a page of rows, one page at a time,
with a bar per page down the right hand margin.

The panel keeps 320 rows of pixels and shows 240 of them, so 80 rows exist
that nobody ever sees. Drawing the incoming page there and then moving the
panel's scroll register slides it into view for the cost of a three byte
write, where a full redraw costs 115 ms of bus traffic.

Only 80 rows can be staged ahead, so the page is drawn a few rows at a time,
each chunk written to the edge it is about to appear from. An application
joins in by offering a ``draw_rows(top, y, height)`` method, which draws the
rows of the page from ``top`` with that row placed at screen row ``y``.

Any row range may be asked for, including one that cuts a tile or a line of
text in half, so an application works out which part of each element falls
inside the range with :py:func:`clip` and passes that to the drawing
primitives, which all take ``first`` and ``rows``.

The slide paces itself. A chunk is drawn and the panel then moves by exactly
that many rows, so the scroll advances as fast as rows can be drawn and no
faster. Drawing a chunk costs about 1.1 ms of fixed overhead plus 0.89 ms a
row on the PineTime, so eight rows is a step of roughly 8.5 ms: inside a
frame, and small enough that the fixed cost is only a sixth of the work.
"""

import cards
import wasp

from micropython import const

_HEIGHT = const(240)
_STAGING = const(80)
_GRAM_HEIGHT = const(320)

def clip(top, height, offset, extent):
    """Work out which rows of an element fall inside a band.

    The element covers rows ``offset`` to ``offset + extent`` of the page,
    and the band covers ``top`` to ``top + height``.

    :param top:    First page row of the band
    :param height: How many rows the band covers
    :param offset: First page row of the element
    :param extent: How many rows the element covers
    :returns:      The element's own first row to draw and how many, with a
                   count of zero when it misses the band entirely
    """
    first = top - offset
    if first < 0:
        first = 0
    last = top + height - offset
    if last > extent:
        last = extent
    rows = last - first
    return (first, rows) if rows > 0 else (0, 0)


def clear_around(y, height, top, tops, row_height, lefts, col_width):
    """Blank the parts of a band that no tile will cover.

    Clearing the whole band and then drawing tiles over it writes most of the
    band twice, and a band is the one thing a slide cannot do while moving.
    Fill the gaps instead: the strips between rows of tiles, and within a row
    the strips beside the tiles.

    :param y:          Screen row the band is drawn at
    :param height:     How many rows the band covers
    :param top:        First page row of the band
    :param tops:       Top edge of each row of tiles
    :param row_height: Height of a row of tiles
    :param lefts:      Left edge of each column of tiles
    :param col_width:  Width of a column of tiles
    """
    draw = wasp.watch.drawable
    bottom = top + height
    cursor = top

    for row in tops:
        first = max(row, top)
        last = min(row + row_height, bottom)
        if last <= first:
            continue
        # Everything above this row of tiles.
        if cursor < first:
            draw.fill(0, 0, y + cursor - top, 240, first - cursor)
        # Beside the tiles, one strip per gap.
        edge = 0
        for left in lefts:
            if left > edge:
                draw.fill(0, edge, y + first - top, left - edge, last - first)
            edge = left + col_width
        if edge < 240:
            draw.fill(0, edge, y + first - top, 240 - edge, last - first)
        cursor = last

    if cursor < bottom:
        draw.fill(0, 0, y + cursor - top, 240, bottom - cursor)


def scroll_in(draw_rows, up=True, step=8):
    """Slide a new page into view, drawing it as it moves.

    The whole screen moves, so this cannot be combined with a fixed area.
    Control does not return until the page has arrived, and the display is
    left scrolled, so a later redraw at ordinary screen coordinates has to
    unscroll first.

    Each chunk is drawn into rows that are not on screen yet and the panel
    then moves over them, which is what keeps the slide smooth: the work per
    step is the same every step, so there is no point at which the picture
    stands still waiting for a large piece to be drawn.

    :param draw_rows: The page's draw_rows(top, y, height)
    :param up:        True if the new page comes from below, as a swipe up
                      asks for, False if it comes from above
    :param step:      How many rows to draw, and move, per step
    """
    display = wasp.watch.display
    scroll = display.scroll
    origin = display.scroll_offset

    moved = 0
    while moved < _HEIGHT:
        rows = _HEIGHT - moved
        if rows > step:
            rows = step
        if up:
            # The page arrives top first, each chunk written to the rows
            # just below the screen and then moved up over the edge.
            top = moved
            y = _HEIGHT
        else:
            # Going the other way it arrives bottom first, into the rows
            # just above the screen.
            top = _HEIGHT - moved - rows
            y = _GRAM_HEIGHT - rows

        draw_rows(top, y, rows)

        moved += rows
        scroll((origin + (moved if up else -moved)) % _GRAM_HEIGHT)


def draw_indicator(page, count, top=0, y=0, height=_HEIGHT):
    """Draw one bar per page in the margin to the right of the rows.

    The band arguments default to the whole screen, so an ordinary redraw can
    leave them out.

    :param page:    Page currently shown
    :param count:   How many pages there are
    :param top:     First row of the page being drawn
    :param y:       Screen row that `top` is drawn at
    :param height:  How many rows are being drawn
    """
    cards.scrollbar(wasp.watch.drawable, page, count,
                    wasp.system.theme('scroll-indicator'),
                    top=top, y=y, height=height)
