# Scanline rendering for smooth sliding

Sliding a page in with the panel's scroll register works, but it does not look
smooth: it moves, stops, moves, stops. This document says why, rules out the
obvious fix, and proposes the one that fits. Written in September 2026, with
figures from the PineTime build (`BOARD=pinetime`).

## 1. Verdict

**The stops are the drawing.** A page arrives a band at a time and a band is
drawn in one burst. While the CPU pushes those pixels it cannot move the
scroll register, so the slide stands still. Four bands, three visible stops.

**Staging the whole page in RAM does not fit.** It is short by a factor of
seven. Section 3 has the arithmetic.

**Render a row range at a time instead.** Draw a few rows per frame, scroll a
few rows per frame, and never let either get ahead of the other.

**Spreading the work is not enough on its own.** Drawing runs at an eighth of
bus speed, so a slide paced to what the current draw path manages takes about
a second. The drawing has to get faster too, and section 4a says where from.

**No display library helps here.** Section 5.

## 2. Where the time goes

[`widgets/page.py`](../wasp/widgets/page.py) cuts a page at row boundaries,
because nothing can draw half a row of tiles. For the grid launcher that gives
bands of 79, 79, 78 and 4 rows.

This section has been wrong twice, which is worth recording because both
mistakes came from working out the cost rather than measuring it.

**The first draft** computed a band from the width of the bus and called it
38 ms. **The second** measured the draw path, found it eight times slower than
that, and concluded the cost was in software. Both were wrong, and the second
was about to justify writing a rasteriser in C.

The truth was in a peripheral register. The display bus was running at 1 Mbps
rather than the 8 MHz `watch.py` asks for, so every measurement of "drawing"
was really a measurement of a bus running at an eighth of its speed. See
[`display-performance.md`](display-performance.md). With the clock fixed:

| Operation | Bytes | At 1 Mbps | At 8 Mbps |
| --- | --- | --- | --- |
| 240x240 fill | 115,200 | 956,000 us | 216,000 us |
| One band, 79 rows | ~38,000 | ~300 ms | ~70 ms |

A band is now about 70 ms. That is four frames at 60 Hz, spent with the
processor unable to move the scroll register, which is why the slide still
stops four times even though every stop is a quarter of what it was.

Pacing the frames does not help. The scroll register is three bytes and costs
microseconds, so the panel jumps through a band's worth of movement almost
instantly and then waits. Pacing spreads the movement evenly, which is
necessary, but it cannot fill the gap where the processor is busy.

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

## 4. Rendering a row range

Turn the question round. Rather than asking how much of the page can be drawn
ahead, ask how much has to be drawn per frame to keep up with the scroll, and
whether that fits in a frame.

| Rows per frame | Bytes | Bus time | Measured rate applied | Frames for a page |
| --- | --- | --- | --- | --- |
| 4 | 1,920 | 2 ms | ~16 ms | 60 |
| 8 | 3,840 | 4 ms | ~32 ms | 30 |
| 16 | 7,680 | 8 ms | ~64 ms | 15 |

The third column is what the bus would allow. The fourth is what the draw path
actually manages today, taken from the measurements above, and it does not
fit: eight rows a frame already costs twice a 16 ms frame.

So spreading the work is necessary but **not sufficient at the current draw
rate**. Either the slide runs at four rows a frame and takes about a second,
which is too slow to feel good, or the draw path gets faster. Section 4a is
the honest answer to that, and it is why the rasteriser now comes first.

Spreading does still give a natural speed limit worth keeping: the scroll can
move exactly as fast as the rows behind it can be drawn, so a slide that asks
for more takes longer rather than stuttering.

**What an application has to provide.** Today it offers
`draw_band(top, y, height)` and draws whatever tiles fall inside. The band
boundaries come from `bounds()` and may not split a row, which is the
constraint that forces the bursts. A renderer that takes any row range removes
that constraint:

```python
def draw_rows(self, top, y, height):
    """Draw page rows top..top+height at screen row y, for any range."""
```

The difference is that `height` may now be 8 rows in the middle of a tile.
Most of it is easy: `Draw565.fill` already takes an arbitrary height, so the
body of a card slices without trouble. Two things need care.

**Corners.** A card's corners are 12x12 bitmaps blitted whole
([`res/ui/corner.svg`](../res/ui/corner.svg)), so a slice boundary cannot fall
inside one. Either round slice boundaries away from corners, or draw a corner
when its first row is reached and let that frame be slightly heavier.

**Text.** Glyphs are blitted whole for the same reason. Rows carrying text
should be drawn in one piece, which is fine: a line of `sans24` is 24 rows,
about 12 ms, still under a frame at the sizes here.

Neither is a blocker, but both mean slices are "about eight rows" rather than
exactly eight, and the pacing has to cope with a frame that runs long. It
already does: `scroll_in` restarts its clock when a frame overruns rather than
trying to catch up.

## 4a. What does not need doing

An earlier draft of this document proposed a span rasteriser and glyph
rendering in C, to close an eight-fold gap between the draw path and the bus.
**That gap was the bus running at 1 Mbps.** With the clock fixed the draw path
is within about a factor of two of the bus, and what remains is the legacy SPI
peripheral asking the processor for one byte at a time.

So the C work is not worth doing, and neither is EasyDMA, yet:

**A span rasteriser in C** would now save a fraction of the per-call overhead
rather than eight times the whole cost. Measure before believing otherwise.

**EasyDMA** was tried and reverted. The port gives SPIM only to the nRF52840,
and enabling it for the nRF52832 corrupts the display: `spi.write` returns
before the transfer has finished, `Draw565` refills its line buffer for the
next row, and chip select is deasserted from Python mid-transfer. The bus is
shared with the external flash, so this is not only a display problem. See
[`display-performance.md`](display-performance.md).

**Concurrency would not fix the slide anyway.** Overlapping the drawing with
the transfer gives at best `max(bus, processor)` instead of their sum: 115 ms
a screen rather than 216. A band would go from 70 ms to about 37, which is
still more than two frames, and still a stop you can see. Granularity is the
fix; concurrency is a speed-up to want afterwards.

## 5. Why not a display library

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

## 6. What InfiniTime does differently

Worth being clear, because it is the obvious comparison and the answer is not
"they picked a better library".

InfiniTime is C++ and renders into a partial buffer which it flushes over
SPIM, which is a DMA peripheral. The CPU hands a buffer to the hardware and
carries on rendering the next one while the first goes down the wire, so
transfer and rendering overlap. Rendering in C is also far cheaper than the
same work in MicroPython, and its display work runs as its own FreeRTOS task
rather than blocking everything else.

wasp-os writes through a blocking `spi.write`. For the ~300 ms a band takes,
the processor does nothing at all — it cannot move the scroll register, cannot render
ahead, cannot service anything. That single difference explains most of the
gap, and it is not something a different UI library would change.

Whether InfiniTime uses the scroll register for its own transitions is not
established here, and this document does not assume it either way.

## 7. Recommendations

1. **Find the 7 us.** Time a bare `spi.write` against the same bytes through
   `quick_write` and through `fill`. Until that is split between the SPI
   driver, the window handling and the interpreter, every estimate below is a
   guess with a number attached.
2. **Write the span rasteriser in C**, as section 4a describes, and measure
   again. This is where the eight-fold gap is, and nothing else in this
   document matters as much.
3. **Write the row-range renderer** in `widgets/page.py` and move the
   launchers and the alarm list onto it. Keep `bounds()` until the last caller
   is gone.
4. **Pick the rows per frame by measurement, on hardware**, once the
   rasteriser has changed what a frame can afford. Eight is a starting guess,
   not a result.
5. **Then non-blocking writes, and asyncio over them.** In that order, and
   only after the drawing is fast enough for the bus to be the thing in the
   way.
