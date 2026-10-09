# Firmware trim review

A review of where MicroPython and wasp-os spend the PineTime's flash, heap
and CPU, what was changed, and what was left alone. Written in October 2026.
Every figure was measured on a PineTime unless it says otherwise.

## 1. Verdict

**The heap after boot went from 8,352 bytes to 19,152.** Over a REPL session
the free heap went from 4,608 bytes to 17,488. Half of the gain is RAM the
SoftDevice had reserved but never used. The other half is Python objects
that no longer load at boot, plus REPL history that no longer piles up.

**The firmware is 28.8 KB smaller** (`.text` 327,368 → 298,604 bytes). That
leaves about 37 KB of flash below the bootloader instead of 8.4 KB. Half of
that saving is the on-watch native code compiler, which nothing on the watch
needed.

**An awake watch no longer spends about 6% of its CPU on garbage
collection.** One `gc.collect()` takes 6–7 ms, and the tick ran one eight
times a second. It now runs one a second, or after an event.

| Measure | Before | After |
| --- | --- | --- |
| `wasp.free` after boot | 8,352 B | 19,152 B |
| `gc.mem_free()` with a REPL attached | 4,608 B | 17,488 B |
| Firmware `.text` | 327,368 B | 298,604 B |
| `gc.collect()`, one call | 7.1 ms | 6.4 ms |
| Collections per second while awake and idle | 8 | 1 |
| SoftDevice RAM reserved / used | 14,784 / 14,784 B | 14,784 / 9,216 B |

## 2. What changed, and where it lives

Each change went into the branch that introduced the code it touches. A change
to code that came from upstream got a new branch.

| Branch | Change | Saving |
| --- | --- | --- |
| `04-widgets-package` | The widgets package imports a module when a name is first used, not all 14 at boot | boot heap |
| `08-launchers` | `list_launcher` is no longer frozen; only the simulator used it | 1.1 KB flash |
| `16-lazy-app-loading` | `wasp.py` no longer imports the step counter just for an `isinstance` | boot heap |
| `21-freeze-pkgmgr` | The companion's `pkg` proxy unloads `pkgmgr` after every call | ~1.2 KB heap after any package call |
| `29-battery-voltage-cache` | Bug: the voltage cache was never reset while charging (assigned to a local); the level is now integer maths, with no floats allocated every second | correctness, garbage |
| `30-boot-heap` | Fonts load on first use; the notification view is built when opened | boot heap |
| `31-idle-gc` | The tick collects once a second or after an event, not on every tick | ~50 ms of CPU a second |
| `32-frozen-trim` | Dual clock digits and the torch and music icons move into their apps; fonts drop seven unused functions | ~3 KB flash |
| `33-draw-allocations` | The notification bar redraws only on change; text drawing stops slicing a memoryview per glyph row | draw time, garbage |
| `34-micropython-trim` | Moves the submodule to the fork commits below | see below |
| `35-no-native-emitter` | Moves the submodule to the fork commit that turns off the on-watch native emitter | 14 KB flash |
| `36-gb-json-line` | `GB({...})` lines are decoded as JSON by a C REPL line hook instead of being compiled | 4 ms and a 512-byte block per message |
| `37-accel-image` | `ACCEL=bma421` or `ACCEL=bma425` builds firmware for one accelerometer | 6 KB flash, opt-in |

On the MicroPython fork (`v1.29-wasp-os`):

- **No `help()`, complex numbers or async/await** on the PineTime: 3.6 KB of
  flash, and nothing in wasp-os used them.
- **REPL history is cut from eight lines to one.** The companion sends every
  message as one REPL line (`GB({...})`). readline kept the last eight on
  the heap, where they took up to a few KB and broke up free space. That
  fits the 512-byte "contiguous block" failures seen after long sessions.
- **`--gc-sections` now runs alongside LTO.** LTO alone kept 5.3 KB of
  unreferenced libm and libc (`lgammaf`, `erff`, the hyperbolic functions,
  `strstr`). The IRQ vector table was checked after the change: every
  handler is still the real one.
- **The SoftDevice is set up as a peripheral only, and the RAM it doesn't
  use goes to the heap.** It used to reserve a central role and two links.
  `sd_ble_enable()` reports that the peripheral-only setup needs `0x23a8`
  bytes, so the board sets `_sd_ram_used = 0x2400`. The reservation itself
  stays at `0x39c0`, because the bootloader keeps its retained-RAM block at
  `0x200039c0` and `nrf_rtc.py` reads it there. Instead, the 5.5 KB gap is
  added to the GC as a second heap area (`MICROPY_GC_SPLIT_HEAP`), which
  costs 620 bytes of flash. `main.c` clears the area list first, so a soft
  reset doesn't add the gap twice. This was checked with a soft reboot.
