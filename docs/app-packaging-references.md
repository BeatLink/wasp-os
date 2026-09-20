# App packaging references

Background for the installable app package format and the companion app protocol. Four
reports: how apps are loaded today, what storage the PineTime has, whether apps can be
loaded just in time, and where BLEFS fits. Written against NeoTime at commit 726cecf,
September 2026.

## 1. How apps are loaded today

### Two tiers of apps

**Frozen apps** are compiled into the firmware image.

- `wasp.toml` lists the apps and watch faces for a build.
- `tools/configure_wasp_apps.py` copies each `apps/NAME/app.py` to `wasp/apps/user/NAME.py`
  and writes `wasp/boards/manifest_user_apps.py`, so the MicroPython build freezes them as the
  modules `apps.user.NAME`.
- The same script writes `wasp/appregistry.py` with three tuples: `software_list` (what the
  Software app offers), `faces_list` (what the Faces app offers) and `autoload_list` (the
  default face, the quick ring and any `auto_load` apps).
- The system apps in `wasp/apps/system/` (launcher, settings, software, pager, step counter),
  the drivers and the wasp core are always frozen via `wasp/boards/<board>/manifest.py`.
- Changing this set means `make BOARD=pinetime micropython` and a DFU flash of
  `micropython.zip`.

**Flash-loaded apps** live on the external flash filesystem.

- The SPI NOR holds a littlefs2 volume mounted at `/flash`. Boot does `os.chdir('/flash')`
  unless the button is held for safe mode, so plain imports resolve there
  (`wasp/boards/pinetime/watch.py.in`).
- On first boot the firmware writes a `/flash/main.py` that just includes the frozen
  `wasp/main.py`. That file is user-editable and is the documented way to make a flash app
  start at boot.
- The Software app scans `/flash/apps/` for `*.py` and `*.mpy`, skips names that clash with a
  frozen app, and registers each as `apps.NAME.NameApp` (`wasp/apps/system/software.py`).
- `make apps` compiles every `apps/NAME/app.py` to `apps/NAME.mpy` with
  `mpy-cross -mno-unicode -march=armv7m`.

### Registration

`wasp.system.register('module.ClassApp')` imports the module into a throwaway namespace,
instantiates the class, deletes the module from `sys.modules`, then appends the instance to the
launcher ring (or the quick ring, or slot 0 for a watch face). `unregister(cls)` removes the
first instance of that class from the launcher ring. The rings are plain lists in RAM.

### Transport

Everything reaches the watch through the REPL over the Nordic UART Service.

- `tools/wasptool --upload` pastes source lines into `shell.upload(path)` on the watch, which
  writes them to a file. `--binary` streams base64 chunks of 64 bytes into an open file through
  a one-line lambda. Both are slow but need nothing beyond the REPL.
- Gadgetbridge messages use the same channel: the phone sends `GB({...})` as a line of Python
  and the REPL evaluates it against `wasp/gadgetbridge.py`, where `main.py` has already pulled
  `GB` into the REPL namespace with `from gadgetbridge import *`.
- Gadgetbridge itself prefixes that line with `\x10`, but that is an Espruino convention, not a
  wasp-os one. Nothing in wasp-os looks for it. It survives only because the MicroPython line
  editor inserts a character just when it falls between 32 and 126, so a byte of 0x10 is
  discarded. That byte is `CHAR_CTRL_P`, "recall previous history line", and the editor acts on
  it when `MICROPY_REPL_EMACS_KEYS` is set. The setting follows the ROM feature level, which the
  nrf port leaves at core features, so the key handling is compiled out today. A build at extra
  features would turn every prefixed message into the previous line plus the new one. New code
  should send the bare line and leave the prefix to Gadgetbridge.
- There is no file-transfer service. The roadmap lists BLEFS as not done.

### What blocks a clean package-by-package flow

- **Nothing persists enable state.** The launcher ring is RAM only, so the Software app's
  checkboxes reset at boot. A registry file read at boot is needed.
- **Watch faces are frozen only.** The Faces app reads `appregistry.faces_list` and never looks
  at `/flash`.
- **No resource convention.** Icons are fine because apps embed the RLE bytes in the module.
  Extra files (gallery images, `haiku.txt`, `alarms.txt`, `Morse.txt`) are opened by
  cwd-relative names with no per-app directory.
- **No config API.** Apps persist their own files ad hoc. `wasp.system` holds brightness,
  notification level, units and theme, and `set_theme` is RAM only. Configuring an app from the
  phone needs a convention such as a per-app JSON file plus a message the app reacts to.
- **RAM and compile limits.** A flash-loaded app costs more RAM than a frozen one because its
  bytecode is loaded into the heap instead of executing in place, and the on-target compiler
  fails on large `.py` files. Packages should ship `.mpy`.
- **Bytecode ABI.** A `.mpy` only loads on the MicroPython bytecode version it was compiled
  for. The firmware pins the `wasp-os/micropython` fork at an old release, and any upgrade
  invalidates every installed package, so packages and firmware both need an ABI tag.

### Verdict

Regular apps can already be installed, removed and enabled one at a time over the REPL with no
reflash. A firmware flash is only needed for the base image. Making that solid needs a small
frozen package manager module, a persisted registry, a per-app directory layout on `/flash`, and
the Faces app reading from it. The open protocol decision is whether to keep streaming files
through the REPL or add a proper file service.

## 2. Storage spaces on the PineTime

