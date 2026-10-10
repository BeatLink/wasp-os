"""Widgets drawn as cards."""

import pytest

import wasp
import widgets


@pytest.fixture
def system():
    system = wasp.system
    if not system.app:
        system.secondary_init()
    return system


@pytest.mark.parametrize('y, value', ((20, 6), (60, 5), (100, 4)))
def test_a_spinner_counts_up_on_its_top_card_and_down_on_its_bottom_one(system, y, value):
    spinner = widgets.Spinner(10, 0, 0, 9, w=60, h=120)
    spinner.value = 5
    spinner.draw()

    spinner.touch((wasp.EventType.TOUCH, 40, y))

    assert spinner.value == value


def test_a_spinner_wraps_past_its_largest_value(system):
    spinner = widgets.Spinner(10, 0, 0, 9)
    spinner.value = 9

    spinner.touch((wasp.EventType.TOUCH, 40, 10))

    assert spinner.value == 0


def test_a_tap_outside_a_spinner_is_left_for_others(system):
    spinner = widgets.Spinner(10, 0, 0, 9)

    assert not spinner.touch((wasp.EventType.TOUCH, 100, 10))


def test_a_confirmation_answers_yes_on_its_left_card(system):
    view = widgets.ConfirmationView()
    view.draw('Restart the game?')

    assert view.touch((wasp.EventType.TOUCH, 60, 210))
    assert view.value is True


def test_the_settings_app_sets_the_brightness_tapped(system):
    from settings import SettingsApp
    saved = system.brightness
    app = SettingsApp()
    system.switch(app)
    app._sett_index = app._settings.index('Brightness')
    app._draw()
    (x, y, w) = app._cell(2, 3)

    app.touch((wasp.EventType.TOUCH, x + w // 2, y + 20))

    assert system.brightness == 3
    system.brightness = saved
    system.switch(system.quick_ring[0])
