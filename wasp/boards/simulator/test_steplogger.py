"""The step logger across a reset of the step counter."""

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
    logger._t = 0

    counter.steps = 120
    logger._tick()

    assert logger._data[0] == 120
