# Vector graphics assessment

Could an SVG library run on the PineTime, and would drawing from vectors beat the RLE bitmaps
wasp-os uses today? Short answer: a general SVG renderer will not fit, and runtime vector fill
would be slower than the bitmap path for everything that is currently a bitmap. The one place
vectors would win is the rotating elements of analog faces, which today take the slowest drawing
path in the tree. Written in September 2026, with figures from
the PineTime build (`BOARD=pinetime`).

## 1. Verdict

Three separate questions hide inside "should we use SVG", and they have different answers.

**As an authoring format, we already do, and should do more of it.** `tools/gen_app_icons.py`
rasterises SVG to RLE at build time. That is the right pattern and it costs the watch nothing.

**As a runtime format, no.** Parsing XML and rasterising paths on a 64 MHz Cortex-M4 with no
framebuffer would be slower and larger than the bitmaps it replaced. This is not a tuning
problem; it is structural, and section 3 explains why.

**As a runtime primitive for rotating shapes, yes — but write it, do not import it.** A scanline
polygon filler in C, a few hundred lines, would make analog hands both faster and better looking
than `Draw565.line`. Importing a library instead would cost far more flash than the primitive,
for features we do not need.

## 2. What the display path actually looks like

The constraint that decides everything is that **the MCU has no framebuffer of its own**. Be
precise about this, because the panel does have one and it matters elsewhere: the ST7789V carries
240x320 of graphics RAM, which is how it holds the image without the MCU refreshing it. What we
cannot do is treat that memory as a canvas. It sits behind an SPI bus, reads back slowly, and
nothing in the driver can composite into it.