- **The native code emitter is off the watch: 14 KB of flash.** Frozen
  `@native` and `@viper` code (draw565, st7789, `_tick`) is compiled on the
  host by mpy-cross. Native `.mpy` packages arrive already compiled. Setting
  `MICROPY_EMIT_THUMB=0` together with
  `MICROPY_PERSISTENT_CODE_LOAD_NATIVE=1` keeps the runtime support
  (`nativeglue`, `mp_fun_table`) and drops the emitter and its compiler
  paths. The frozen native functions are byte-for-byte the same size, and on
  the watch text, images and fills draw and the tick runs. A
  `@micropython.native` typed at the REPL is now a `SyntaxError`.

## 3. Measured and left alone

- **The C stack stays at 8 KB.** After boot and a REPL session, painting the
  stack showed a peak of 6,280 bytes. There's no safe 2 KB to take, and
  heavier use (deep compiles, JSON) will only go deeper. Measure again after
  a day of real use before going lower.
- **The switch-time collections in `16-lazy-app-loading` stay.** One app
  switch runs about five, roughly 30 ms. Each is there for a reason given in
  its comment: a large app only fits after a collection. Merging them is
  possible, but needs a test with the largest frozen app on a full heap
  first.

## 4. Companion messages and accelerometer images

**Messages skip the compiler.** Gadgetbridge and the companion send every
message as a REPL line, `GB({...})`. On the watch, compiling a typical
notification took 5.8 ms; `json.loads` takes 1.7 ms. With the GC paused, the
garbage left behind differs by only about 50–100 bytes, because the compiler
frees its own parse tree. An earlier draft of this report called the
compiler "the source of most fragmentation", and the measurements don't
support that. What matters more is that the parser starts with a 512-byte
rule stack (64 entries of 8 bytes). That is the "REPL needs 512 contiguous
bytes" limit seen on the watch, and every notification needed such a block.
A REPL line hook in the MicroPython fork (`MICROPY_REPL_LINE_HOOK`) now
gives each line to `wasp/modules/gbline` first. If the line is `GB(` +
valid JSON + `)`, the module decodes it and calls `GB()`. Anything else
(Python-only syntax, a mistyped line) goes to the compiler as before. This
needs no change to Gadgetbridge or the companion. It was checked on the
watch with a JSON escape (`\/`) that only the JSON path decodes, a
single-quoted message that falls back to the compiler, and a broken line
that still reports its error.

**One image per accelerometer is opt-in.** The default image still carries
both 6 KB configuration blobs, so it works on any PineTime.
`make BOARD=pinetime ACCEL=bma425 all` (or `bma421`) links one blob and
saves 6,192 bytes. An image built for the other chip still boots and runs;
the accelerometer reports `invalid sensor`, so there is no step counter.
Both outcomes were checked on a PineTime with a BMA425 (chip ID `0x13`).

## 5. Not done

These were left because each saves well under 200 bytes, or costs more than
it saves:

- `StepIterator` could move out of the always-loaded `steplogger`.
- Several public `const()` names (`R`, `G`, `B`, `TICK_PERIOD`) could become
  private, so they stop costing a global each.
- `mpy-cross` could target `armv7emsp` instead of `armv7m`, which helps
  float maths in native code.
- `MICROPY_QSTR_BYTES_IN_HASH=0` would save about 0.8 KB, but slows every
  string intern, the compiler included.
- `MICROPY_ALLOC_PARSE_RULE_INIT` could drop from 64 to 32. That would halve
  the 512-byte block every *other* REPL line needs. The stack grows on
  demand, so nothing breaks, but deep code then pays for reallocations.

## 6. How the numbers were taken

- **Flash:** `arm-none-eabi-size`, and `nm -S` compared symbol by symbol,
  against a clean build of `development` at `0fdba8c`.
- **Heap:** `wasp.free`, recorded once after startup, read over the NUS
  REPL with `tools/nus.py`. Also `micropython.mem_info()`.
- **GC time:** `time.ticks_us()` around one `gc.collect()` on a settled watch.
- **SoftDevice need:** a probe build called `sd_ble_enable()` with a base that
  was too low. The SoftDevice answers `NRF_ERROR_NO_MEM` and writes the
  minimum it needs back into the argument.
- **Stack peak:** a probe build painted the stack with `0x55aa55aa` at
  startup, and the REPL then scanned for the first overwritten word with
  `machine.mem32`.

The probes were taken out before the final build.
