# Native compilation assessment

Can wasp-os be compiled to a binary to make it faster? Short answer: the parts that matter
already are, and there is no whole-program compiler that would take it further. This report
records what is already native, what the remaining options buy, and what actually costs time
on the watch. Written in September 2026, with the firmware
figures taken from the PineTime build (`BOARD=pinetime`, SoftDevice S132 6.1.1).

Two runtime versions are in play. Master vendors MicroPython 1.16; the unmerged
`worktree-micropython-upgrade` branch moves to 1.29. Where the two differ, both are given.

## 1. Verdict

MicroPython is not an interpreter bolted onto plain source files. Everything in a wasp-os
build is already compiled ahead of time, and the hot drawing loops are already compiled to
ARM machine code. The realistic gains left are a VM build flag worth roughly a tenth of
bytecode execution time, a handful of extra native functions, and a MicroPython uplift.

Whole-program native compilation is not worth pursuing: it does not fit in the flash budget,
and the paths it would speed up are not the ones users wait for.

## 2. What already compiles to native code

**Every module is frozen bytecode.** `wasp/boards/<board>/manifest.py` freezes the core, the
drivers, the system apps and the selected user apps at `opt=3`, the highest optimisation
level. Nothing is parsed or compiled on the watch, and frozen bytecode executes directly from
flash instead of being copied to RAM.

**The hot paths are ARM machine code.** `@micropython.viper` and `@micropython.native`
compile a function to Thumb instructions with unboxed integers. The build enables the emitter
that makes this possible: on 1.16 through `MICROPY_EMIT_THUMB` in
`ports/nrf/mpconfigdevice_nrf52832.h`, and on 1.29 through the same flag set explicitly in
`ports/nrf/boards/pinetime/mpconfigboard.h`. The second one matters, because 1.29 would
otherwise leave the emitter off: it ties the default to the extra feature level, and the
nRF52832 is configured one level below that. Current usage:

| File | Native or viper functions | What they do |
|---|---|---|
| `wasp/draw565.py` | 7 | bit-blit, fill, glyph drawing, RLE decode, colour lookup |
| `wasp/drivers/st7789.py` | 3 | display window and raw blit |
| `wasp/drivers/nrf_rtc.py` | 3 | tick and uptime arithmetic |
| `wasp/ppg.py` | 1 | heart-rate sample comparison |
| `wasp/drivers/battery.py` | 1 | ADC averaging |
| `wasp/drivers/touch.py` | 1 | K9 touch decode |
| `wasp/wasp.py` | 1 | tick dispatch helper |
| `apps/game_of_life/app.py` | 5 | cell generation |

**One component is already C.** The BMA421 accelerometer is a C module
(`wasp/modules/bma42x-upy`) built in through `USER_C_MODULES`. It is the working template for
moving anything else to C.

**Apps shipped to flash can be precompiled.** `make apps` runs `mpy-cross -mno-unicode
-march=armv7m` over every `apps/NAME/app.py`, and `MICROPY_PERSISTENT_CODE_LOAD` is enabled,
so the watch loads `.mpy` files without compiling them.

## 3. The budget

Flash, from the linker scripts (`nrf52832_512k_64k_bldr78.ld`, `s132_6.1.1.ld`, `memory.ld`):

| Region | Size |
|---|---|
| Total flash before the bootloader | 491,520 B (0x78000) |
| SoftDevice S132 6.1.1 | 155,648 B (0x26000) |
| Filesystem in internal flash | 0 B, the filesystem lives on external SPI NOR |
| Application region | 335,872 B (0x52000) |
| One recovered build's `firmware.bin` | 315,380 B |
| Headroom in that build | 20,492 B, about 6% |

RAM is tighter and matters more:

| Region | Size |
|---|---|
| Device RAM | 65,536 B |
| Reserved by the SoftDevice | 14,784 B |
| PNVRAM, carries the RTC across resets | 32 B |
| Available to the application | 50,720 B |
| Stack | 8,192 B |
| Minimum heap enforced at link time | 32,768 B |

The recovered build measured above came from a customised configuration, so treat the
headroom figure as one data point rather than a constant. The shape of the constraint is the
point: a few tens of kilobytes of flash, and under 50 KB of RAM for everything.

## 4. Options

### 4.1 Compile everything with the native emitter

`mpy-cross -X emit=native`, or the equivalent for frozen modules, compiles whole modules to
machine code instead of bytecode.

- **Buys:** roughly a doubling on loop-heavy pure-Python code. Much less on the UI code that
  dominates this firmware, because native code still uses boxed objects, dictionary lookups for
  attributes and the same object model. Native compilation removes interpreter dispatch, not
  the cost of being Python.
