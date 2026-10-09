# Scanline rendering for smooth sliding

Sliding a page in with the panel's scroll register is cheap, but making it
look smooth took three attempts. This document records what the cost actually
is, what was tried, and the design that works. Written in September 2026, with
figures measured on the PineTime (`BOARD=pinetime`).

## 1. Verdict

**Draw a few rows, move a few rows, repeat.** The slide paces itself: the
scroll advances exactly as fast as rows can be drawn. There is no frame
budget to miss and no point where the picture stands still.

**Sixteen rows a step.** A real page costs far more per step than the bare
fill model below predicted: each step clips every tile and icon it crosses,
and a step through a row of launcher tiles takes about 35 ms. Measured on a
PineTime, the launcher slides in 815 ms at eight rows a step and 571 ms at
sixteen, so the step is sixteen rows (section 4).

**One row a step is worse, not better.** The fixed cost per step is larger
than the work in a single row, so it doubles the length of the slide and buys
nothing the panel can show. Section 4.

**Staging the whole page in RAM does not fit.** It is short by a factor of
seven. Section 3.

**No display library helps here.** Section 6.

## 2. Where the time goes

The cost of drawing splits cleanly into a fixed part and a per-row part.
Timed on the watch over the REPL, ten `fill` calls of each height:

| Rows | Time per call |
| --- | --- |
| 1 | 1,995 us |
| 2 | 2,883 us |
| 4 | 4,736 us |
| 8 | 8,380 us |
| 16 | 15,475 us |
| 32 | 29,644 us |
| 80 | 72,177 us |

That is a straight line: **1.1 ms of fixed overhead per call, plus 0.89 ms a
row.** A write to the scroll register costs a further **0.26 ms**.

This section was wrong twice, which is worth recording because both mistakes
came from computing the cost rather than measuring it.

**The first draft** computed a band from the width of the bus and called it
38 ms. **The second** measured the draw path, found it eight times slower,
and concluded the cost was in software — and nearly justified rewriting the
rasteriser in C on that basis.

The truth was in a peripheral register: the display bus was running at 1 Mbps
rather than the 8 MHz `watch.py` asks for. See
[`display-performance.md`](display-performance.md). Every "drawing is slow"
figure in those drafts was a bus running at an eighth of its speed.

A third error survived into this document for a while: a table claiming eight
rows cost ~32 ms, left over from the 1 Mbps era, which made smooth scrolling
look arithmetically impossible. At the real rate it is 8.4 ms.

## 3. Why staging the page in RAM does not fit

The tempting fix is to draw the whole incoming page before moving anything:
put what fits in the panel's spare rows and the rest in a buffer.

The panel holds 320 rows and shows 240, so 80 rows are spare. A page is 240
rows. The shortfall is 160 rows:

    160 rows x 240 px x 2 bytes = 76,800 bytes

The nRF52832 has 64 KB of RAM in total, and after wasp-os has started there is
about 10 KB of it free. The buffer alone is larger than the chip. Dropping to
one bit per pixel would fit in 4,800 bytes, but the UI needs black, tile grey
and white at the least, so one bit cannot carry it.

This is not a tuning problem and no amount of freeing up memory reaches it.

## 4. Choosing the step

The first model took the fixed cost of a step from bare fills, 1.36 ms
(drawing plus the scroll write), and 0.89 ms a row. It predicted:

| Rows per step | Step cost | Whole slide | Wasted on overhead |
| --- | --- | --- | --- |
| 1 | 2.25 ms | 540 ms | 60% |
| 4 | 4.9 ms | 295 ms | 28% |
| 8 | 8.5 ms | 254 ms | 16% |
| 16 | 15.6 ms | 234 ms | 9% |
| — | — | 214 ms | 0% (drawing only) |

Stepping a row at a time is the obvious idea and it is the wrong one. It
moves the panel 444 px/s, but the panel refreshes at about 60 Hz, so roughly
seven rows of movement land in every refresh whatever the step size. Nothing
below one refresh is visible, so a one-row step looks identical to an
eight-row step and takes twice as long.

The model was wrong about the fixed cost. A real step also blanks the gaps
beside the tiles, redraws the page indicator, and clips each tile and its
icon, whose decoder starts from the top of the icon. Measured on a PineTime
with the slides themselves:

| Rows per step | Launcher | Alarm list |
| --- | --- | --- |
| 8 | 815 ms | 780 ms |
| 12 | 679 ms | 649 ms |
| 16 | 571 ms | 598 ms |
| 20 | 515 ms | 569 ms |
| 24 | 520 ms | 545 ms |

