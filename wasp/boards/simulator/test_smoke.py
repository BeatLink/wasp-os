import pytest
import time
import wasp
import apps.test.app
import settings

def step():
    wasp.system._tick()
    wasp.machine.deepsleep()
    time.sleep(0.1)
wasp.system.step = step

wasp.watch.touch.press = wasp.watch.touch.i2c.sim.press
wasp.watch.touch.swipe = wasp.watch.touch.i2c.sim.swipe

wasp.system.secondary_init()
wasp.system.apps = {}
for app in wasp.system.quick_ring + wasp.system.launcher_ring:
    wasp.system.apps[app.NAME] = app

@pytest.fixture
def system():
    system = wasp.system
    if system.app != system.quick_ring[0]:
        system.switch(system.quick_ring[0])
    system.step()

    return system

def test_step(system):
    system.step()

def test_quick_ring(system):
    names = [ x.NAME for x in system.quick_ring ]
    assert('WeekClk' in names)
    assert('Steps' in names)
    assert('Stopclock' in names)
    assert('Heart' in names)

def test_launcher_ring(system):
    names = [ x.NAME for x in system.launcher_ring ]
    assert('Settings' in names)
    assert('Software' in names)

@pytest.mark.parametrize("name",
        ('Steps', 'Stopclock', 'Heart', 'Settings', 'Software'))
def test_app(system, name):
    system.switch(system.apps[name])
    for i in range(4):
        system.step()
    system.switch(system.quick_ring[0])

def test_constructor(system, constructor):
    # Special case for the notification app
    if 'NotificationApp' in str(constructor):
         wasp.system.notify(wasp.watch.rtc.get_uptime_ms(),
             {
                 "src":"testcase",
                 "title":"A test",
                 "body":"This is a long message containingaverylongwordthatdoesnotfit and lots of other contents as well."
             })

    try:
        system.switch(constructor())
        system.step()
        system.step()
        wasp.watch.touch.press(120, 120)
        system.step()
        system.step()
        system.switch(system.quick_ring[0])
    except FileNotFoundError:
        # Some apps intend to generate exceptions during the constructor
        # if they don't have required files available
        if 'HaikuApp' not in str(constructor):
            raise

def test_stopwatch(system):
    system.switch(system.apps['Stopclock'])

    system.step()

    wasp.watch.button.value(0)
    system.step()
    assert(system.app._timer._started_at > 0)
    wasp.watch.button.value(1)

    system.step()
    system.step()
    system.step()

    wasp.watch.button.value(0)
    system.step()
    assert(system.app._timer._started_at == 0)
    wasp.watch.button.value(1)

    system.step()

def test_selftests(system):
    """Walk though each screen in the Self Test.

    This is a simple "does it crash" test and the only thing we do to stimulate
    the app is press in the centre of the screen. For most of the tests that
    will do something useful! For example it will run the benchmark for every
    one of the benchmark tests.
    """
    system.switch(apps.test.app.TestApp())
    system.step()

    start_point = system.app.test

    for i in range(len(system.app.tests)):
        wasp.watch.touch.press(120, 120)
        system.step()
        wasp.watch.touch.swipe('down')
        system.step()

    assert(start_point == system.app.test)

def test_selftest_crash(system):
    system.switch(apps.test.app.TestApp())
    system.step()

    def select(name):
        for i in range(len(system.app.tests)):
            if system.app.test == name:
                break
            wasp.watch.touch.swipe('down')
            system.step()
        assert system.app.test == name

    select('Crash')

    wasp.watch.button.value(0)
    with pytest.raises(Exception):
        system.step()

    # Get back to a safe state for the next test!
    try:
        wasp.watch.button.value(1)
        system.step()
    except:
        pass
    system.step()

def test_settings(system):
    """Walk though each screen in the setting application.

    This is a simple "does it crash" test and the only thing we do to stimulate
    the app is press in the centre of the screen.
    """
    system.switch(settings.SettingsApp())
    system.step()

    start_point = system.app._current_setting

    for i in range(len(system.app._settings)):
        wasp.watch.touch.press(120, 120)
        system.step()
        wasp.watch.touch.swipe('down')
        system.step()

    assert(start_point == system.app._current_setting)

def test_swipe_up_slides_the_launcher_in(system):
    assert wasp.watch.display.scroll_offset == 0

    system.navigate(wasp.EventType.UP)

    assert system.app_entry is system.launcher
    # The launcher arrived by moving the display rather than redrawing it.
    assert wasp.watch.display.scroll_offset == 240

def test_leaving_a_slid_launcher_unscrolls(system):
    system.navigate(wasp.EventType.UP)
    system.switch(system.quick_ring[0])

    assert wasp.watch.display.scroll_offset == 0

def test_the_launcher_still_slides_the_second_time(system):
    system.navigate(wasp.EventType.UP)
    system.switch(system.quick_ring[0])
    system.navigate(wasp.EventType.UP)

    assert system.app_entry is system.launcher
    assert wasp.watch.display.scroll_offset == 240

def _paged_alarm_app():
    from apps.user.alarm import AlarmApp
    app = AlarmApp()
    # Six alarms is two pages of four.
    app.alarms = [[6 + i, 0, 0x80] for i in range(6)]
    app.num_alarms = 6
    return app

def test_the_alarm_list_slides_between_pages(system):
    app = _paged_alarm_app()
    system.switch(app)
    assert app._num_pages == 2

    app.swipe((wasp.EventType.UP, 0, 0))
    assert app.scroll == 1
    # The second page arrived by moving the display rather than redrawing it.
    assert wasp.watch.display.scroll_offset == 240

    app.swipe((wasp.EventType.DOWN, 0, 0))
    assert app.scroll == 0
    assert wasp.watch.display.scroll_offset == 0

def test_a_full_alarm_redraw_unscrolls(system):
    app = _paged_alarm_app()
    system.switch(app)
    app.swipe((wasp.EventType.UP, 0, 0))

    app._draw()

    assert wasp.watch.display.scroll_offset == 0
