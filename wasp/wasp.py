# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson
"""Wasp-os system manager
~~~~~~~~~~~~~~~~~~~~~~~~~

.. data:: wasp.system

    wasp.system is the system-wide singleton instance of :py:class:`.Manager`.
    Application must use this instance to access the system services provided
    by the manager.

.. data:: wasp.watch

    wasp.watch is an import of :py:mod:`watch` and is simply provided as a
    shortcut (and to reduce memory by keeping it out of other namespaces).
"""
import gc
import json
import machine
import micropython
import sys
import watch
import widgets
import appregistry

from apps.system import steplogger
from apps.system.pager import PagerApp, CrashApp, NotificationApp
from events import EventType, EventMask
from pin_handler import PinHandler

def _key_app(d):
    """Get a sort key for apps."""
    return d.NAME


class AppEntry():
    """An application the system knows about but has not loaded.

    The rings hold these rather than application objects, so an application
    costs a name and a path until the moment it is opened. Its icon is read
    the first time the launcher asks for it and then kept, which is free:
    frozen images live in flash and only the reference is in RAM.

    What survives an application being left is decided as it is left, see
    :py:meth:`Manager._background`: either the whole instance, or the few
    values its save method hands back.
    """
    __slots__ = ('path', 'NAME', 'no_except', '_icon', '_app', 'state', 'resident')

    def __init__(self, path, name, no_except=False):
        self.path = path
        self.NAME = name
        self.no_except = no_except
        self._icon = None
        # The instance kept while the application asked to outlive being left.
        self._app = None
        # What the application's save method returned, for restore to take back.
        self.state = None
        self.resident = False

    @property
    def ICON(self):
        if self._icon is None:
            try:
                self._icon = _peek(self.path, 'ICON')
            except:
                self._icon = False
        return self._icon if self._icon else None

    def load(self):
        """Return the kept instance, or build the application and restore its state.

        An instance is kept when the application was left asking to persist,
        such as a timer that is counting: its callback is still with the
        scheduler, and building a second one would show a stopped timer while
        the first one rings.
        """
        if self._app:
            return self._app
        app = _load(self.path)
        state = self.state
        self.state = None
        restore = getattr(app, 'restore', None)
        if state is not None and restore:
            restore(state)
        return app

    def __call__(self):
        """Wake the application for a pending alarm, building it first if it is not loaded.

        An application that queues its entry with the scheduler, rather than a
        bound method of its own, does not have to stay in memory to be woken.
        Its alarm method is called once it is in the foreground.
        """
        system.switch(self)
        # A switch asked for from inside an application's handler happens later, so check it did.
        if system.app_entry is self:
            alarm = getattr(system.app, 'alarm', None)
            if alarm:
                alarm()


def _import(path):
    """Import the module holding path and return its namespace.

    Collect first. An application used to be built during startup, on a heap
    with nothing on it; building one on demand happens on a heap that has
    been in use for a while, and a large application needs room that only a
    collection will give back.
    """
    modname = path[:path.rindex('.')]
    gc.collect()
    namespace = {}
    exec('import ' + modname, namespace)
    return modname, namespace


def _peek(path, attribute):
    """Read one class attribute without keeping the module loaded."""
    modname, namespace = _import(path)
    try:
        return eval(path + '.' + attribute, namespace)
    finally:
        del namespace
        _unload(modname)
        gc.collect()


def _load(path):
    """Instantiate path, leaving the module unloaded behind us."""
    modname, namespace = _import(path)
    try:
        # The module is in memory now, so give back whatever importing it
        # displaced before asking for the application itself.
        gc.collect()
        return eval(path + '()', namespace)
    finally:
        del namespace
        _unload(modname)
        gc.collect()

def _alarm_set():
    """Tell whether alarms.txt, as the alarm app writes it, holds an alarm that is switched on."""
    try:
        with open('alarms.txt') as f:
            text = f.read()
        for alarm in text.split(';'):
            fields = alarm.split(',')
            # The third field holds the alarm app's flags, where 0x80 means switched on.
            if len(fields) == 3 and int(fields[2]) & 0x80:
                return True
    except (OSError, ValueError):
        pass
    return False