- **Costs:** native code is several times larger than the equivalent bytecode. Against about
  20 KB of headroom, applying it broadly does not fit. Making room means moving frozen apps
  out to the filesystem, which trades flash for RAM, and RAM is the scarcer resource.
- **Verdict:** no. It does not fit, and it targets the wrong bottleneck.

### 4.2 More viper functions

- **Buys:** up to ten times on tight integer and pointer loops.
- **Costs:** viper is a restricted dialect with manual typing and no exceptions, so the code
  becomes harder to read and to change.
- **Verdict:** selectively. The loops that deserve it are already done. Remaining candidates
  are small and should be chosen by measurement, not by guess. Plausible ones: text wrapping
  in `draw565.wrap()`, the launcher redraw, the tick dispatcher.

### 4.3 C modules for the UI core

- **Buys:** the largest single step, but a smaller step than it sounds, because the RLE
  decoder and glyph renderer are already viper and viper is close to C for this kind of code.
- **Costs:** a rebuild and reflash for every change, loss of the Python app model for that
  code, and a much slower development loop.
- **Verdict:** only if profiling shows a specific path dominating and viper has already been
  tried there.

### 4.4 Turn on computed goto in the VM

`MICROPY_OPT_COMPUTED_GOTO` is `0` in `ports/nrf/mpconfigport.h`. It replaces the bytecode
dispatch switch with a jump table.

It is off on both 1.16 and 1.29, and the nRF port does not override the default.

- **Buys:** upstream's own comment puts it at roughly ten percent across all bytecode
  execution, with no source changes.
- **Costs:** upstream estimates about 1 KiB of flash on a Cortex-M4 for the jump table.
- **Verdict:** the cheapest real win available, and the first thing to try. Measure the flash
  delta anyway, since the budget is thin.

### 4.5 Turn on the map lookup cache, after the 1.29 upgrade

This one only exists once the upgrade lands. MicroPython 1.29 has
`MICROPY_OPT_MAP_LOOKUP_CACHE`, which caches map lookups in a small side table. It defaults on
only at the extra feature level, and the nRF52832 sits at the basic level, so it is off and
the nRF port does not override it.

- **Buys:** upstream claims ten to fifteen percent on benchmarks doing a lot of attribute
  access or dictionary lookup, which describes the widget and app code well.
- **Costs:** 128 bytes of RAM for the cache, plus a little flash.
- **Verdict:** try it alongside computed goto. Unlike the bytecode-rewriting cache that older
  MicroPython offered, this one uses a separate table, so it is safe for frozen modules
  executing from read-only flash.

### 4.6 Uplift MicroPython

wasp-os vendors MicroPython 1.16, commit `b349588876` from November 2021. Branch
`13-micropython-1.29` moves it to 1.29 and repoints the vendored submodule at a BeatLink
fork.

- **Buys:** years of VM and compiler improvements, a toolchain that builds on current GCC, and
  the map lookup cache described above.
- **Costs:** the figures in this report were measured on 1.16, so they have to be taken again
  against 1.29 before they can be trusted.
- **Verdict:** done, and it boots on a PineTime. Every other measurement should be taken
  against 1.29, the runtime that is actually going to ship.

## 5. Where the time actually goes

Compilation cannot help with the two largest costs.

**Display transfer.** A full 240x240 frame is 115,200 bytes. Over the 8 MHz SPI link that is
about 115 ms, and it is the same 115 ms whatever language produced the pixels. Full-screen
fills, app switches and screen transitions are transfer-bound. The wins here are algorithmic:
redraw less, which is exactly what the lazy update pattern in the widgets already does, and
what `display.mute()` is for during a switch.

**App switching.** Switching imports a module, constructs the app and usually triggers a
garbage collection. The cost is dominated by import and allocation, not by instruction
dispatch. Precompiled `.mpy` files already remove the compile step for flash-loaded apps.

**Glyph rendering.** Text is drawn glyph by glyph into the display line buffer. This is
already viper. Drawing less text, or caching rendered strings, would beat compiling it
differently.

## 6. Recommended order

1. Land the MicroPython 1.29 upgrade and verify it on hardware. Everything below should be
   measured against the runtime that will ship, not against 1.16.
2. Enable computed goto and the map lookup cache, then measure the flash and RAM cost and the
   benchmark delta. Two build flags, no source changes.
3. Profile before optimising anything else. The Self Test app already has fill, line, string
   and RLE benchmarks that report milliseconds per operation, and the simulator can run them
   without hardware.
4. Move the two or three hottest remaining paths to viper, chosen from that profile.
5. Revisit C modules only if a specific path still dominates.

If real-time responsiveness ever matters more than the Python application model, that is the
point at which InfiniTime's C++ base wins outright, and the honest answer is to port the
feature rather than to keep compiling Python harder.
