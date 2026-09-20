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
import machine
import ppg

# 1-bit RLE, 48x48, generated from apps/heart/icon.png, 131 bytes
icon = (
    48, 48,
    b'\x9a\x06\x10\x06\x12\x0b\n\x0b\x0e\x0f\x06\x0f\x0b\x11\x04\x11'
    b'\t\x13\x02\x13\x07*\x05,\x03.\x02.\x02.\x01\x10'
    b'\x03,\x05+\x05*\x06\x08\x04\x1e\x07\x07\x04\x1d\x08\x06'
    b'\x06\x1c\t\x05\x06\x1b\n\x04\x08\x0e\x01\x0b\x05\x01\x05\x03'
    b"\t\x0c\x12\x01\x05\x02'\x03\x05\x01&\x04\n\x02\x1f\x06"
    b'\t\x03\x14\x10\x08\x10\t\x0f\x08\x0f\x0b\x0f\x06\x0f\r\x0e'
    b'\x06\x0e\x0f\x0e\x04\x0e\x11\x0e\x02\x0e\x13\x1c\x15\x1a\x17\x18'
    b"\x19\x16\x1b\x14\x1e\x11 \x0e#\x0c%\n'\x08)\x06"
    b'+\x04\xd6'
)

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
        draw.fill()
        draw.set_color(wasp.system.theme('bright'))
        draw.string('PPG graph', 0, 6, width=240)

        wasp.system.request_tick(1000 // 8)

        self._hrdata = ppg.PPG(wasp.watch.hrs.read_hrs())
        if self._debug:
            self._hrdata.enable_debug()
        self._x = 0

    def background(self):
        wasp.watch.hrs.disable()
        self._hrdata = None

    def _subtick(self, ticks):
        """Notify the application that its periodic tick is due."""
        draw = wasp.watch.drawable

        spl = self._hrdata.preprocess(wasp.watch.hrs.read_hrs())

        if len(self._hrdata.data) >= 240:
            draw.set_color(wasp.system.theme('bright'))
            draw.string('{} bpm'.format(self._hrdata.get_heart_rate()),
                        0, 6, width=240)

        # Graph is orange by default...
        color = wasp.system.theme('spot1')

        # If the maths goes wrong lets show it in the chart!
        if spl > 100 or spl < -100:
            color = 0xffff
        if spl > 104 or spl < -104:
            spl = 0
        spl += 104

        x = self._x
        draw.fill(0, x, 32, 1, 208-spl)
        draw.fill(color, x, 239-spl, 1, spl)
        if x < 238:
            draw.fill(0, x+1, 32, 2, 208)
        x += 2
        if x >= 240:
            x = 0
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
