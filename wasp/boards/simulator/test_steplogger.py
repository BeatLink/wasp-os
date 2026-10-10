"""The step logger across a reset of the step counter."""

import time

import wasp
from apps.system import steplogger


class Counter:
    """An accelerometer whose count a test sets directly."""
    steps = 0


class Manager:
    def set_alarm(self, when, action):
        pass


def test_a_reset_counter_logs_its_new_steps_not_a_huge_number(monkeypatch):
    counter = Counter()
    monkeypatch.setattr(wasp.watch, 'accel', counter)
    counter.steps = 500
    logger = steplogger.StepLogger(Manager())
    # Start the tick at the beginning of a dump period, so it records without writing the flash.
    logger._t = int(time.mktime((2026, 10, 10, 0, 0, 0, 0, 0, 0)))

    counter.steps = 120
    logger._tick()

    assert logger._data[0] == 120


import os

import pytest


@pytest.fixture
def logger(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    counter = Counter()
    monkeypatch.setattr(wasp.watch, 'accel', counter)
    logger = steplogger.StepLogger(Manager())
    # Keep the ticks this test causes off the real scheduler.
    monkeypatch.setattr(wasp.system, 'set_alarm', lambda when, action: None)
    return (logger, counter)


def _at(hour, minute=0):
    return int(time.mktime((2026, 10, 10, hour, minute, 0, 0, 0, 0)))


def test_the_count_starts_again_at_midnight(logger):
    (logger, counter) = logger
    logger._t = _at(23, 54)
    logger._steps = 9000
    counter.steps = 9500

    logger._tick()

    assert counter.steps == 0
    assert logger._steps == 0
    # The last steps of the day are still logged against it.
    assert list(logger.data(_at(12)))[-1] == 500


def test_a_tick_in_the_day_leaves_the_count_alone(logger):
    (logger, counter) = logger
    logger._t = _at(10, 6)
    counter.steps = 300

    logger._tick()

    assert counter.steps == 300


def test_today_has_data_before_anything_is_written(logger):
    (logger, counter) = logger
    logger._t = _at(1, 0)
    logger._steps = 0
    counter.steps = 42

    data = list(logger.data(_at(1, 0)))

    assert len(data) == 240
    assert data[10] == 42
    assert sum(data) == 42


def test_reading_today_after_a_reset_neither_fails_nor_changes_the_log(logger):
    (logger, counter) = logger
    logger._t = _at(1, 0)
    logger._steps = 500
    counter.steps = 20

    data = list(logger.data(_at(1, 0)))

    assert data[10] == 20
    assert list(logger._data) == [0] * steplogger.DUMP_LENGTH


def test_todays_counts_in_ram_follow_a_gap_in_the_log(logger):
    (logger, counter) = logger
    # Nothing was logged before 06:00, when the watch started again.
    logger._t = _at(6, 6)
    logger._steps = 0
    counter.steps = 7
    logger._data[0] = 3
    os.mkdir('logs/2026')
    with open('logs/2026/10-10.steps', 'wb') as f:
        f.write(b'\x05\x00')

    data = list(logger.data(_at(6)))

    assert data[0] == 5
    assert data[1:60] == [0] * 59
    assert data[60:62] == [3, 7]


def test_a_dump_written_again_lands_in_its_place(logger):
    (logger, counter) = logger
    for _ in range(2):
        # The last tick of the first dump of the day, so it writes the flash.
        logger._t = _at(2, 54)
        logger._steps = 0
        counter.steps = 11
        logger._tick()

    with open('logs/2026/10-10.steps', 'rb') as f:
        log = f.read()
    assert len(log) == steplogger.DUMP_LENGTH * 2
    assert log[-2:] == b'\x0b\x00'
