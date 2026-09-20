# NeoTime app packaging design

How watch apps are packaged, installed over Bluetooth, enabled and configured from the NeoTime
Companion App, with no firmware reflash per app.

The research this rests on is in [app-packaging-references.md](app-packaging-references.md). Read
that first for why the design looks like this.

## Scope

In scope: packages on the external flash, transfer over the existing Nordic UART Service, lazy
loading so an app costs RAM only while it is open, and per-app configuration from the phone.

Out of scope: placing apps in internal flash at runtime. The nrf port cannot write a ROMFS
partition, so that is a separate piece of firmware work. See section 5 of the references.

One firmware flash is still needed to land the frozen pieces below. After that, apps come and go
without another one.

## On-watch layout

```
/flash/pkg/index.json          what is installed and what is enabled
/flash/pkg/<name>/app.mpy      the code, imported as pkg.<name>.app
/flash/pkg/<name>/meta.json    the manifest, copied from the package
/flash/pkg/<name>/icon.rle     launcher icon, readable without importing the app
/flash/pkg/<name>/config.json  written by the manager, absent until configured
/flash/pkg/<name>/...          any other resources the app opens
```

`/flash/pkg/` and each package directory are plain directories. MicroPython imports through them
without an `__init__.py`, which is how the existing frozen `apps.user.NAME` modules already work.

Uninstalling is removing one directory and rewriting the index.

## Why the icon is a separate file

The launcher draws `app.ICON` off a live instance today. Under lazy loading there is no instance
until the app is opened, so the icon has to be readable on its own. `icon.rle` holds exactly the
bytes that the in-module `ICON` tuple concatenates to: a depth byte, a width byte, a height byte,
then the run-length data. The launcher reads it while drawing a page and drops it again.

Keep `ICON` in the module as well, so the app still works when loaded and nothing in the existing
app guide changes. The duplicate costs a couple of hundred bytes on a four megabyte chip.

## The manifest

`meta.json`, written by the build tool and copied to the watch verbatim.

| Field | Meaning |
|---|---|
| `name` | Directory and module name, snake case |
| `cls` | Class to instantiate, for example `MusicPlayerApp` |
| `label` | Short name for the launcher, the app's `NAME` |
| `version` | Package version string |
| `abi` | `.mpy` version and architecture the code was compiled for |
| `kind` | `app` or `face` |
| `resident` | True when the app must exist while not shown |
| `quick_ring` | True to place it on the quick ring rather than the launcher |
| `config` | Optional list of settings fields the phone renders |

`resident` is the flag that makes lazy loading safe. An app that registers a system alarm bound
to its own method, as the alarm app does, has to stay alive while in the background. Timer and
step counter are the same. Everything without background duty defaults to lazy.

A `config` field is an object with `key`, `type`, `label`, `default` and, depending on type,
`min`, `max` or `options`. Types are `bool`, `int` and `choice`.

## The index

`/flash/pkg/index.json` is the only file read at boot. It holds one entry per installed package
with the fields the system needs before anything is imported: name, label, class, kind, enabled,
resident and quick_ring. The manager rewrites it on install, uninstall, enable and disable, and
can rebuild it by scanning the package directories.

Reading one index beats reading N manifests, both for boot time and for heap.

## Import and lazy loading

`wasp.system.register` gains a lazy path that appends a descriptor rather than an instance. The
descriptor carries `NAME`, the module path, the class name and the icon path, which is all the
launcher needs to draw a page.

`wasp.system.switch` materialises a descriptor before calling `foreground`, and releases the
instance when the app goes to background, followed by a collection. Apps marked `resident` are
instantiated at boot as they are today and never released.

One detail: `register` currently deletes the imported module from `sys.modules` by its own name.
For `pkg.<name>.app` that leaves the `pkg` and `pkg.<name>` entries behind. The manager should
purge all three so a reinstall picks up new code.

## Wire protocol

Commands are lines of Python on the existing REPL channel, exactly as `GB({...})` already is.
The manager is imported in `main.py` so its name is in the REPL namespace. Replies are one JSON
object per line tagged `{"t": "pkg", ...}`, which the companion app's existing line decoder
already splits and parses.

| Command | Purpose |
|---|---|
| `pkg.abi()` | Report the watch's `.mpy` version and architecture |
| `pkg.ls()` | List installed packages with version and enabled state |
| `pkg.recv(path, size)` | Receive exactly `size` bytes into `path` |
| `pkg.rm(name)` | Delete a package and its index entry |
| `pkg.enable(name)` / `pkg.disable(name)` | Update the persisted enabled set |
| `pkg.cfg(name, json)` | Write `config.json` for a package |
| `pkg.reindex()` | Rebuild the index by scanning |

