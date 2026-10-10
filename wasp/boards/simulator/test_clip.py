# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2026 Daniel Thompson

"""Row clipping: drawing in bands must match drawing all at once.

A sliding page is drawn a few rows at a time, so every primitive it uses has
to be splittable at any row without the result changing.
"""

import pytest
import fonts
import wasp

from display import spi_st7789_sim as sim

@pytest.fixture
def draw():
    d = wasp.watch.display
    d.set_scroll_area()
    d.scroll(0)
    return wasp.watch.drawable

def snapshot(x, y, w, h):
    return [[int(sim.gram[col][row]) for row in range(y, y + h)]
            for col in range(x, x + w)]

def in_bands(step, height, paint):
    """Call paint(first, rows) over the whole height, step rows at a time."""
    first = 0
    while first < height:
        rows = min(step, height - first)
        paint(first, rows)
        first += rows

@pytest.mark.parametrize("step", (1, 3, 8, 16))
def test_a_banded_rounded_rect_matches_a_whole_one(draw, step):
    draw.fill(0)
    draw.rounded_rect(10, 20, 100, 80, 0x3186)
    whole = snapshot(0, 0, 240, 240)

    draw.fill(0)
    in_bands(step, 80,
             lambda f, r: draw.rounded_rect(10, 20, 100, 80, 0x3186,
                                            first=f, rows=r))

    assert snapshot(0, 0, 240, 240) == whole

def test_rounded_rect_corners_are_quarter_circles(draw):
    """Each corner is a 12px quarter circle, matched pixel for pixel."""
    draw.fill(0)
    draw.rounded_rect(10, 20, 100, 80, 0x3186)
    card = snapshot(10, 20, 100, 80)
    grey = card[50][40]

    bare = (9, 6, 5, 4, 3, 2, 1, 1, 1, 0, 0, 0)
    for e, k in enumerate(bare):
        for row in (e, 79 - e):
            line = [card[col][row] for col in range(100)]
            assert line[:k] == [0] * k
            assert line[100 - k:] == [0] * k
            assert line[k:100 - k] == [grey] * (100 - 2 * k)

@pytest.mark.parametrize("step", (1, 5, 8))
def test_a_banded_string_matches_a_whole_one(draw, step):
    draw.set_font(fonts.sans24)
    draw.set_color(0xffff, 0)

    draw.fill(0)
    draw.string('Wasp 123', 10, 30, width=200)
    whole = snapshot(0, 0, 240, 240)

    draw.fill(0)
    in_bands(step, fonts.sans24.height(),
             lambda f, r: draw.string('Wasp 123', 10, 30, width=200,
                                      first=f, rows=r))

    assert snapshot(0, 0, 240, 240) == whole

def test_a_zero_height_band_draws_nothing(draw):
    draw.fill(0)
    blank = snapshot(0, 0, 240, 240)

    draw.rounded_rect(10, 20, 100, 80, 0x3186, first=0, rows=0)
    draw.string('Wasp', 10, 30, width=200, first=0, rows=0)

    assert snapshot(0, 0, 240, 240) == blank


# A whole page, drawn by the applications that slide

def _page_apps():
    from apps.system.grid_launcher import GridLauncherApp
    from apps.system.list_launcher import ListLauncherApp
    from apps.user.alarm import AlarmApp

    grid = GridLauncherApp()
    grid._page = 0
    listed = ListLauncherApp()
    listed._page = 0
    alarm = AlarmApp()
    # foreground() builds the row checkboxes, and also draws, so the test
    # clears the screen again before it measures anything.
    alarm.foreground()
    alarm.alarms = [[6 + i, 0, 0x80] for i in range(6)]
    alarm.num_alarms = 6
    alarm.scroll = 0
    alarm.page = -1
    return {'grid': grid, 'list': listed, 'alarm': alarm}

@pytest.mark.parametrize("name", ('grid', 'list', 'alarm'))
@pytest.mark.parametrize("step", (8, 16))
def test_a_banded_page_matches_a_whole_one(draw, name, step):
    app = _page_apps()[name]

    draw.fill(0)
    app.draw_rows(0, 0, 240)
    whole = snapshot(0, 0, 240, 240)

    draw.fill(0)
    top = 0
    while top < 240:
        rows = min(step, 240 - top)
        app.draw_rows(top, top, rows)
        top += rows

    assert snapshot(0, 0, 240, 240) == whole
