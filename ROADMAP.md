# NeoTime Roadmap

NeoTime starts from wasp-os and aims to offer everything that both wasp-os and
InfiniTime can do. This document is the master inventory of those features.
Every item carries a NeoTime checkbox so progress can be tracked here.

Sources: InfiniTime 1.16.0 (`InfiniTimeOrg/InfiniTime` main, September 2026)
and wasp-os v0.4-189 (`wasp-os/wasp-os` master, August 2026) plus the
BeatLink fork that NeoTime is cloned from.

Legend for the source columns: **Yes** = present, **Partial** = limited form,
**No** = absent, **Opt** = present but disabled or not frozen in by default.

How to read the NeoTime column: `[x]` done, `[ ]` not started, `[~]` in
progress. wasp-os features are inherited, so most wasp-os "Yes" rows start as
`[x]`; that only means the code is in the tree, not that it has been tested on
NeoTime.

---

## 1. Platform baseline

| Area | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| Language / runtime | C++20 on FreeRTOS, LVGL 7, NimBLE | MicroPython (nRF port, old MicroPython release) with frozen modules | [x] MicroPython |
| Supported watches | PineTime, Moy-TFK5/TIN5/TON5/UNK clones | PineTime, Colmi P8, Senbono K9, DS-D6, 96Boards Nitrogen | [x] wasp-os set |
| Display | ST7789 240x240 over DMA SPI, hardware scroll for transitions | ST7789 240x240 over SPI, line buffer, no framebuffer | [x] |
| Touch | CST816S with gestures (tap, double tap, long tap, 4 swipes) | CST816S with tap and 4 swipes; K9 button-only touch | [x] |
| Accelerometer | BMA421 and BMA425 auto-detected | BMA421 via C module | [x] BMA421 / [ ] BMA425 |
| Heart-rate sensor | HRS3300 with ALS | HRS3300 with ALS | [x] |
| External flash | 4 MB SPI NOR, littlefs, OTA slot and bootloader assets | SPI NOR via micropython-eeprom, littlefs2 at `/flash` | [x] |
| Bootloader | MCUBoot with slot swap and auto-revert | wasp-bootloader (Adafruit fork) plus reloader | [x] |
| Watchdog | nRF WDT with reset-reason reporting | Watchdog fed from tick and REPL, long-press reset | [x] / [ ] reset reason |
| Desktop simulator | InfiniSim (SDL2, separate repo) | Built in SDL2 simulator with skin | [x] |
| Memory model | 64 KB RAM, apps compiled in | RAM is the constraint; apps enabled on demand | [x] |

## 2. Apps

### 2.1 App inventory

