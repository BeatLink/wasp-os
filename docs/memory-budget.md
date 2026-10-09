# Memory budget

The nRF52832 has 64 KB of RAM, shared between the MicroPython heap, the stack
and the SoftDevice. What is left over decides how many applications can exist
at once, and for a long time the answer was "barely one". This records where
it goes and what changed. Written in September 2026, measured on a PineTime.

## 1. Verdict

**Applications are built when opened and dropped when left.** Registering one
used to build it immediately and keep it for as long as the watch was on.
Recording them instead took the free heap from **5,264 bytes to 11,696**.

**Freezing does not help with this.** Frozen code and constants live in flash,
which is why images cost nothing, but an instance costs RAM whether or not its
code is frozen. Every application here is already frozen.

**The launcher was the expensive one**, not the applications opened from it.

## 2. How to measure this

`wasp.free` is recorded once, after startup, and is the number to quote.
`gc.mem_free()` is the live figure and needs a `gc.collect()` first or it
reports uncollected garbage as used.

Be aware that a BLE REPL session costs about 5 KB of the very heap being
measured, so every figure taken over `gatttool` is pessimistic by roughly
that much. Comparisons between two REPL measurements are fair; a REPL
measurement compared against `wasp.free` is not.

Anything that leaves an application bound in the REPL's globals keeps it
alive, which ruins the next measurement and usually needs a reboot. Bind
nothing that is not needed, and prefer one pre-compiled line that walks the
whole sequence and stores results in a list allocated in advance:

```python
r = [0, 0, 0]
s = wasp.system.switch
s(F); r[0] = gc.mem_free(); s(L); r[1] = gc.mem_free(); s(A); r[2] = gc.mem_free()
```

The line is compiled before any of it runs, so it still works when the heap is
too full to compile anything new.

## 3. Where it went

Measured over a REPL, so about 5 KB lower than reality throughout:

| Point | Free |
| --- | --- |
| At rest | 5,488 |
| After switching to the watch face | 5,488 |
| **After opening the launcher** | **1,632** |
| After opening the alarm from there | 0, then MemoryError |

**The launcher cost 3,856 bytes.** The alarm needs about 832 to construct and
could not fit in what was left, which is why it raised the low memory pager.
The alarm was never the problem, and a `gc.collect()` before loading it did
not help because nothing collectable was being held.

For scale, the parts of an application:

| Part | Cost |
| --- | --- |
| Importing a frozen module | ~200 bytes |
| Constructing `AlarmApp` | ~832 bytes |
| Its twelve 3-byte alarm slots and a 12-double array | ~400 bytes |

## 4. What holds memory now

After the change, exactly one application instance is alive: whichever is in
the foreground. The rings hold `AppEntry`, which is a name, a path and a
lazily read icon reference. Frozen icons live in flash, so caching one costs a
pointer.

The launcher used to be the exception, built in `Manager.__init__` and held
forever with its module pinned by a top level import. It is an `AppEntry` like
everything else now.

Two things still persist deliberately:

- **The notification app**, because a notification can arrive at any time.
- **Anything referenced from elsewhere.** The alarm app stays alive while it
  has a pending alarm, because the scheduler holds its bound method.

Pending alarms no longer keep the alarm app in memory. It schedules its own
entry rather than a bound method, so the scheduler builds the app only when an
alarm falls due. Start up builds it once to schedule `alarms.txt` and lets it
go.

Dropping an application used to leave its module behind: importing `a.b.c`
also stores `c` on `a.b`, and only `sys.modules` was cleared, so every
application opened, and every module the launcher read an icon from, stayed
half loaded. Clearing that attribute too freed 1600 bytes for the alarm app
alone. On a PineTime with an alarm on, free heap after boot went from 7.0 KB
to 8.7 KB, against 9.0 KB with no alarm.

## 5. What this costs

An application is rebuilt every time it is opened, so state survives leaving it
only through the application's `save` and `restore` methods, or by its staying
resident through `PERSIST`. Saved values are kept in RAM on the application's
entry, a start time rather than an elapsed time, which costs 192 bytes of heap
across the default set. They do not survive a restart; a store on the external
flash was considered and left out, because it would write on every switch and
the stopwatch's uptime-based values are meaningless after a restart anyway.

Rebuilding is cheap because the code is frozen: about 200 bytes and a fraction
of a millisecond to import, and under a kilobyte to construct.

## 6. Recommendations

1. **Do not hold application instances.** One foreground application, plus
   whatever a callback legitimately keeps alive.
2. **Do not reach for freezing to save RAM.** It saves flash and makes loading
   cheap; instances cost the same either way.
3. **Quote `wasp.free`, not `gc.mem_free()` over a REPL**, or say which one
   and subtract the session.
4. **Give an application `save` and `restore`** rather than keeping it resident,
   unless the scheduler holds a callback of its own.
