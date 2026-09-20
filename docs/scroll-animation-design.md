# Scroll animation design

Can wasp-os animate scrolling, and if so how? Short answer: not by redrawing, which tops out
around 9 frames per second, but the ST7789V will scroll its own memory for the cost of a
three-byte register write. That makes smooth vertical scrolling cheap. The work is not in the
driver commands, which are small, but in teaching the drawing layer that a logical row and a
physical row are no longer the same thing. Written in September 2026, with figures from the
PineTime build (`BOARD=pinetime`).

## 1. Verdict

**Redraw-driven animation: no.** The SPI bus cannot carry enough frames. Section 2 has the
arithmetic, and it is not close.

**Hardware vertical scrolling: yes, and it is cheap.** The panel has 80 rows of graphics memory
the display never shows. Write the incoming content there, then move the scroll register. The
panel does the shifting and the bus stays almost idle.

**Horizontal transitions: no.** The scroll axis is fixed by the memory layout. Launcher page
changes need something else, and this document does not solve them.

## 2. Why redrawing cannot animate

The SPI clock is 8 MHz ([`watch.py:65`](../wasp/boards/pinetime/watch.py#L65)), so the bus moves
roughly one megabyte per second.

| Transfer | Bytes | Time at 8 MHz |
| --- | --- | --- |
| One 240 px row, 16bpp | 480 | 0.48 ms |
| Full 240x240 screen | 115,200 | 115 ms |

A full screen is 115 ms of solid bus traffic, which is about **8.7 frames per second** before any
drawing cost, any MicroPython overhead, or any of the work that decides what the pixels should be.
Animation wants 30 to 60. The gap is more than an order of magnitude, so this is not a tuning
problem.

That figure also explains why the existing UI redraws whole pages on a transition and accepts the
flicker. There was never a frame budget to spend.

## 3. What the panel already does

The ST7789V holds **240x320** of graphics RAM while the PineTime panel shows **240x240**. Eighty
rows exist in the controller that the user never sees. That memory is how the panel keeps an image
without the MCU refreshing it, and the overscan is addressable like any other part of it.

Two commands drive the scroll, and neither is in
[`st7789.py`](../wasp/drivers/st7789.py) today — the driver defines only `CASET`, `RASET`,
`RAMWR`, `MADCTL` and `COLMOD`:

- **`VSCRDEF` (0x33)** divides the 320 rows into a top fixed area, a scrolling area and a bottom
  fixed area. Set once per screen layout. A pinned status bar or page indicator lives in a fixed
  area and simply does not move.
- **`VSCSAD` (0x37)** sets which GRAM row appears at the top of the scrolling area. This is the
  register that animates.

`VSCSAD` is one command byte plus two data bytes. At 8 MHz that is a few microseconds, against
115 ms to redraw the screen. The scroll itself is effectively free; the only real cost is drawing
the new rows arriving at the edge.

## 4. The cost model

Scrolling by `n` pixels per frame means writing `n` new rows into the region that just left the
display, and one `VSCSAD` write.

| Frame step | New rows | Bytes | SPI time | Share of a 60 fps frame |
| --- | --- | --- | --- | --- |
| 2 px | 2 | 960 | 0.96 ms | 6% |
| 4 px | 4 | 1,920 | 1.9 ms | 12% |
| 8 px | 8 | 3,840 | 3.8 ms | 23% |

A 240 px page transition at 8 px per frame is 30 frames, so half a second at 60 fps, with the bus
busy under a quarter of the time. Compare the same transition today: one 115 ms redraw, visibly a
jump rather than a movement.

The 80 rows of overscan are the lookahead budget. They are comfortable for a list — the launcher
and the alarm list both use a 59 px row pitch, so more than a full row is staged ahead — but they
do not hold a whole second page. A long scroll refills continuously as it moves rather than
staging its destination, which is why the per-frame figures above are the ones that matter.

## 5. What has to change

**The driver gains two commands.** `VSCRDEF` and `VSCSAD` writers next to the existing
`write_cmd` helpers. This part is perhaps thirty lines and carries no risk.

**The drawing layer learns about the offset.** This is the actual work. Today
[`set_window`](../wasp/drivers/st7789.py#L110) writes `x`, `y` straight into `CASET`/`RASET`, and
every drawing operation in `Draw565` assumes logical row `y` is physical row `y`. Once the scroll
register moves, GRAM behaves as a 320-row circular buffer and that assumption breaks: the row an
app wants to draw at `y` may live anywhere, and a window near the wrap point covers two disjoint
physical ranges.

The offset itself belongs in `set_window`, which adds it and takes it modulo 320. Everything
above the driver then keeps working in screen coordinates. The cost is a modulo and a branch on
the hottest path in the graphics stack, skipped entirely while the display is unscrolled.

The split is harder, because `set_window` cannot do it alone: it ends by sending `RAMWR` and the
caller then streams the pixels, so the driver never sees the data it would have to hand to a
second window. The answer is for `set_window` to record where memory runs out and for
`quick_write` to break the stream there, reopen at the start of memory and carry on. That keeps
the split in the driver, where the wrap is, and costs the rest of the graphics stack nothing —
`Draw565` streams through `quick_write` already and needed no changes at all.

The wrap cannot be avoided by timing. A row of an incoming page always lands at the same place in
graphics memory, whenever it is drawn, so exactly one band of every 240 px page crosses row 320
and no choice of step size or draw order moves it. Anything that scrolls real content needs the
split first.

**The event loop needs frames.** Scrolling is currently a discrete redraw triggered by a swipe.
An animation needs to be driven across ticks and to be interruptible, because a second swipe
during a scroll must not queue behind it.

## 6. Limits

- **Vertical only.** With `MADCTL 0x00` ([`st7789.py:60`](../wasp/drivers/st7789.py#L60)) the
  scroll axis follows the memory layout, so left/right page transitions cannot use it. Rotating
  the panel to buy horizontal scrolling would make every existing layout vertical-scrolled
  instead; that is a trade, not a win.
- **80 rows of lookahead**, as covered above.
- **A full redraw has to unscroll first.** Screen coordinates still mean what they say while the
  display is scrolled, but the page that slid in is no longer at row 0 of memory, so redrawing it
  in place would land on top of whatever scrolled off. Switching applications unscrolls; an
  application that slides its own pages has to do the same before redrawing one.
- **Power.** A 500 ms animation keeps the CPU awake for 500 ms. That is real but small next to a
  screen that is already lit and a redraw that already costs 115 ms.

## 7. Recommendations

1. **Add `VSCRDEF` and `VSCSAD` to the driver** and prove them with a throwaway test that scrolls
   a static screen. This validates the panel's behaviour and the fixed-area split before any of
   the harder work starts.
2. **Break the stream in the driver**, not in `Draw565`. `set_window` records where memory runs
   out and `quick_write` reopens at the start of it, so a band may sit anywhere.
3. **Share the page machinery.** `widgets/page.py` holds the band boundaries, the slide and the
   page indicator, and an application joins in by offering `draw_band(top, y, height)`. The grid
   launcher, the list launcher and the alarm list all use it.
4. **Leave left and right alone.** Those transitions are horizontal, this mechanism does not serve
   them, and conflating the two would sink both.