| App | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| Stopwatch | Yes: start/pause/clear, 4 stored laps, hours field, wake lock | Yes: start/stop/reset, split times, runs while asleep | [x] wasp-os / [ ] lap buffer like InfiniTime |
| Alarm | Yes: single alarm, once / daily / weekdays, time remaining, persisted | Yes: up to 4 alarms, per-weekday toggles, snooze, persisted to `alarms.txt` | [x] wasp-os / [ ] time-remaining info |
| Timer | Yes: MM:SS counters, hold-to-reset animation, wake lock | Yes: MM:SS spinners, vibrates on expiry | [x] |
| Steps | Yes: today, goal arc, yesterday, trip counter | Yes: today, midnight reset, per-day history graphs | [x] wasp-os / [ ] goal arc / [ ] yesterday / [ ] trip counter |
| Heart rate | Yes: FFT PPG, status states, background interval, wake lock | Yes: filter-chain PPG, scrolling graph, raw logging | [x] wasp-os / [ ] background measurement |
| Music | Yes: artist/album/track, elapsed/total, disc animation, volume page | Yes: play/pause/fwd/back, swipe volume, track and artist | [x] wasp-os / [ ] album, position, animation |
| Paint | Yes: freehand drawing, long-press colour cycle | No | [ ] |
| Paddle (Pong) | Yes | No | [ ] |
| Twos (2048) | Yes | Yes upstream (`play2048`), dropped from the fork | [ ] restore play2048 |
| Dice | Yes: NdD, shake to roll, haptics | No | [ ] |
| Metronome | Yes: BPM arc, tap tempo, beats per bar, vibration | No | [ ] |
| Navigation (Maps) | Yes: flag, narrative, distance, progress; needs resources | No | [ ] needs a navigation BLE service |
| Calculator | Yes: fixed point, 12 digits, error states | Opt: keypad, `eval()` based | [x] wasp-os / [ ] harden |
| Weather | Yes: current plus 5-day forecast, icons | Yes: current only from Gadgetbridge | [x] current / [ ] forecast |
| Motion | Opt: live 3-axis chart and steps | No (Self Test has partial sensor readouts) | [ ] |
| Flashlight | Yes: white screen, 3 brightness dots | Opt: white and red modes, brightness cycling | [x] wasp-os |
| Notifications viewer | Yes: 5 stored, preview mode, call buttons | Yes: pager over notification queue, clear confirmation | [x] wasp-os / [ ] history of 5 |
| Settings | Yes: 15 entries, see section 5 | Yes: 5 pages, see section 5 | [x] wasp-os |
| Software (enable/disable apps) | No (compile time) | Yes: runtime checkboxes, auto-discovers apps on flash | [x] |
| Launcher | Yes: 6 icons per page tile grid | Yes: 4 icons per page grid | [x] |
| Battery info | Yes: %, mV, charging arc | Partial: battery meter widget only | [ ] |
| System info | Yes: 5 pages incl. tasks, heap, reset reason, IDs | Partial: Self Test shows free memory | [ ] |
| Firmware validation | Yes: validate or roll back | No (bootloader handles recovery) | [ ] |
| Firmware update screen | Yes: progress and state | No (DFU handled by bootloader) | [ ] |
| Pass key display | Yes: 6-digit pairing key | No | [ ] |
| Crash screen | Error screen with boot errors | Yes: CrashApp shows traceback in pager | [x] |
| Beacon (HRS LED flasher) | No | Opt | [x] |
| DisaBLE (turn BLE off) | Opt via settings toggle | Opt app | [x] |
| Faces chooser | Yes via settings | Yes: Faces app with previews | [x] |
| Four in a row | No | Opt: alpha-beta AI, 7 levels | [x] |
| Gallery (BMP viewer) | No | Opt: RGB565 BMPs from flash | [x] |
| Game of Life | No | Opt | [x] |
| Haiku | No | Opt: from `haiku.txt` | [x] |
| Hello (example) | No | Opt | [x] |
| Level (spirit level) | No | Opt: calibration menu | [x] |
| Morse notepad | No | Opt | [x] |
| Phone finder | Yes via Immediate Alert (watch side) | Opt: rings the phone via Gadgetbridge | [x] |
| Pomodoro | No | Opt: presets, vibration patterns | [x] |
| Puzzle 15 | No | Opt: solvable boards | [x] |
| Read Me (flash app demo) | No | Opt | [x] |
| Snake | No | Opt | [x] |
| Sports (stopwatch + steps) | No | Opt | [x] |
| Template app | Documented in `doc/code/Apps.md` | Opt: reference app with all entry points | [x] |
| Self Test / benchmarks | No | Opt: render benchmarks, widget tests, crash test | [x] |
| Demo (logo sweep) | No | Opt | [x] |

### 2.2 App framework capabilities

| Capability | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| Add an app | C++ class, register in `Apps.h.in` and CMake | Python file: frozen via `wasp.toml`, uploaded to flash, or exec'd over REPL | [x] |
| Per-app availability check | `IsAvailable()` hides apps missing resources | `no_except` flag and Software app discovery | [x] |
| App lifecycle hooks | Constructor, `Refresh`, `OnTouchEvent`, `OnButtonPushed` | `foreground`, `background`, `sleep`, `wake`, `tick`, `touch`, `swipe`, `press`, `preview` | [x] |
| Screen transitions | Directional slide animations, return direction | Display muted during switch, no animation | [ ] transitions |
| App icons | FontAwesome glyphs | 2-bit RLE icon per app, `ICON` attribute | [x] |
| Package layout | One directory per app | Fork: `apps/NAME/app.py` with icon and screenshot; build still expects flat files | [~] wire packages into `wasp.toml`, Makefile and tests |
| Runtime app enable/disable | No | Yes (Software app) | [x] |
| Wake lock | RAII `WakeLock` | `keep_awake()` per tick | [x] |

## 3. Watch faces

