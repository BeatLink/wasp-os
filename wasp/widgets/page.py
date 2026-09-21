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

Only 80 rows can be staged ahead, so a page arrives a band at a time, each
band drawn at the edge it is about to appear from. An application joins in by
offering a ``draw_band(top, y, height)`` method, which draws the rows of the
page from ``top`` with that row placed at screen row ``y``, and a set of
boundaries from :py:func:`bounds` saying where the page may be cut. A band
may be no taller than 80 rows and no boundary may fall inside a row, because
nothing here can draw half of one.
"""

import cards
import time
import wasp

from micropython import const

_HEIGHT = const(240)
_STAGING = const(80)
_GRAM_HEIGHT = const(320)

def bounds(tops, height, screen=_HEIGHT):
    """Work out where a page of rows may be cut into bands.

    Each cut is made immediately below a row, which is the latest a band can
    end without splitting the next one, and so the place that keeps bands as
    tall as they are allowed to be.

    :param tops:    Top edge of each row of the page
    :param height:  Height of a row
    :param screen:  Height of the page
    """
    edges = [0]
    for top in tops:
        edges.append(top + height)
    if edges[-1] < screen:
        edges.append(screen)
    return tuple(edges)


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


def scroll_in(draw_band, edges, up=True, step=4, frame_ms=16):
    """Slide a new page into view.

    The whole screen moves, so this cannot be combined with a fixed area.
    Control does not return until the page has arrived, and the display is
    left scrolled, so a later redraw at ordinary screen coordinates has to
    unscroll first.

    Moving the panel costs almost nothing, so without pacing the screen
    would jump the whole way between bands and wait there while the next one
    is drawn. Each step is held to a frame instead, and time spent drawing is
    taken off the frames that follow rather than added to the total.

    :param draw_band: The page's draw_band(top, y, height)
    :param edges:     Band boundaries, as :py:func:`bounds` returns them
    :param up:        True if the new page comes from below, as a swipe up
                      asks for, False if it comes from above
    :param step:      How many pixels to move per frame
    :param frame_ms:  How long a frame should last
    """
    display = wasp.watch.display
    scroll = display.scroll
    origin = display.scroll_offset
    bands = len(edges) - 1
    scrolled = 0
    due_at = time.ticks_ms()

    def advance(target):
        """Move the panel to target, a step a frame."""
        nonlocal scrolled, due_at
        while scrolled < target:
            scrolled += step
            if scrolled > target:
                scrolled = target
            scroll((origin + (scrolled if up else -scrolled)) % _GRAM_HEIGHT)

            due_at = time.ticks_add(due_at, frame_ms)
            spare = time.ticks_diff(due_at, time.ticks_ms())
            if spare > 0:
                time.sleep_ms(spare)
            elif spare < -frame_ms:
                # A band took long enough that catching up would race the
                # rest of the slide. Start the clock again from here.
                due_at = time.ticks_ms()

    for i in range(bands):
        if up:
            # Bands arrive top first, each one drawn just below the screen.
            top = edges[i]
            height = edges[i+1] - top
            due = top
            y = _HEIGHT
        else:
            # Going the other way the page arrives bottom first, into the
            # rows just above the screen.
            top = edges[bands-1-i]
            height = edges[bands-i] - top
            due = _HEIGHT - top - height
            y = _GRAM_HEIGHT - height

        advance(due)
        draw_band(top, y, height)

    advance(_HEIGHT)


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