`recv` is the only one that leaves line mode. It has two transfer modes.

**Raw** reads exactly `size` bytes from `sys.stdin.buffer` in windows, acknowledging each. It
disables the interrupt character with `micropython.kbd_intr(-1)` first, so a `0x03` byte in the
payload is not read as Ctrl-C. This is the fast path and avoids the base64 overhead as well as
the per-line round trip that makes `wasptool` slow.

**Base64** reads one encoded line per window instead. It needs no control-character handling and,
more importantly, works on a firmware without `sys.stdin.buffer`. That attribute follows
`MICROPY_PY_SYS_STDIO_BUFFER`, which defaults to the extra feature level while the nrf port sits
at core features, so it is absent today. Base64 is therefore the only mode available before the
firmware change, which is what makes the `/flash` prototype possible.

`abi()` reports which modes the watch offers, so the phone picks the fast one when it exists.

Flow control is set by the buffer between the radio and Python, a fixed 128 byte array in
`ble_uart.c`. The consumer stalls for tens of milliseconds during a littlefs write, so the phone
must not run further ahead than the buffer holds.

| | Bytes |
|---|---|
| Receive ring today | 128 |
| Safe window today | 96 |
| Safe window after raising the ring to 1 KB | 512 |

Integrity is already covered per packet by the BLE link layer. `recv` still returns a 32-bit
additive sum so a truncated or duplicated window is caught.

## Configuration

The phone renders the `config` schema from the manifest, then calls `pkg.cfg`. The manager writes
`config.json` beside the app. On instantiation the manager calls `configure(values)` on the app
when the class defines it, otherwise the app reads the file itself in `foreground`.

## Firmware changes needed

All of these land in one flash:

- The package manager as a frozen module.
- The lazy path in `wasp.system.register` and `switch`.
- The Faces app reading faces from the index, not only from the frozen `faces_list`.
- The receive ring in `ble_uart.c` raised from 128 bytes to 1 KB.
- `MICROPY_PY_SYS_STDIO_BUFFER` enabled for the board, which is what puts `sys.stdin.buffer`
  there and unlocks raw transfer.

The manager can be prototyped before any of this by uploading it to `/flash/pkgmgr.py` and
importing it from `/flash/main.py`, which is already user-editable. That validates the format and
the protocol on real hardware. Only the lazy path genuinely needs freezing.

## Task list

### Phase 1, build tooling, no hardware needed

- [x] `tools/mkpkg.py`: compile `apps/NAME/app.py` with mpy-cross, encode `apps/NAME/icon.png`
      with `rle_encode.py`, write `meta.json`, emit a package directory and a `.zip`.
- [x] Per-app packaging metadata, read from an optional `apps/NAME/pkg.toml`, defaulting to the
      existing naming conventions.
- [x] A round-trip test that builds a package from a real app and checks the layout and the icon
      bytes against the in-module `ICON`. `tools/test_mkpkg.py`, 10 tests.

The builder probes mpy-cross for `-mno-unicode` rather than passing it unconditionally, because
MicroPython 1.29 removed that flag while the Makefile still uses it for the pinned old release.

### Phase 2, watch side, prototyped from `/flash`

- [x] `wasp/pkgmgr.py`: index read and write, `ls`, `rm`, `enable`, `disable`, `reindex`, `cfg`,
      plus `icon_of` and `config_of` for the launcher. `tools/test_pkgmgr.py`, 22 tests.
- [x] `recv`: both transfer modes, windowed acknowledgements and a returned checksum.
- [x] `abi`: report the bytecode version, the architecture and which transfer modes exist.
- [ ] Try it on real hardware: upload `wasp/pkgmgr.py` to `/flash/pkgmgr.py`, import it from
      `/flash/main.py`, and install a package built by `mkpkg.py` over base64.

### Phase 3, companion app

- [ ] `src/protocol/packages.ts`: the command encoders and the reply types.
- [ ] Transfer driver: chunk a file into windows, wait for each acknowledgement, verify the sum.
- [ ] Installed list with enable toggles, install and uninstall flows, ABI check before transfer.
- [ ] Settings form generated from the `config` schema.

### Phase 4, firmware

- [ ] Freeze the manager.
- [ ] Lazy path in `register` and `switch`, with the `resident` flag honoured.
- [ ] Faces app reads the index.
- [ ] Receive ring raised to 1 KB.
- [ ] Mark the apps that need `resident` in their manifests: alarm, timer, step counter.
