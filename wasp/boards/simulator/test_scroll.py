# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2026 Daniel Thompson

"""Hardware scrolling, driven through the emulated panel."""

import pytest
import wasp

from display import spi_st7789_sim as sim

# Each row of memory is filled with its own row number as a colour, so a
# screen row can say which row of memory it is showing.
def colour_of(row):
    return row + 1

def pixel_of(row):
    """The 24 bit pixel the panel stores for that row's colour."""
    rgb = colour_of(row)
    return ((rgb & 0xf800) << 8) + ((rgb & 0x07e0) << 5) + ((rgb & 0x001f) << 3)

@pytest.fixture
def display():
    d = wasp.watch.display

    # Whatever the last test left behind, draw into plain unscrolled memory.
    d.set_scroll_area()
    d.scroll(0)

    for row in range(320):
        d.fill(colour_of(row), 0, row, 240, 1)

    return d

def visible(column=0):
    """Read back the row number showing on each row of the panel."""
    return [int(sim.gram[column][row]) for row in sim.visible_rows()]

def test_unscrolled_shows_the_first_240_rows(display):
    assert visible() == [pixel_of(row) for row in range(240)]

def test_scrolling_moves_the_window_down(display):
    display.scroll(40)

    assert visible() == [pixel_of(row) for row in range(40, 280)]

def test_scrolling_reaches_the_offscreen_rows(display):
    """The 80 rows the panel never shows are what a scroll animates through."""
    display.scroll(80)

    assert visible()[-1] == pixel_of(319)

def test_scrolling_wraps_at_the_end_of_memory(display):
    display.scroll(280)

    assert visible() == [pixel_of(row % 320) for row in range(280, 520)]

def test_a_fixed_area_does_not_move(display):
    display.set_scroll_area(top_fixed=40)
    display.scroll(120)

    rows = visible()
    assert rows[:40] == [pixel_of(row) for row in range(40)]
    assert rows[40:] == [pixel_of(row) for row in range(120, 320)]

def test_drawing_follows_the_scroll(display):
    """A row drawn while scrolled lands where the viewer sees that row."""
    display.scroll(40)
    display.fill(colour_of(999), 0, 0, 240, 1)

    assert visible()[0] == pixel_of(999)
    assert int(sim.gram[0][40]) == pixel_of(999)

def test_drawing_below_the_panel_stages_the_next_rows(display):
    """Rows past the bottom are the memory about to be scrolled into view."""
    display.fill(colour_of(999), 0, 240, 240, 1)
    display.scroll(1)

    assert visible()[-1] == pixel_of(999)

def test_drawing_wraps_past_the_end_of_memory(display):
    display.scroll(280)
    display.fill(colour_of(999), 0, 40, 240, 1)

    assert visible()[40] == pixel_of(999)
    assert int(sim.gram[0][0]) == pixel_of(999)

def test_a_fixed_area_is_drawn_where_it_sits(display):
    display.set_scroll_area(top_fixed=40)
    display.scroll(120)
    display.fill(colour_of(999), 0, 10, 240, 1)

    assert visible()[10] == pixel_of(999)
    assert int(sim.gram[0][10]) == pixel_of(999)

def test_a_draw_across_the_seam_lands_in_both_halves(display):
    """Memory wraps after row 320, so the pixels have to be sent as two."""
    display.scroll(280)
    # Screen rows 30 to 49 are memory rows 310 to 319 and then 0 to 9.
    display.fill(colour_of(999), 0, 30, 240, 20)

    assert visible()[30:50] == [pixel_of(999)] * 20
    assert int(sim.gram[0][310]) == pixel_of(999)
    assert int(sim.gram[0][9]) == pixel_of(999)
    # The rows either side of the draw are untouched.
    assert int(sim.gram[0][309]) == pixel_of(309)
    assert int(sim.gram[0][10]) == pixel_of(10)

def test_the_seam_splits_a_part_width_draw(display):
    """The break falls mid-row when the rectangle is narrower than the panel."""
    display.scroll(280)
    display.fill(colour_of(999), 60, 30, 100, 20)

    assert visible(100)[30:50] == [pixel_of(999)] * 20
    # Columns outside the rectangle keep the rows they had.
    assert visible(59)[30] == pixel_of(310)
    assert visible(160)[49] == pixel_of(9)

def test_the_drawing_layer_splits_at_the_seam_too(display):
    """Draw565 streams its own pixels, so it must break in the same place."""
    display.scroll(280)
    wasp.watch.drawable.fill(colour_of(999), 0, 30, 240, 20)

    assert visible()[30:50] == [pixel_of(999)] * 20
    assert int(sim.gram[0][309]) == pixel_of(309)
    assert int(sim.gram[0][10]) == pixel_of(10)


# Band boundaries

from widgets.page import bounds

def test_bounds_cuts_below_each_row():
    # The alarm list and the list launcher, four rows at a 59 pixel pitch.
    assert bounds((4, 63, 122, 181), 55) == (0, 59, 118, 177, 236, 240)
    # The grid launcher, three rows of tiles at an uneven pitch.
    assert bounds((4, 83, 161), 75) == (0, 79, 158, 236, 240)

def test_bounds_leaves_no_band_taller_than_the_staging_area():
    """Only 80 rows can be staged, so a taller band could not be drawn."""
    for edges in (bounds((4, 63, 122, 181), 55), bounds((4, 83, 161), 75)):
        heights = [edges[i+1] - edges[i] for i in range(len(edges) - 1)]
        assert max(heights) <= 80

def test_bounds_does_not_cut_inside_a_row():
    tops = (4, 63, 122, 181)
    edges = bounds(tops, 55)
    for top in tops:
        for edge in edges:
            assert not top < edge < top + 55