Figures read from `boards/nrf52832_512k_64k_bldr78.ld` and `boards/s132_6.1.1.ld` in the nrf port.

| Space | Size | What lives there | How it changes |
|---|---|---|---|
| Internal flash (nRF52832) | 512 KB | SoftDevice S132 from 0 to 0x26000, 152 KB. The MicroPython image with every frozen module from 0x26000 to 0x78000, 328 KB. wasp-bootloader in the last 32 KB. | Only by DFU flash. Frozen apps execute in place here, which is why they are cheap on RAM. |
| External SPI NOR | 4 MB | The littlefs2 volume at `/flash`: `main.py`, `apps/`, app data files, step logs, gallery images | Writable at runtime over the REPL. This is where installable packages go. wasp-os uses nothing else here, unlike InfiniTime, which reserves an OTA slot. |
| RAM (nRF52832) | 64 KB | The SoftDevice reserves the first 0x39c0, about 14.5 KB, which is why the PNVRAM block sits at `0x200039c0`. The stack takes 8 KB. What is left, a little under 42 KB, is the MicroPython heap, and the link fails if it drops below 32 KB. | The heap is the real ceiling and cannot be raised. Every enabled app holds its instance and any flash-loaded bytecode there. |

There is no spare region in internal flash. The linker sets `_fs_size = 0`, so the whole 328 KB
application window is firmware, and any partition carved out of it comes directly out of the
frozen modules.

Two consequences for the package design:

- **Storage is not the constraint, RAM is.** Four megabytes holds hundreds of `.mpy` packages,
  but only what is enabled costs RAM. Install and enable must stay separate operations, which
  the Software app already models.
- **Frozen versus flash is a RAM trade, not a space trade.** Moving an app out of the firmware
  frees internal flash but raises its RAM cost when enabled. A minimal frozen base plus
  installable packages is the right split, but the heaviest always-on apps, such as the default
  watch face, should stay frozen.

## 3. Can apps be loaded just in time?

Three different things hide in the question, and only one is available on this hardware today.

**Lazy loading into RAM at launch.** Yes, and it is the practical answer. Today `register()`
imports and instantiates immediately, so every enabled app holds its instance and bytecode in the
heap for the whole session. Instead the launcher ring can hold a small descriptor per package,
with the name and icon taken from a manifest, and the app is imported and instantiated only when
opened, then dropped and garbage collected when it goes to background. The launcher and the
Software app never import anything. The cost is a launch delay while the `.mpy` is read from the
SPI NOR and loaded, plus some heap fragmentation. This needs no toolchain changes.

**Executing in place from the external flash.** No. The nRF52832 has no QSPI or memory-mapped
external flash, and the PineTime's NOR chip sits on plain SPI. Bytecode there can only run after
being copied into RAM. The nRF52840 can do this, the PineTime cannot.

**Executing in place from internal flash without a rebuild.** Possible in principle, not with
the current firmware. Frozen modules already give this at build time: the bytecode runs from
internal flash and only the module's objects use the heap. Recent MicroPython releases add
ROMFS, a read-only filesystem image whose `.mpy` files load in place from a memory-mapped region,
and the SoftDevice lets the application write internal flash at runtime. A firmware could keep a
spare internal-flash partition and have the package manager copy an installed `.mpy` into it. Two
things stand in the way: the fork pins an old MicroPython with no ROMFS, so the MicroPython
upgrade comes first, and the application region is only about 320 KB shared with the firmware,
so the partition would hold a handful of apps. It would still be the right home for always-on
pieces such as the default watch face.

**Recommendation.** Build the package system around lazy loading now: packages live on
`/flash`, the launcher holds descriptors, and code is loaded on launch and released on exit.
Keep the descriptor format open to a later placement choice per package, external versus
internal, once the MicroPython upgrade lands. Frozen modules then shrink to the system core plus
whatever must never fail to load.

## 4. BLEFS versus a protocol over the REPL

BLEFS is separate work. The MicroPython upgrade does not bring it.

**What it is.** BLEFS is Adafruit's BLE file transfer protocol: an application-level GATT
service with a version characteristic and a transfer characteristic that carries framed read,
write, delete, mkdir, listdir and move commands. InfiniTime implements it in its own C++ against
NimBLE. It is a protocol spec, not a library, so any firmware that wants it writes its own server.

**What the upgrade changes.** Nothing about BLEFS itself. The watch exposes only the Nordic UART
Service, implemented in C inside the nrf port. Adding a second GATT service means either C in the
port, as NUS is done now, or Python through whatever BLE API the port compiles in. The old nrf
port has `ubluepy`, which can define custom services and characteristics; whether the wasp-os
build enables it is unconfirmed because the submodule is not checked out. A newer MicroPython may
give a cleaner API for that, but it will still not contain a file-transfer service.

**The alternative that needs no BLE work.** Define the file protocol on top of the REPL channel
that already exists: a small frozen Python module on the watch accepts framed commands over NUS,
the same way `GB()` does, and the companion app's existing transport talks to it. This works
today with no change to the BLE stack.

**Trade-off.** A NUS-based protocol is the fast path and stays entirely in Python. BLEFS costs a
GATT service in the firmware but buys compatibility with the InfiniTime tooling that already
speaks it, including Gadgetbridge's file upload.

**Recommendation.** NUS protocol first, with the command set shaped like BLEFS so a real BLEFS
service can be added under it later without changing the companion app's package logic.