Eight rows looked smooth but slow. Sixteen is the choice: most of the gain,
with the panel still moving about 25 times a second. Beyond twenty the slide
gets no faster, and the steps only get coarser.

The old design, for comparison, cut the page into four bands at row
boundaries and drew a band in one burst. Each band was about 70 ms during
which the panel could not move, inside a slide padded to roughly 960 ms by
fixed frame pacing. Four visible stops in a slow slide.

## 5. What an application has to provide

`draw_rows(top, y, height)`, drawing page rows `top` to `top + height` with
the first of them at screen row `y`. Any range may be asked for, including
one that cuts a tile or a line of text in half.

That is the part that needed work. Every primitive a page uses now takes
`first` and `rows`:

- `Draw565.fill` already took an arbitrary height.
- `Draw565.rounded_rect` draws only its rows in range, curved or straight.
- `Draw565.rleblit` and `Draw565.blit` count rows as they decode and emit
  only those inside the range.
- `Draw565.string` clips each glyph, and the padding either side of it.
- `widgets.Checkbox.draw` passes a range through to its icon.

Applications work out the range for each element with `widgets.page.clip`,
which intersects an element with the band and returns the element's own first
row and a count.

The 2-bit decoder packs two image rows into one buffer row when it can, which
halves the work but means a buffer row is no longer a row. That optimisation
is now used only when the whole image is being drawn.

`test_clip.py` pins the property that makes all of this safe: drawing a page
in bands must be pixel-identical to drawing it whole, at every step size
including one row, for the grid launcher, the list launcher and the alarm
list.

## 6. Why not a display library

LVGL, and the lighter ones alongside it, all assume the same shape: render
into a buffer, hand the buffer to a flush callback, repeat. None of them drive
a panel's vertical scroll register, because that is a display-specific trick
rather than something a portable toolkit exposes. Using one would mean
fighting it to do the one thing that makes sliding affordable here.

The budget settles it regardless. The PineTime application region leaves about
16 KB free, and a C library plus its MicroPython bindings is well past that.

This is the same conclusion [`vector-graphics-assessment.md`](vector-graphics-assessment.md)
reached about polygon filling: the useful piece is a primitive of a few
hundred lines, not a graphics stack.

## 7. What is not worth doing

**A span rasteriser in C.** An earlier draft proposed one to close an
eight-fold gap between the draw path and the bus. That gap was the bus
running at 1 Mbps. A full screen is 115,200 bytes, which is 115 ms of bus
time at 8 MHz, against 214 ms of measured drawing — under 2x, not 8x. C would
save a fraction of the fixed 1.1 ms per call, and the whole slide only spends
16% of its time there.

**EasyDMA.** Tried and reverted. The port gives SPIM only to the nRF52840,
and enabling it for the nRF52832 corrupts the display: `spi.write` returns
before the transfer has finished, `Draw565` refills its line buffer for the
next row, and chip select is deasserted from Python mid-transfer. The bus is
shared with the external flash, so this is not only a display problem. See
[`display-performance.md`](display-performance.md).

**Concurrency, for smoothness.** Overlapping drawing with transfer gives at
best `max(bus, processor)` rather than their sum: about 115 ms a screen
instead of 214. That is worth having as a speed-up, but it is not what made
the slide stutter. Granularity was.

## 8. What InfiniTime does differently

Worth being clear, because it is the obvious comparison and the answer is not
"they picked a better library".

InfiniTime is C++ and renders into a partial buffer which it flushes over
SPIM, a DMA peripheral. The CPU hands a buffer to the hardware and carries on
rendering the next one while the first goes down the wire, so transfer and
rendering overlap. Rendering in C is also far cheaper than the same work in
MicroPython, and its display work runs as its own FreeRTOS task rather than
blocking everything else.

wasp-os writes through a blocking `spi.write`, so the processor can do
nothing else while a chunk goes out. Keeping each chunk to 8.5 ms is what
makes that acceptable rather than removing it.

Whether InfiniTime uses the scroll register for its own transitions is not
established here, and this document does not assume it either way.

## 9. Still open

1. **Pick the step by measurement on hardware.** Eight comes from the table
   in section 4, which is arithmetic over measured constants rather than a
   measurement of the slide itself.
2. **Non-blocking writes, and asyncio over them**, once the port offers a
   working SPIM on the nRF52832.
3. **Fix the SPI clock in the port** so the `mem32` workaround in
   `watch.py.in` can go.