| Face | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| Digital | Yes: 12/24 h, date, steps, HR, weather, status icons | Yes (`clock`): HH:MM, date, battery | [x] wasp-os / [ ] steps, HR, weather, notification icons |
| Digital with weekday | Part of Digital | Yes (`week_clock`), default face | [x] |
| Analog | Yes: hands with outlines, ticks, icons | Yes (`chrono`): hands via `polar()`, battery | [x] wasp-os / [ ] icons |
| PineTimeStyle | Yes: sidebar, 18-colour palette, gauge styles, weather toggle, long-press menu | No | [ ] |
| Terminal | Yes: key/value shell aesthetic | No | [ ] |
| Infineat | Yes: diagonal lines, 7 colour schemes, side cover, needs resources | No | [ ] |
| Casio G-7710 | Yes: segmented fonts, needs resources | No | [ ] |
| Pride flag | Yes: 4 flags | No | [ ] |
| Dual clock (stacked) | No | Yes | [x] |
| Fibonacci clock | No | Yes | [x] |
| Resistor colour-code clock | No | Yes | [x] |
| Word clock | No | Yes | [x] |
| Per-face settings via long press | Yes (PTS, Infineat, Pride) | No | [ ] |
| Face chooser with preview | Settings list, hides unavailable | Faces app with live preview | [x] |
| Persisted face selection | Yes | Yes via `wasp.toml` default and Faces app | [x] |

## 4. Navigation and system screens

| Item | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| Swipe up from face | Launcher | Launcher | [x] |
| Swipe down from face | Notifications | Notifications (vibrate if none) | [x] |
| Swipe left/right from face | Nothing / Quick settings | Quick ring of favourite apps | [x] / [ ] quick settings |
| Quick settings panel | Yes: brightness, flashlight, notification mode, settings | No | [ ] |
| Button click | Back / wake | Home then sleep | [x] |
| Button double click | Notifications | No | [ ] |
| Button long press | Return to watch face | Reset after about 5 s (watchdog) | [ ] |
| Button longer press | System info | No | [ ] |
| Context-sensitive NEXT event | No | Yes (K9 support) | [x] |
| Status bar | StatusIcons: battery, plug, BLE, radio off, alarm | StatusBar: battery meter, clock, BLE, notification icons | [x] / [ ] alarm icon |
| Notification preview popup with timeout | Yes: 7 s, dismiss animation | Yes: popup via NotificationApp | [x] |
| Incoming call accept / mute / reject | Yes | No (protocol has `call`, unimplemented) | [ ] |
| Chimes | Off / hourly / half-hourly | No | [ ] |
| Always-on display | Yes with reduced frame rate | No | [ ] |
| Low memory handling | Heap counters in SysInfo | MemoryError caught, low-memory pager | [x] |
| Crash handling | Error screen | CrashApp with traceback | [x] |

## 5. Settings

| Setting | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| Brightness | 3 levels plus Off and AlwaysOn, quick settings | 3 levels slider | [x] |
| Screen timeout | 5/7/10/15/20/30 s | `blank_after`, 15 s default, not user-settable | [ ] UI |
| Always-on display toggle | Yes | No | [ ] |
| Wake modes | Single tap, double tap, raise wrist, shake, lower wrist | Button, charger event | [ ] raise / [ ] shake / [ ] tap / [ ] lower wrist |
| Shake threshold calibration | Yes, live readout | No | [ ] |
| Time format 12/24 h | Yes | 24 h only | [ ] |
| Set date and time manually | Yes | Yes (spinners) | [x] |
| Units metric / imperial | Weather format | Units toggle | [x] |
| Steps goal | Yes, 1 000 to 500 000 | No | [ ] |
| Heart-rate background interval | Off / continuous / 30 s to 30 m | No | [ ] |
| Chimes | Yes | No | [ ] |
| Notification mode | On / Off / Sleep | Silent / Mid / High level | [x] / [ ] sleep mode |
| Bluetooth radio toggle | Yes, not persisted | DisaBLE app (restart to re-enable) | [x] |
| OTA and file access mode | Enabled / Disabled / Till reboot | No | [ ] |
| Firmware validate / roll back | Yes | No | [ ] |
| Battery info | Yes | No | [ ] |
| About / system info | Yes | No | [ ] |
| Watch face select | Yes | Faces app | [x] |
| Theme / colours | Per-face colour menus, 18-colour palette | Global 11-slot RGB565 theme blob, `themer.py` | [x] theme blob / [ ] per-face colours |
| Settings persistence | Versioned struct on littlefs, dirty flag | Mostly RAM; alarms in `alarms.txt` | [ ] persist settings to flash |
| Remember last menu page | Yes | No | [ ] |

## 6. UI toolkit and graphics