def _unload(modname):
    """Forget a module, everywhere its import left a reference to it.

    Importing a.b.c also stores c as an attribute of a.b, which keeps the
    module alive after it has left sys.modules. Installed packages leave
    their pkg and pkg.NAME levels behind as well.
    """
    del sys.modules[modname]
    dot = modname.rfind('.')
    if dot > 0:
        parent = sys.modules.get(modname[:dot])
        leaf = modname[dot + 1:]
        if parent is not None and hasattr(parent, leaf):
            delattr(parent, leaf)
    if modname.startswith('pkg.'):
        sys.modules.pop(modname[:dot], None)
        sys.modules.pop('pkg', None)


def _pkgmgr(call, *args):
    """Make one call into the package manager without keeping it loaded."""
    loaded = 'pkgmgr' in sys.modules
    import pkgmgr
    try:
        return getattr(pkgmgr, call)(*args)
    finally:
        if not loaded:
            del sys.modules['pkgmgr']


def packages(kind='app'):
    """Return the index entries of the enabled packages of one kind."""
    return _pkgmgr('enabled', kind)


class PackageEntry(AppEntry):
    """An application installed as a package on the external flash.

    Its icon is a file beside its code, so the launcher draws it without
    importing anything. A package marked resident keeps its one instance once
    built, as an application declaring PERSIST does.
    """

    def __init__(self, entry):
        name = entry['name']
        super().__init__('pkg.{}.app.{}'.format(name, entry['cls']),
                         entry.get('label', name))
        self.package = name
        self.resident = entry.get('resident', False)

    @property
    def ICON(self):
        if self._icon is None:
            self._icon = _pkgmgr('icon_of', self.package) or False
        return self._icon if self._icon else None


# The screen timeouts the Settings app offers, in seconds.
BLANK_AFTER = (5, 10, 15, 30, 60)


def _key_alarm(d):
    """Get a sort key for alarms."""
    return d[0]