The nRF52832 has 64 KB of RAM. A full 240x240 16bpp canvas is 115 KB. What
[`st7789.py:47`](../wasp/drivers/st7789.py#L47) allocates instead is a single scanline:

```python
self.linebuffer = memoryview(bytearray(2 * width))
```

480 bytes. Every drawing operation in [`draw565.py`](../wasp/draw565.py) is built to stream into
that buffer and flush it to the panel over SPI, strictly top to bottom, never revisiting a row.

Within that shape the bitmap path is close to optimal. `rleblit` and `_rle2bit`
([`draw565.py:189`](../wasp/draw565.py#L189) onward) walk a run-length stream and `memset` each
run into the line buffer:

```python
count = min(sx - bp, rl)
_fill(buf, color, count, bp)
bp += count
rl -= count
if bp >= sx:
    write_data(buf)
    bp = 0
```

The per-pixel cost is a byte store inside a viper-compiled fill. There is no arithmetic per pixel,
no compositing, no source sampling. The work is proportional to the number of *runs*, not the
number of pixels.

The compression is also better than people expect for this kind of art. Card UI used to be stored
as full-screen 240x240 images, one per layout, as 1-bit RLE literals in the source — 1361 bytes
for the launcher's 3x3 grid, 471 for the 4x1 list. An SVG of the same drawing, plus the parser and
rasteriser needed to read it, would not come close.

Those full-screen assets are gone now, which sharpens the point rather than blunting it. The
corners are baked once as four 12x12 bitmaps totalling 74 bytes
([`res/ui/corner.svg`](../res/ui/corner.svg)), and `Draw565.rounded_rect` fills a card's body and
draws those four over it. The bitmap path did not lose; a smaller bitmap won.

## 3. Why a general SVG library does not fit

**The compositing buffer.** nanosvg, ThorVG and comparable renderers take a path set and
composite it into an RGBA buffer they can address randomly. Rasterising a path means computing
edge crossings for a scanline, and anti-aliasing means accumulating coverage — both want to touch
pixels out of order. To fit our 480-byte window we would have to re-run the path pipeline once per
band, so the geometry cost multiplies by the number of bands.

Note the limit of this argument. It says such a renderer needs a working buffer larger than one
scanline; it does not say a UI toolkit cannot run here. LVGL renders in partial bands and flushes
each through a callback, which is very nearly what `Draw565` already does, and InfiniTime runs it
on this same watch. What rules LVGL out for wasp-os is the budget rather than the architecture:
InfiniTime spends its flash on C, while we spend ours on the MicroPython runtime and the
SoftDevice, and the PineTime application region leaves roughly 20 KB free. Do not repeat the
claim that the hardware forbids it.

**SVG is a large format.** It is XML with a transform stack, presentation attributes, `<use>`
references, gradients, clip paths and cubic Béziers. A conforming-enough parser plus a path
rasteriser is tens of kilobytes of flash, and the parse would run in MicroPython. We would spend
more flash on the decoder than we currently spend on all the images together.

**The work per pixel is the wrong shape.** Bitmap blit is O(runs). Polygon fill is O(pixels x
active edges): flatten Béziers to line segments, build an edge table, intersect each scanline,
sort the crossings, fill spans. On a part that wakes for tens of milliseconds a second, that
trade goes the wrong way.

**Storage is not our bottleneck anyway.** The PineTime pairs 512 KB of internal flash with 4 MB of
external SPI flash. We are constrained on RAM and on CPU-awake time, which is precisely where
vectors lose and bitmaps win.

If a runtime vector format is ever genuinely wanted, the candidate is **TinyVG** — a binary vector
format with a decoder around 1 KB, designed for microcontrollers, no XML. It removes the parsing
objection entirely. It does not remove the rasteriser objection, which is the expensive half.

## 4. Where vectors would actually win

`Draw565.line` ([`draw565.py:394`](../wasp/draw565.py#L394)) is the weak point. For any line that
is not exactly horizontal or vertical it walks Bresenham and issues **one SPI window command and
one write per step**:

```python
while True:
    set_window(x0, y0, width, width)
    write_data(px)
```

`polar` is a thin wrapper over it, and that is how analog faces draw their hands. The chrono face
([`faces/chrono/app.py:94`](../faces/chrono/app.py#L94)) draws a minute hand as
`polar(120, 120, mm, 5, 106, 5)` — roughly a hundred steps, each a separate addressing command
plus a 50-byte payload, and the hand is drawn twice per update to erase and redraw. The square
brush also means the hand has hard aliased edges and slightly uneven width as the angle changes.

A filled-polygon primitive fixes both halves at once:

- Take the hand as four corner points, compute the scanline spans, emit each row into the existing
  line buffer as one contiguous write. That is one window command for the whole shape instead of
  one per pixel.
- Accumulate coverage at the span ends for anti-aliasing, blending against the known background
  colour. Hands stop looking jagged at arbitrary angles.

This is the case pre-rendering cannot cover, which is what makes it worth writing. A hand needs
60 or more rotations to look smooth; storing them all as bitmaps is wasteful and still quantises
the angle. Ticks, dial marks and any rotating indicator have the same shape of problem.

Scope it as a C function in the existing native module next to `_fill`, taking a point list and a
colour, rendering top-to-bottom into `display.linebuffer`. It does not need curves, transforms,
gradients or a file format — just convex polygon fill. That is a few hundred lines, and it stays
inside the streaming model rather than fighting it.

## 5. Recommendations

1. **Keep authoring in SVG and rasterise at build time.** `tools/gen_app_icons.py` already does
   this: `bake()` shells out to Inkscape for a PNG, `rle_encode.encode()` turns it into a literal,
   and `replace()` writes it back into the source with a provenance comment naming the SVG. Extend
   that table rather than inventing a second pipeline. Note that `rle_encode.py` reads through PIL
   and so cannot open SVG directly — the Inkscape step is load-bearing.
2. **Do not add a runtime SVG parser or renderer.** Sections 2 and 3 cover the reasoning; revisit
   only if the hardware changes enough to hold a framebuffer.
3. **Consider a C convex-polygon fill for analog faces.** It is the one change here that makes the
   watch both faster and better looking, and it is bounded work. Treat it as a `Draw565` primitive,
   not as a graphics library.