| Item | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| Widgets | LVGL objects plus Counter, DotIndicator, PageIndicator, StatusIcons, List, CheckboxList | BatteryMeter, Clock, NotificationBar, StatusBar, ScrollIndicator, Button, ToggleButton, Checkbox, GfxButton, Slider, Spinner, Stopwatch, ConfirmationView | [x] / [ ] page indicator / [ ] dot indicator |
| Drawing primitives | LVGL | fill, blit, 1-bit and 2-bit RLE, string with alignment, wrap, line, polar, lighten, darken | [x] |
| Fonts | JetBrains Mono, Open Sans, FontAwesome, Material Icons, segment fonts, external fonts on flash | sans18/24/28/36, clock, clock_dual bitmap fonts | [x] / [ ] more sizes / [ ] fonts loadable from flash |
| Icons | FontAwesome glyphs and RLE images | 2-bit RLE icon set, `rle_encode.py` | [x] |
| Images from flash | `.bin` LVGL images via resources package | BMP gallery, RLE from `haiku.rle` | [x] |
| Colour palette | 18 named colours | Algorithmic 256-colour CLUT, RGB565 | [x] |
| Text wrapping | LVGL | `wrap()` | [x] |
| Screen scrolling lists | ScreenList with up/down and long-press paging | PagerApp, ScrollIndicator | [x] |

## 7. Phone integration and BLE

### 7.1 Protocols

| Item | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| Transport | Standard GATT services (NimBLE) | Nordic UART Service with Gadgetbridge JSON (Bangle.js style) | [x] NUS / [ ] GATT services |
| Companion apps | Gadgetbridge, Amazfish, Siglo, InfiniLink (iOS), ITD, WatchMate, InfiniTimeExplorer | Gadgetbridge (Bangle.js device), wasptool | [x] Gadgetbridge / [ ] others |
| Notifications in | ANS 0x1811 New Alert plus custom event char, 11 categories | `notify` JSON: id, src, title, subject, body, sender, tel | [x] |
| Notification dismiss from phone | Not applicable | `notify-` by id | [x] |
| Incoming call handling | Accept / reject / mute over ANS event | `call` documented, not implemented | [ ] |
| Current time | CTS server and client | `--rtc` from wasptool, Gadgetbridge set time | [x] / [ ] CTS |
| Device information | 0x180A manufacturer, model, FW, HW | No | [ ] |
| Battery level | 0x180F read and notify | No | [ ] |
| Heart-rate broadcast | 0x180D read and notify | No | [ ] |
| Immediate alert (find watch) | 0x1802 vibration and alert | `find` JSON drives vibrator | [x] |
| Motion service | Steps and raw XYZ, notify | No | [ ] |
| Music service | 14 characteristics, events for open/play/pause/next/prev/volume | `musicstate`, `musicinfo`, `music` commands over NUS | [x] NUS / [ ] GATT |
| Navigation service | Flag, narrative, distance, progress | No | [ ] |
| Weather service | Current with sunrise/sunset plus 5-day forecast | `weather` JSON: temp, humidity, text, wind, location | [x] current / [ ] forecast |
| Alarm sync from phone | No | `alarm` JSON documented, not implemented | [ ] |
| Vibrate command | Via immediate alert | `vibrate` documented, not implemented | [ ] |
| Find phone (watch to phone) | No | `findPhone` JSON | [x] |
| Pairing with pass key | Yes, PassKey screen | No | [ ] |
| Bond persistence | Yes | No | [ ] |
| Fast advertising restart | Yes | Not applicable | [ ] |
| BLE radio off | Yes | DisaBLE app | [x] |

### 7.2 File transfer and firmware update

| Item | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| File system over BLE | BLEFS (Adafruit protocol v4): read, write, delete, mkdir, listdir, move | REPL over NUS: `wasptool --upload/--pull/--binary`, `shell.py` | [x] wasptool / [ ] BLEFS |
| OTA firmware update | Nordic legacy DFU service in app, MCUBoot swap, validation step | Reboot to bootloader, DFU via nrfutil / ota-dfu / Gadgetbridge / DaFlasher | [x] |
| OTA lock-out setting | Enabled / disabled / till reboot | No | [ ] |
| External resources package | `infinitime-resources-X.zip` with fonts and images, `resources.json`, obsolete file list | Individual uploads (`haiku.rle`, gallery BMPs, `.mpy`) | [ ] resource bundle |
| Firmware version reporting | Device Information Service | `wasptool`, none over BLE | [ ] |

### 7.3 Developer tooling over BLE