class Manager():
    """Wasp-os system manager

    The manager is responsible for handling top-level UI events and
    dispatching them to the foreground application. It also provides
    services to the application.

    The manager is expected to have a single system-wide instance
    which can be accessed via :py:data:`wasp.system` .
    """

    # Where settings are kept across a restart, relative to /flash; None keeps them in RAM.
    settings_file = 'settings.json'

    def __init__(self):
        self.app = None
        self.app_entry = None
        # Set while an application's own handler is running, and the
        # application it asked to switch to.
        self._dispatching = False
        self._pending = None

        self.bar = widgets.StatusBar()

        self.quick_ring = []
        # The launcher is built when it is opened and dropped when it is
        # left, like every other application. Holding it meant the watch
        # face, the launcher and whatever was opened from it were all in
        # memory at once, which the alarm app could not fit alongside.
        self.launcher = AppEntry('apps.system.grid_launcher.GridLauncherApp',
                                 'Launcher')
        self.launcher_ring = []
        self.notifications = {}
        self.musicstate = {}
        self.musicinfo = {}
        self.weatherinfo = {}
        self._units = "Metric"
        # The settings as last written, or None until start up has read them back.
        self._settings_text = None

        self._theme = (
                b'\x7b\xef'     # ble
                b'\x7b\xef'     # scroll-indicator
                b'\x7b\xef'     # battery
                b'\xe7\x3c'     # status-clock
                b'\x7b\xef'     # notify-icon
                b'\xff\xff'     # bright
                b'\xbd\xb6'     # mid
                b'\x39\xff'     # ui
                b'\xff\x00'     # spot1
                b'\xdd\xd0'     # spot2
                b'\x00\x0f'     # contrast
        )

        self._blank_after = 15
        self._clock_24h = True

        self._alarms = []
        self._brightness = 2
        self._notifylevel = 2
        if 'P8' in watch.os.uname().machine:
            self._nfylevels = [0, 225, 450]
        else:
            self._nfylevels = [0, 40, 80]
        self._nfylev_ms = self._nfylevels[self._notifylevel - 1]
        self._button = PinHandler(watch.button)
        self._charging = True
        self._scheduled = False
        self._scheduling = False

    def secondary_init(self):
        global free

        if not self.app:
            # Register default apps if main hasn't put anything on the quick ring
            if not self.quick_ring:
                self.register_defaults()
            self.register_packages()
            self._load_settings()

            # System start up...
            watch.display.poweron()
            watch.display.mute(True)
            watch.backlight.set(self._brightness)
            self.sleep_at = watch.rtc.uptime + 90
            if watch.free:
                gc.collect()
                free = gc.mem_free()

            self.switch(self.quick_ring[0])

    def register_defaults(self):
        """Register the default applications."""

        for app in appregistry.autoload_list:
            self.register(app[0], app[1], app[2], app[3], app[4])

        self.register('apps.system.step_counter.StepCounterApp', True,
                      no_except=True, name='Steps')
        self.register('apps.system.settings.SettingsApp', no_except=True,
                      name='Settings')
        self.register('apps.system.software.SoftwareApp', no_except=True,
                      name='Software')

    def _settings(self):
        """Return the settings worth keeping across a restart, as JSON text."""
        face = self.quick_ring[0] if self.quick_ring else None
        return json.dumps({
            'brightness': self._brightness,
            'notify_level': self._notifylevel,
            'units': self._units,
            'blank_after': self._blank_after,
            'clock_24h': self._clock_24h,
            'theme': list(self._theme),
            'face': [face.path, face.NAME] if isinstance(face, AppEntry) else None,
        })

    def _save_settings(self):
        """Write the settings to the flash, but only if they changed since the last write."""
        if self._settings_text is None or not self.settings_file:
            return
        try:
            text = self._settings()
            if text != self._settings_text:
                with open(self.settings_file, 'w') as f:
                    f.write(text)
                self._settings_text = text
        except Exception as e:
            # Losing a setting is better than failing whatever changed it.
            sys.print_exception(e)

    def _face_exists(self, path):
        """Tell whether a watch face saved before a restart can still be built."""
        if path.startswith('pkg.'):
            name = path.split('.')[1]
            return any(face['name'] == name for face in packages('face'))
        return any(face[0] == path for face in appregistry.faces_list)

    def _load_settings(self):
        """Apply the settings saved before the last restart, then start saving changes.

        Each value is checked before it is used, so a damaged file or a watch
        face that has since been removed leaves the default in place.
        """
        try:
            with open(self.settings_file) as f:
                saved = json.load(f)
            value = saved.get('brightness')
            if value in (1, 2, 3):
                self._brightness = value
            value = saved.get('notify_level')
            if value in (1, 2, 3):
                self._notifylevel = value
                self._nfylev_ms = self._nfylevels[value - 1]
            value = saved.get('units')
            if value in ('Metric', 'Imperial'):
                self._units = value
            value = saved.get('blank_after')
            if value in BLANK_AFTER:
                self._blank_after = value
            value = saved.get('clock_24h')
            if value in (True, False):
                self._clock_24h = value
            value = saved.get('theme')
            if value and len(value) == len(self._theme):
                self._theme = bytes(value)
            value = saved.get('face')
            if value and self._face_exists(value[0]):
                self.register(value[0], watch_face=True, name=value[1])
        except Exception:
            # A missing or damaged file leaves the defaults in place.
            pass
        try:
            self._settings_text = self._settings()
        except Exception as e:
            # Start up must finish even if the settings cannot be written out.
            sys.print_exception(e)

    def register_packages(self):
        """Register the enabled applications installed as packages.

        A damaged index or package must not stop the watch starting, so a
        failure is reported and the packages are skipped.
        """
        try:
            for entry in packages('app'):
                self.register(PackageEntry(entry),
                              quick_ring=entry.get('quick_ring', False))
        except Exception as e:
            sys.print_exception(e)

    def register(self, app, quick_ring=False, watch_face=False, no_except=False,
                 name=None):
        """Register an application with the system.

        An application named by its path is recorded rather than built, and is
        not loaded until something switches to it. Pass its name too, so the
        launcher can list it without loading anything.

        :param object app: The application to register, or the path to it
        :param object quick_ring: Place the application on the quick ring
        :param object watch_face: Make the new application the default watch face
        :param object no_except: Ignore exceptions when loading the application
        :param object name: Name to list a path under, defaulting to its class
        """
        if isinstance(app, str):
            if not name:
                name = app[app.rindex('.') + 1:]
                if name.endswith('App'):
                    name = name[:-3]
            # "Special case" for watches that have working step counters!
            # More usefully it allows other apps to detect the presence or
            # absence of a working step counter by looking at
            # wasp.system.steps .
            if app.endswith('.StepCounterApp'):
                try:
                    # Starting the sensor belongs with the step counter, but
                    # the app is only built when it is opened and the logger
                    # below reads the count straight away, so it happens here.
                    watch.accel.reset()
                    self.steps = steplogger.StepLogger(self)
                except:
                    pass
            app = AppEntry(app, name, no_except)
        elif type(app).__name__ == 'StepCounterApp':
            self.steps = steplogger.StepLogger(self)

        if watch_face:
            self.quick_ring[0] = app
            self._save_settings()
        elif quick_ring:
            self.quick_ring.append(app)
        else:
            self.launcher_ring.append(app)
            self.launcher_ring.sort(key = _key_app)

        # Saved alarms are scheduled as the app is built, so build it once now if one is on;
        # its entry is in a ring by now, which is what the app hands the scheduler.
        if isinstance(app, AppEntry) and app.path.endswith('.AlarmApp') and _alarm_set():
            try:
                app.load()
            except Exception as e:
                sys.print_exception(e)

    def unregister(self, cls):
        """Remove an application from the launcher.

        :param cls: The application's class, or the name it is listed under
        """
        for app in self.launcher_ring:
            if app.NAME == cls if isinstance(cls, str) else isinstance(app, cls):
                self.launcher_ring.remove(app)
                break

    @property
    def blank_after(self):
        """Seconds without input before the screen goes blank, one of BLANK_AFTER."""
        return self._blank_after

    @blank_after.setter
    def blank_after(self, value):
        self._blank_after = value
        self._save_settings()

    @property
    def clock_24h(self):
        """True to show the time as 24 hours, False for 12 hours."""
        return self._clock_24h

    @clock_24h.setter
    def clock_24h(self, value):
        self._clock_24h = value
        self._save_settings()

    def display_hour(self, hour):
        """Return an hour of the day, 0 to 23, as the user prefers to read it."""
        if self._clock_24h:
            return hour
        return hour % 12 or 12

    @property
    def units(self):
        """The units the user prefers, 'Metric' or 'Imperial'."""
        return self._units

    @units.setter
    def units(self, value):
        self._units = value
        self._save_settings()

    @property
    def brightness(self):
        """Cached copy of the brightness current written to the hardware."""
        return self._brightness

    @brightness.setter
    def brightness(self, value):
        self._brightness = value
        watch.backlight.set(self._brightness)
        self._save_settings()

    @property
    def notify_level(self):
        """Cached copy of the current notify level"""
        return self._notifylevel

    @notify_level.setter
    def notify_level(self, value):
        self._notifylevel = value
        self._nfylev_ms = self._nfylevels[self._notifylevel - 1]
        self._save_settings()

    @property
    def notify_duration(self):
        """Cached copy of the current vibrator pulse duration in milliseconds"""
        return self._nfylev_ms

    def _background(self):
        """Background the foreground application and keep what should outlive it.

        An application whose PERSIST is true as it is left keeps its one
        instance on its entry; PERSIST may be a property, true only while
        there is something running. Any other application is dropped, and if
        it has a save method the values that returns are kept for restore.
        """
        app = self.app
        if not app:
            return
        if 'background' in dir(app):
            try:
                app.background()
            except:
                # Leave something truthy behind so switching to the crash
                # handler does not run the start up path again.
                self.app = True
                raise
        entry = self.app_entry
        if entry:
            if entry.resident or getattr(app, 'PERSIST', False):
                entry._app = app
            else:
                entry._app = None
                save = getattr(app, 'save', None)
                if save:
                    entry.state = save()

    def _entry_of(self, app):
        """Find the entry keeping app, so an application switching to itself is still tracked."""
        for ring in (self.quick_ring, self.launcher_ring):
            for entry in ring:
                if isinstance(entry, AppEntry) and entry._app is app:
                    return entry
        return None

    def _retire(self):
        """Background the foreground application and let go of it."""
        self._background()
        self.app = None
        self.app_entry = None
        gc.collect()

    def _resolve(self, app):
        """Build an application from its entry, if it is not built already.

        :param app: An application or an AppEntry
        :returns:   (application, entry or None), or None if there is
                    nothing to switch to
        """
        if not isinstance(app, AppEntry):
            return (app, self._entry_of(app))
        if self.app_entry is app and self.app:
            return None
        if app.no_except:
            try:
                return (app.load(), app)
            except:
                return None
        return (app.load(), app)

    def switch(self, app):
        """Switch to the requested application.

        An unloaded application is built here and dropped again as soon as
        something else is switched to, so only the foreground application and
        the launcher occupy memory. An application referenced from elsewhere,
        by a pending alarm for instance, stays alive on that reference.
        """
        if isinstance(app, AppEntry):
            if self.app_entry is app and self.app:
                return
            if self._dispatching:
                # Wait until the handler that asked for this has returned,
                # so the application it belongs to can actually be freed.
                self._pending = app
                return
            # Let the outgoing application go before building the new one.
            # Two of them will not fit at once, and the one being left is
            # usually the launcher, which is the larger.
            self._retire()

        loaded = self._resolve(app)
        if not loaded:
            # Nothing is running if the retire above emptied the foreground,
            # so fall back to the watch face rather than leave the system
            # with no application at all.
            face = self.quick_ring[0]
            if not self.app and app is not face:
                self.switch(face)
            return
        self._switch(*loaded)

    def _switch(self, app, entry):
        """Switch to an application that is already built.

        :param app:   The application to show
        :param entry: The entry it came from, or None if it was passed in
        """
        if self.app is app:
            return

        self._background()

        # Clear out any configuration from the old application
        self.event_mask = 0
        self.tick_period_ms = 0
        self.tick_expiry = None

        self.app = app
        self.app_entry = entry
        # The outgoing application is unreachable by now unless something
        # else kept hold of it, so let the collector take it back.
        gc.collect()
        watch.display.mute(True)
        watch.display.set_scroll_area()
        watch.display.scroll(0)
        watch.drawable.reset()
        app.foreground()
        watch.display.mute(False)

    def slide(self, app):
        """Switch to an application by sliding it up into view.

        Only an application that can draw itself a band at a time can slide,
        because just 80 rows can be staged ahead of the display, so anything
        else is switched the usual way.
        """
        if isinstance(app, AppEntry):
            if self.app_entry is app and self.app:
                return
            self._retire()

        loaded = self._resolve(app)
        if not loaded:
            face = self.quick_ring[0]
            if not self.app and app is not face:
                self.switch(face)
            return
        (app, entry) = loaded

        if self.app is app or 'sliding' not in dir(app) \
                or watch.display.scroll_offset:
            self._switch(app, entry)
            return

        self._background()

        # Clear out any configuration from the old application
        self.event_mask = 0
        self.tick_period_ms = 0
        self.tick_expiry = None

        self.app = app
        self.app_entry = entry
        gc.collect()
        watch.drawable.reset()
        app.sliding()

    def navigate(self, direction=None):
        """Navigate to a new application.

        Left/right navigation is used to switch between applications in the
        quick application ring. Applications on the ring are not permitted
        to subscribe to :py:data`EventMask.SWIPE_LEFTRIGHT` events.

        Swipe up is used to bring up the launcher. Clock applications are not
        permitted to subscribe to :py:data`EventMask.SWIPE_UPDOWN` events since
        they should expect to be the default application (and is important that
        we can trigger the launcher from the default application).

        :param int direction: The direction of the navigation
        """
        app_list = self.quick_ring

        current = self.app_entry if self.app_entry else self.app

        if direction == EventType.LEFT:
            if current in app_list:
                i = app_list.index(current) + 1
                if i >= len(app_list):
                    i = 0
            else:
                i = 0
            self.switch(app_list[i])
        elif direction == EventType.RIGHT:
            if current in app_list:
                i = app_list.index(current) - 1
                if i < 0:
                    i = len(app_list)-1
            else:
                i = 0
            self.switch(app_list[i])
        elif direction == EventType.UP:
            self.slide(self.launcher)
        elif direction == EventType.DOWN:
            if current is not app_list[0]:
                self.switch(app_list[0])
            else:
                if len(self.notifications):
                    self.switch(NotificationApp())
                else:
                    # Nothing to notify... we must handle that here
                    # otherwise the display will flicker.
                    watch.vibrator.pulse()

        elif direction == EventType.HOME or direction == EventType.BACK:
            if self.app != app_list[0]:
                self.switch(app_list[0])
            else:
                self.sleep()

    def notify(self, id, msg):
        self.notifications[id] = msg

    def unnotify(self, id):
        if id in self.notifications:
            del self.notifications[id]

    def toggle_music(self, state):
        self.musicstate = state

    def set_music_info(self, info):
        self.musicinfo = info

    def set_weather_info(self, info):
        self.weatherinfo = info

    def set_alarm(self, time, action):
        """Queue an alarm.

        :param int time: Time to trigger the alarm (use time.mktime)
        :param function action: Action to perform when the alarm expires.
        """
        alarm = (time, action)
        # An application built again schedules its alarms again, so a repeat is dropped.
        if alarm not in self._alarms:
            self._alarms.append(alarm)
            self._alarms.sort(key=_key_alarm)

    def entry_for(self, app):
        """Find the entry an application was registered under, by its class name, or None."""
        name = '.' + type(app).__name__
        for ring in (self.quick_ring, self.launcher_ring):
            for entry in ring:
                if isinstance(entry, AppEntry) and entry.path.endswith(name):
                    return entry
        return None

    def cancel_alarm(self, time, action):
        """Unqueue an alarm."""
        alarms = self._alarms
        try:
            if not time:
                time_to_remove = [al[0] for al in alarms if al[1] == action]
                [alarms.remove((t, action)) for t in time_to_remove]
            else:
                alarms.remove((time, action))
        except:
            return False
        return True

    def request_event(self, event_mask):
        """Subscribe to events.

        :param int event_mask: The set of events to subscribe to.
        """
        self.event_mask |= event_mask

    def request_tick(self, period_ms=None):
        """Request (and subscribe to) a periodic tick event.

        Note: With the current simplistic timer implementation sub-second
        tick intervals are not possible.
        """
        if period_ms:
            self.tick_period_ms = period_ms
            self.tick_expiry = watch.rtc.get_uptime_ms() + period_ms
        else:
            self.tick_period_ms = 0
            self.tick_expiry = None

    def keep_awake(self):
        """Reset the keep awake timer."""
        self.sleep_at = watch.rtc.uptime + self.blank_after

    def sleep(self):
        """Enter the deepest sleep state possible.
        """
        watch.backlight.set(0)
        if 'sleep' not in dir(self.app) or not self.app.sleep():
            self.switch(self.quick_ring[0])
            self.app.sleep()
        watch.display.poweroff()
        watch.touch.sleep()
        self._charging = watch.battery.charging()
        self.sleep_at = None

    def wake(self):
        """Return to a running state.
        """
        if not self.sleep_at:
            watch.display.poweron()
            if 'wake' in dir(self.app):
                self.app.wake()
            watch.backlight.set(self._brightness)
            watch.touch.wake()

        self.keep_awake()

    def _handle_button(self, state):
        """Process a button-press (or unpress) event.
        """
        self.keep_awake()

        if bool(self.event_mask & EventMask.BUTTON):
            # Currently we only support one button
            if not self.app.press(EventType.HOME, state):
                # If app reported None or False then we are done
                return

        if state:
            self.navigate(EventType.HOME)

    def _handle_touch(self, event):
        """Process a touch event.
        """
        self.keep_awake()
        event_mask = self.event_mask

        # Handle context sensitive events such as NEXT
        if event[0] == EventType.NEXT:
            if bool(event_mask & EventMask.NEXT) and not self.app.swipe(event):
                # The app has already handled this one (mark as no event)
                event[0] = 0
            elif self.app == self.quick_ring[0] and len(self.notifications):
                event[0] = EventType.DOWN
            elif isinstance(self.app, NotificationApp):
                event[0] = EventType.UP
            else:
                event[0] = EventType.RIGHT

        if event[0] < 5:
            updown = event[0] == 1 or event[0] == 2
            if (bool(event_mask & EventMask.SWIPE_UPDOWN) and updown) or \
               (bool(event_mask & EventMask.SWIPE_LEFTRIGHT) and not updown):
                if self.app.swipe(event):
                    self.navigate(event[0])
            else:
                self.navigate(event[0])
        elif event[0] == 5 and self.event_mask & EventMask.TOUCH:
            self.app.touch(event)

        watch.touch.reset_touch_data()

    @micropython.native
    def _tick(self):
        """Handle the system tick.

        This function may be called frequently and includes short
        circuit logic to quickly exit if we haven't reached a tick
        expiry point.
        """
        rtc = watch.rtc
        update = rtc.update()

        alarms = self._alarms
        if update and alarms:
            now = rtc.time()
            head = alarms[0]

            if head[0] <= now:
                alarms.remove(head)
                head[1]()

        if self.sleep_at:
            if update and self.tick_expiry:
                now = rtc.get_uptime_ms()

                if self.tick_expiry <= now:
                    ticks = 0
                    while self.tick_expiry <= now:
                        self.tick_expiry += self.tick_period_ms
                        ticks += 1
                    self.app.tick(ticks)

            # An application asking to switch while its own handler is
            # running cannot be let go of, because the running frame still
            # refers to it. Note the request and act on it below, once the
            # handler has returned and the frame is gone.
            self._dispatching = True
            try:
                state = self._button.get_event()
                if None != state:
                    self._handle_button(state)
                    update = True

                event = watch.touch.get_event()
                if event:
                    self._handle_touch(event)
                    update = True
            finally:
                self._dispatching = False

            if self._pending:
                pending = self._pending
                self._pending = None
                self.switch(pending)

            if self.sleep_at and watch.rtc.uptime > self.sleep_at:
                self.sleep()

            # Collect once a second, or after an event, rather than on every tick.
            if update:
                gc.collect()
        else:
            if 1 == self._button.get_event() or \
                    self._charging != watch.battery.charging():
                self.wake()

    def run(self, no_except=True):
        """Run the system manager synchronously.

        This allows all watch management activities to handle in the
        normal execution context meaning any exceptions and other problems
        can be observed interactively via the console. This is used by the
        simulator or for debugging is not normally called. The watch instead
        calls self.schedule() directly at startup from main.py.
        """
        if self._scheduling:
            print('Watch already running in the background')
            return

        self.secondary_init()

        # Reminder: wasptool uses this string to confirm the device has
        # been set running again.
        print('Watch is running, use Ctrl-C to stop')

        if not no_except:
            # This is a simplified (uncommented) version of the loop
            # below
            while True:
                self._tick()
                machine.deepsleep()

        while True:
            try:
                self._tick()
            except KeyboardInterrupt:
                raise
            except MemoryError:
                self.switch(PagerApp("Your watch is low on memory.\n\nYou may want to reboot."))
            except Exception as e:
                # Only print the exception if the watch provides a way to do so!
                if 'print_exception' in dir(watch):
                    watch.print_exception(e)
                self.switch(CrashApp(e))

            # Currently there is no code to control how fast the system
            # ticks. In other words this code will break if we improve the
            # power management... we are currently relying on not being able
            # to stay in the low-power state for very long.
            machine.deepsleep()

    def _work(self):
        self._scheduled = False
        try:
            self._tick()
        except MemoryError:
            self.switch(PagerApp("Your watch is low on memory.\n\nYou may want to reboot."))
        except Exception as e:
            # Only print the exception if the watch provides a way to do so!
            if 'print_exception' in dir(watch):
                watch.print_exception(e)
            self.switch(CrashApp(e))

    def _schedule(self):
        """Asynchronously schedule a system management cycle."""
        if not self._scheduled:
            self._scheduled = True
            micropython.schedule(Manager._work, self)

    def schedule(self, enable=True):
        """Run the system manager synchronously."""
        self.secondary_init()

        if enable:
            watch.schedule = self._schedule
        else:
            watch.schedule = watch.nop

        self._scheduling = enable

    def set_theme(self, new_theme) -> bool:
        """Sets the system theme.

        Accepts anything that supports indexing,
        and has a len() equivalent to the default theme."""
        if len(self._theme) != len(new_theme):
            return False
        self._theme = new_theme
        self._save_settings()
        return True

    def theme(self, theme_part: str) -> int:
        """Returns the relevant part of theme. For more see ../tools/themer.py"""
        theme_parts = ("ble",
                       "scroll-indicator",
                       "battery",
                       "status-clock",
                       "notify-icon",
                       "bright",
                       "mid",
                       "ui",
                       "spot1",
                       "spot2",
                       "contrast")
        if theme_part not in theme_parts:
            raise IndexError('Theme part {} does not exist'.format(theme_part))
        idx = theme_parts.index(theme_part) * 2
        return (self._theme[idx] << 8) | self._theme[idx+1]

system = Manager()
