# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Heart rate monitor
~~~~~~~~~~~~~~~~~~~~~

A graphing heart rate monitor using a PPG sensor.

.. figure:: apps/heart/screenshot.png
    :width: 179

This program also implements some (entirely optional) debug features to
store the raw heart data to the filesystem so that the samples can be used
to further refine the heart rate detection algorithm.

To enable the logging feature select the heart rate application using the
watch UI and then run the following command via wasptool:

.. code-block:: sh

    ./tools/wasptool --eval 'wasp.system.app.debug = True'

Once debug has been enabled then the watch will automatically log heart
rate data whenever the heart rate application is running (and only
when it is running). Setting the debug flag to False will disable the
logging when the heart rate monitor next exits.

Finally to download the logs for analysis try:

.. code-block:: sh

    ./tools/wasptool --pull hrs.data
"""

import wasp
import cards
import fonts
import machine
import ppg

# 1-bit RLE, 32x32, generated from apps/heart/icon.png, 87 bytes
icon = (
    32, 32,
    b'F\x05\n\x05\n\n\x04\n\x07\x0c\x02\x0c\x05\x1c\x03\x1e'
    b'\x02\x1e\x01*\x03\x1d\x03\x1c\x05\x05\x02\x14\x05\x04\x04\x13'
    b'\x06\x03\x04\n\x01\x07\x07\x02\x06\x08\x0c\x01\x03\x02\x19\x03'
    b'\x07\x01\x14\x04\x06\x03\r\x0b\x05\n\x07\n\x04\n\t\t'
    b'\x04\t\x0b\t\x02\t\r\x12\x0f\x10\x11\x0e\x13\x0c\x15\n'
    b'\x17\x08\x19\x06\x1b\x04N'
)

# A short card with the reading above a tall card with the graph.
_HEAD_H = cards.size(4)
_GRAPH_Y = cards.edges((_HEAD_H, cards.SPAN - _HEAD_H - cards.GAP))[1]
_CARD_H = cards.SPAN + cards.MARGIN - _GRAPH_Y
# The graph keeps clear of the rounded corners at the top and bottom.
_PLOT_Y = _GRAPH_Y + 12
_PLOT_H = _CARD_H - 24
_PLOT_END = cards.MARGIN + cards.SPAN
_TEXT_Y = cards.MARGIN + (_HEAD_H - 24) // 2

class HeartApp():
    """Heart rate monitor application."""
    NAME = 'Heart'
    ICON = icon

    def __init__(self):
        self._debug = False
        self._hrdata = None

    def foreground(self):
        """Activate the application."""
        wasp.watch.hrs.enable()

        # There is no delay after the enable because the redraw should
        # take long enough it is not needed
        draw = wasp.watch.drawable
        draw.fill(0)
        draw.rounded_rect(cards.MARGIN, cards.MARGIN, cards.SPAN, _HEAD_H,
                          cards.COLOR)
        draw.rleblit(icon, (cards.MARGIN + 12, cards.MARGIN + (_HEAD_H - 32) // 2),
                     wasp.system.theme('bright'), cards.COLOR)
        draw.rounded_rect(cards.MARGIN, _GRAPH_Y, cards.SPAN, _CARD_H,
                          cards.COLOR)
        self._reading('PPG graph')

        wasp.system.request_tick(1000 // 8)

        self._hrdata = ppg.PPG(wasp.watch.hrs.read_hrs())
        if self._debug:
            self._hrdata.enable_debug()
        self._x = cards.MARGIN

    def background(self):
        wasp.watch.hrs.disable()
        self._hrdata = None

    def _reading(self, text):
        """Show a line of text on the top card beside the heart."""
        draw = wasp.watch.drawable
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans24)
        draw.string(text, 56, _TEXT_Y, width=164)

    def _subtick(self, ticks):
        """Notify the application that its periodic tick is due."""
        draw = wasp.watch.drawable

        spl = self._hrdata.preprocess(wasp.watch.hrs.read_hrs())

        if len(self._hrdata.data) >= 240:
            self._reading('{} bpm'.format(self._hrdata.get_heart_rate()))

        # Graph is orange by default...
        color = wasp.system.theme('spot1')

        # If the maths goes wrong lets show it in the chart!
        if spl > 100 or spl < -100:
            color = 0xffff
        if spl > 104 or spl < -104:
            spl = 0
        spl = (spl + 104) * _PLOT_H // 208

        x = self._x
        draw.fill(cards.COLOR, x, _PLOT_Y, 1, _PLOT_H - spl)
        draw.fill(color, x, _PLOT_Y + _PLOT_H - spl, 1, spl)
        if x < _PLOT_END - 2:
            draw.fill(cards.COLOR, x + 1, _PLOT_Y, 2, _PLOT_H)
        x += 2
        if x >= _PLOT_END:
            x = cards.MARGIN
        self._x = x

    def tick(self, ticks):
        """This is an outrageous hack but, at present, the RTC can only
        wake us up every 125ms so we implement sub-ticks using a regular
        timer to ensure we can read the sensor at 24Hz.
        """
        t = machine.Timer(id=1, period=8000000)
        t.start()
        self._subtick(1)
        wasp.system.keep_awake()

        while t.time() < 41666:
            pass
        self._subtick(1)

        while t.time() < 83332:
            pass
        self._subtick(1)

        t.stop()
        del t

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value):
        self._debug = value
        if value and self._hrdata:
            self._hrdata.enable_debug()