| Item | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| REPL over BLE | No | Yes (NUS, pynus) | [x] |
| `wasptool` | Not applicable | console, upload, push, pull, binary, exec, eval, rtc, check-rtc, battery, memfree, reset, bootloader, ota, send-notification, device, verbose | [x] |
| Debug notifications from PC | No | `--send-notification` | [x] |

## 8. Sensors, health and motion

| Item | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| Step counting | Hardware step counter, 2-day history, daily rollover, trip counter | Hardware step counter, midnight reset, 6-minute logging to flash, per-day graphs | [x] wasp-os / [ ] trip counter |
| Daily step goal | Yes | No | [ ] |
| Step history | Yesterday only | Unlimited on flash (`logs/YYYY/MM-DD.steps`) | [x] |
| Distance estimate | No | No (on wasp-os 0.5 list) | [ ] |
| Sports / activity app | No | Yes | [x] |
| Heart rate algorithm | 64-sample FFT at 10 Hz, SNR check, 40-230 BPM, not-on-wrist via ALS | Biquad HPF/AGC/LPF chain, autocorrelation, 30-210 BPM | [x] wasp-os / [ ] evaluate FFT approach |
| Background HR measurement | Yes with interval setting | No | [ ] |
| Raw HR data export | No | `hrs.data` plus `hrs2csv.py` | [x] |
| Raise-wrist wake | Yes | No | [ ] |
| Lower-wrist sleep | Yes | No | [ ] |
| Shake detection | Yes, calibratable | No | [ ] |
| Raw accelerometer readout | Motion app and Motion service | `accel_xyz()`, Level app | [x] |
| Sleep tracking | No | No | [ ] |

## 9. Power management

| Item | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| Sleep states | Running, GoingToSleep, Sleeping, AODSleeping | Awake / asleep, `deepsleep` between ticks | [x] |
| Wake sources | Touch, button, raise, shake, charger, notification, call, alarm, chime, DFU, pairing | Button, charger change | [ ] touch / [ ] raise / [ ] shake / [x] button / [x] charger |
| Wake lock | Yes | `keep_awake()` | [x] |
| Screen timeout | User setting | `blank_after` | [ ] setting UI |
| Backlight | Hardware PWM via PPI, 5 levels | 3 GPIO levels | [x] / [ ] PWM dimming |
| Battery measurement | ADC every 10 min plus on charge events | ADC with averaging on demand | [x] |
| Battery service over BLE | Yes | No | [ ] |
| SPI flash power saving | Deep sleep on flash | Automatic power-saving mode | [x] |
| Display low-power mode | `LowPowerOn`, sleep | `poweroff` | [x] |
| Vibration motor | One-shot and ringing patterns, two timers | `pulse(duty, ms)` | [x] / [ ] ringing pattern |
| SoftDevice sleep logic | Not applicable | On wasp-os future list | [ ] |

## 10. Storage and resources

| Item | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| File system | littlefs, about 3.3 MB usable, POSIX-like API | littlefs2 at `/flash`, auto-format on first boot | [x] |
| Settings file | Versioned struct | None (alarms only) | [ ] |
| Alarm persistence | Versioned struct | `alarms.txt` | [x] |
| User apps on flash | No | `apps/*.py` and `.mpy`, auto-discovered | [x] |
| Precompiled modules | Not applicable | `mpy-cross` with `-march=armv7m` | [x] |
| Resource verification | `VerifyResource()` | No | [ ] |
| Flash map documentation | Yes | Bootloader protocols documented | [x] |
| Gallery images | No | `gallery/*.bmp` | [x] |

## 11. Bootloader, recovery and updates

| Item | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| Bootloader | MCUBoot, image swap and auto-revert, watchdog before jump | wasp-bootloader: splash, watchdog, long-press reset, OTA recovery | [x] |
| Bootloader replacement tool | Not applicable | reloader: factory, mcuboot and daflasher variants with pre and post-flash verification, board identity check, UICR update | [x] |
| Recovery firmware | Yes (`pinetime-recovery`) | Bootloader OTA mode | [x] |
| Firmware validation | Explicit validate step or rollback | Not needed | [ ] |
| Boot graphic | PineTime logo from flash offset 0 | Splash screen, colour logo on the future list | [x] |
| Time survives reset | No (CTS resync) | PNVRAM keeps the RTC counter across resets | [x] |
| Stay in bootloader after battery run-down | Not applicable | On the future list | [ ] |
| Power-off support | No | On the future list | [ ] |

## 12. Build, test and documentation

