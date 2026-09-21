# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2026 Daniel Thompson

"""Register level tests for the ST7789 driver."""

import time

# The driver expects the MicroPython flavour of sleep, which the board files
# normally add for us.
if not hasattr(time, 'sleep_ms'):
    time.sleep_ms = lambda ms: None

import pytest

from drivers.st7789 import ST7789_SPI

VSCRDEF = 0x33
VSCSAD = 0x37

class FakePin:
    def __init__(self):
        self.OUT = 'out'

    def init(self, *args, **kwargs):
        pass

    def value(self, v=None):
        pass

class FakeSPI:
    """Record everything the driver puts on the bus."""
    def __init__(self):
        self.traffic = []

    def write(self, buf):
        self.traffic.append(bytes(buf))

@pytest.fixture
def spi():
    return FakeSPI()

@pytest.fixture
def display(spi):
    d = ST7789_SPI(240, 240, spi, FakePin(), FakePin())
    spi.traffic.clear()
    return d

def transfer_after(spi, cmd):
    """Return the data that followed the last time cmd was sent."""
    for i in range(len(spi.traffic) - 1, -1, -1):
        if spi.traffic[i] == bytes((cmd,)):
            return spi.traffic[i+1]
    raise AssertionError(f'command 0x{cmd:02x} was never sent')

def test_scroll_area_defaults_to_everything(display, spi):
    display.set_scroll_area()

    assert transfer_after(spi, VSCRDEF) \
            == b'\x00\x00\x01\x40\x00\x00'

def test_scroll_area_splits_320_rows(display, spi):
    display.set_scroll_area(top_fixed=40, bottom_fixed=24)

    # The three areas must add up to the 320 rows the controller has.
    assert transfer_after(spi, VSCRDEF) \
            == b'\x00\x28\x01\x00\x00\x18'

def test_scroll_sends_a_two_byte_row(display, spi):
    display.scroll(300)

    assert transfer_after(spi, VSCSAD) == b'\x01\x2c'

def test_scroll_allocates_nothing(display):
    """An animation frame must not build a new buffer every time."""
    display.scroll(0)
    first = display.scroll_addr

    display.scroll(240)

    assert display.scroll_addr is first
    assert bytes(first) == b'\x00\xf0'
