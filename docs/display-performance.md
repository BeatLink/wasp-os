# Display performance

Everything wasp-os draws goes down one SPI bus to one panel, so what that bus
is doing sets the pace of the whole interface. This records what it was
actually doing, what fixed it, and what was tried and reverted. Written in
September 2026, measured on a PineTime.

## 1. Verdict

**The bus was running at 1 Mbps instead of 8.** `watch.py` asks for 8 MHz and
the request never reached the peripheral. Setting the frequency register
directly made every redraw **4.4 times faster**, and it is the single largest
change in this document by a wide margin.

**EasyDMA was tried and reverted.** It corrupts the display, and because the
same bus carries the filesystem, that is not only a cosmetic risk.

**Concurrency is worth about 1.9x, not more.** The bus is a hard floor at
115 ms a screen. Worth having eventually; not worth having first.

## 2. How to measure this

Over the NUS REPL, with a timer calibrated against a known sleep every time:

```python
import machine, time
t = machine.Timer(id=1, period=8000000)
t.start(); time.sleep_ms(100); print(t.time()); t.stop()   # expect ~100000
```

The calibration is not optional. Two of the conclusions below were wrong
before measuring, and a third was nearly wrong because a result was accepted
without checking it against what the hardware can physically do.

Registers worth reading, with `machine.mem32`:

| Register | Address | Meaning |
| --- | --- | --- |
| SPI0/SPIM0 `ENABLE` | `0x40003500` | 1 is legacy SPI, 7 is SPIM, 0 is disabled |
| SPI0/SPIM0 `FREQUENCY` | `0x40003524` | `0x10000000` is 1 Mbps, `0x80000000` is 8 |
| SPIM1 | `0x40004500` / `0x40004524` | |
| SPIM2 | `0x40023500` / `0x40023524` | |

**Compare every timing against the bus limit before believing it.** At 8 Mbps
a byte takes 1 us. A result faster than that is a bug, not a win.

## 3. The bus was running at an eighth of its speed

[`watch.py`](../wasp/boards/pinetime/watch.py.in) does this:

```python
spi = SPI(0)
spi.init(polarity=1, phase=1, baudrate=8000000)
```

The peripheral ignored it. `FREQUENCY` read `0x10000000`, which is 1 Mbps and
happens to be the default the SPI constructor applies. Measurements agreed to
within a rounding error:

| Operation | Bytes | Measured | At 1 Mbps | At 8 Mbps |
| --- | --- | --- | --- | --- |
| 480 byte `spi.write` | 480 | 3,979 us | 3,840 us | 480 us |
| 240x240 fill | 115,200 | 956,000 us | 921,600 us | 115,200 us |
| 75x75 card | 11,250 | 96,206 us | 90,000 us | 11,250 us |

8.29 us a byte is 1 Mbps to three figures. Writing `0x80000000` to the
frequency register took a full screen to **216 ms**, live, with no rebuild.

Neither `spi.init(baudrate=...)` nor `SPI(0, baudrate=...)` changes it, and
the value read back from the object is a mangled `4286967296`, which is
-8000000 as unsigned. The config struct and the hardware disagree, which
points at `nrfx_spi_init` returning something the caller does not expect so
the reconfiguration is never applied. **The workaround belongs in the port,
not the board file, and the board file should stop doing this once it is.**

## 4. Why the remaining time is not software

With the clock fixed, a full screen is 216 ms against 115 ms of bus time. The
difference is roughly 0.875 us a byte, and it is the legacy SPI peripheral
asking the processor to hand it one byte at a time. `ENABLE` reads `1`, which
is the legacy SPI rather than SPIM.

This matters because an earlier reading of the same numbers concluded the draw
path was software-bound by a factor of eight and proposed rewriting it in C.
It was not software; it was the clock. See
[`scanline-rendering-design.md`](scanline-rendering-design.md) section 4a.

## 5. EasyDMA, and why it is reverted

The nRF52832 has SPIM0/1/2 with EasyDMA. The MicroPython port enables SPIM
only for the nRF52840 and nRF9160, while `NRF51 || NRF52832` gets the legacy
SPI, and `spi.c` already carries the whole `#if NRFX_SPIM_ENABLED` path. So it
is one config change away, and it builds, and it runs, and the display renders
as a cross between two frames.

Measured before the corruption was noticed:

| Operation | Legacy at 1 Mbps | Legacy at 8 Mbps | SPIM |
| --- | --- | --- | --- |
| 240x240 fill | 956,000 us | 216,000 us | 69,810 us |
| 480 byte write | 3,979 us | — | 322 us |

**69,810 us for 115,200 bytes is 13.2 Mbit/s, on a bus whose frequency
register reads 8 Mbps.** That is the tell, and it was visible before anyone
looked at the screen. `spi.write` returns once the transfer has been started,
not finished.

Three things then go wrong, and only the first is about pixels:

1. `Draw565` refills `display.linebuffer` for the next row immediately, so
   EasyDMA reads a buffer that has already been overwritten.
2. Chip select is driven from Python. `quick_end` deasserts it while the
   transfer is still clocking, cutting the row short.
3. **The bus is shared with the external flash.** `watch.py` hands the same
   `SPI(0)` to the display and to `FLASH`, told apart only by chip select. A
   transfer that outlives the Python call can overlap the other device's
   selection, and that device holds `main.py` and the alarm list.

Making this safe needs all three of: the port waiting on `EVENTS_END`, a
second line buffer so the next row is built elsewhere, and chip select moved
into the transfer or explicitly waited on. A mutex does not substitute for any
of them — MicroPython here is single threaded, so nothing is racing another
caller; what races is the hardware against Python having moved on. A lock
becomes necessary if asyncio arrives, and then it has to be held across the
whole `quick_start` to `quick_end` sequence rather than per write.

## 6. What concurrency would be worth

Assume it were all done. Overlapping the drawing with the transfer gives
`max(bus, processor)` instead of their sum:

| | now | with overlap |
| --- | --- | --- |
| Full screen | 216 ms | ~115 ms |
| One band of a slide | ~70 ms | ~37 ms |

**1.9x, with the bus as a floor.** Worth having for every redraw in the
system. But a 37 ms band is still more than two frames at 60 Hz, so the slide
would still visibly stop. Concurrency is not what makes scrolling smooth;
drawing in pieces small enough to fit between frames is, and that works
against a blocking bus today.

## 7. Recommendations

1. **Fix the frequency in the port** and drop the register write from
   `watch.py.in`. It is a workaround sitting in a board file for a bug in a
   driver.
2. **Leave EasyDMA alone** until the line buffer is doubled and chip select is
   no longer driven from Python around live transfers.
3. **Do not rewrite the draw path in C** on the strength of the old numbers.
   The gap they described was the clock.
4. **Measure against the bus limit, every time.** Both mistakes in this
   document would have been caught in one line of arithmetic.