| Item | InfiniTime | wasp-os | NeoTime |
|---|---|---|---|
| Build system | CMake with cmake-nRF5x, app and face lists selectable | Makefile: bootloader, reloader, micropython, apps, sim, check, docs, dfu, flash, debug, dist | [x] |
| App selection at build time | `ENABLE_USERAPPS`, `ENABLE_WATCHFACES` | `wasp.toml` and `configure_wasp_apps.py` | [x] / [ ] support package layout |
| Docker build | Yes, published image, devcontainer, gitpod | Dockerfile and shell script; Nix shell and flake | [x] |
| CI | Build, size report on PRs, clang-format and clang-tidy checks, simulator build, docker image publish | Full dist build on push and PR, artifacts as CI builds | [x] / [ ] size report |
| Simulator | InfiniSim | `make sim` with skin, keyboard and mouse input, screenshots | [x] |
| Automated tests | Format and tidy scripts only | pytest: QA gates, smoke test across all apps, unit tests | [x] |
| Code style tooling | clang-format, clang-tidy, hooks | None | [ ] linter / formatter |
| Memory analysis docs | Yes | No | [ ] |
| Debug docs | gdb, JLink, OpenOCD, SWD, nRF52-DK stub | Debug and troubleshooting guide, Black Magic gdb target | [x] |
| User docs | Getting started, apps, faces, OTA guides per companion | Sphinx: install, app guide, app library, reference manual, contributing | [x] |
| BLE protocol docs | ble.md, BLEFS, Motion, Navigation, Weather formats | Gadgetbridge protocol docstring, bootloader protocols | [x] / [ ] document new services |
| Screenshot pipeline | Manual | Simulator `s` key at 358x406, enforced by tests | [x] |
| Font conversion | lv_font_conv, resource generator scripts | micropython-font-to-py | [x] |
| Image conversion | lv_img_conv, bin2c | rle_encode (1, 2 and 8 bit), encode.sh | [x] |
| Versioning | CMake version plus git hash in SysInfo | `git describe` in dist | [x] |
| Companion protocol docs for third parties | Yes | Partial | [ ] |

## 13. Known gaps carried over

Unfinished or missing items noted in either upstream project. They belong on
this roadmap because NeoTime inherits them.

From wasp-os:

- [ ] Gadgetbridge `alarm`, `vibrate` and `call` messages are documented but unimplemented.
- [ ] `PinHandler` has no button debounce.
- [ ] K9 touch coordinates are not decoded; the K9 is button-only.
- [ ] `shell.download()` is broken.
- [ ] Newer Colmi P8 revisions have an unsupported step-counter part.
- [ ] MicroPython is old; GCC 13 and newer need `-Wno-error` workarounds (upstream issue 493).
- [ ] Distance estimation in the step counter (0.5 list).
- [ ] Use SoftDevice sleep logic, fix BLE hangs, asynchronous SPI chip select for double buffering (future list).
- [ ] Bootloader: stay in bootloader after battery run-down, power-off without splash, colour boot logo (future list).
- [ ] The fork's package layout (`apps/NAME/app.py`, `faces/NAME/app.py`) is not wired into `wasp.toml`, the Makefile or the tests, and the flat `watch_faces/` copies still exist.
- [ ] Upstream binary releases were withdrawn and the project is looking for maintainers.

From InfiniTime:

- [ ] Motion app exists but is disabled by default.
- [ ] Timer has no presets.
- [ ] No sleep tracking.
- [ ] Applications and watch face docs are out of date with the code.

## 14. Suggested phases

1. **Consolidate the base.** Wire the package layout into the build, restore play2048, add a settings file on flash, add a linter, keep the wasp-os test suite green.
2. **Parity on daily use.** Wake modes (tap, raise, shake), screen timeout setting, 12/24 h format, quick settings panel, step goal, notification history, call handling, chimes.
3. **Standard GATT services.** Device Information, Battery, Current Time, Heart Rate, Immediate Alert, Motion, Music, Weather with forecast, Navigation, so InfiniTime companion apps work with NeoTime.
4. **Ports of InfiniTime apps.** Paint, Paddle, Dice, Metronome, Navigation, Motion, Battery Info, System Info.
5. **Ports of InfiniTime faces.** PineTimeStyle, Terminal, Infineat, Casio G-7710, Pride flag, plus per-face colour menus and a resource bundle for fonts and images.
6. **Polish.** Screen transitions, always-on display, background heart-rate measurement, PWM backlight dimming, BLEFS, size reporting in CI.
