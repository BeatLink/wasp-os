# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson
# Copyright (C) 2020 Carlos Gil

"""Weather for GadgetBridge and wasp-os companion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. figure:: apps/weather/screenshot.png
        :width: 179

        Screenshot of the Weather application

"""

import wasp

import icons
import time
import fonts.sans36

# 1-bit RLE, 32x32, generated from apps/weather/icon.png, 99 bytes
icon = (
    32, 32,
    b'f\x01\x06\x02\x16\x04\x03\x03\x16\n\x16\x0b\x15\x0b\x12\x11'
    b'\r\x08\x05\x08\x0b\x07\x02\x02\x03\x06\r\x05\x02\x05\x02\x05'
    b'\x0e\x04\x01\x06\x02\x04\x0f\x04\x01\x07\x14\x04\x01\x06\x04\x02'
    b'\x0e\x05\x02\x05\x02\x06\x0c\x06\x02\x03\x02\r\x05\x08\x06\x0e'
    b'\x05\t\x04\x0e\t\x05\x03\x10\x08\x04\x02\x12\x08\x04\x01\x14'
    b'\x07\x03\x02\x15\x07\x02\x02\x16\n\x16\n\x16\n\x16\x0b\x14'
    b'\r\x12b'
)

class WeatherApp(object):
    """ Weather application."""
    NAME = 'Weather'
    ICON = icon
    
    def __init__(self):
        self._temp = -1
        self._hum = 0
        self._txt = ''
        self._wind = 0
        self._loc = ''
        self._temp_changed = True
        self._hum_changed = True
        self._txt_changed = True
        self._wind_changed = True
        self._loc_changed = True

    def foreground(self):
        """Activate the application."""
        get_info = wasp.system.weatherinfo.get
        temp = get_info('temp')
        hum = get_info('hum')
        txt = get_info('txt')
        wind = get_info('wind')
        loc = get_info('loc')
        if temp:
            self._temp = temp
        if hum:
            self._hum = hum
        if txt:
            self._txt = txt
        if wind:
            self._wind = wind
        if loc:
            self._loc = loc
        wasp.watch.drawable.fill()
        self.draw()
        wasp.system.request_tick(1000)

    def background(self):
        """De-activate the application (without losing state)."""
        self._temp_changed = True
        self._hum_changed = True
        self._txt_changed = True
        self._wind_changed = True
        self._loc_changed = True

    def tick(self, ticks):
        wasp.system.keep_awake()
        get_info = wasp.system.weatherinfo.get
        temp_now = get_info('temp')
        hum_now = get_info('hum')
        txt_now = get_info('txt')
        wind_now = get_info('wind')
        loc_now = get_info('loc')
        if temp_now:
            if temp_now != self._temp:
                self._temp = temp_now
                self._temp_changed = True
        else:
            self._temp_changed = False
        if hum_now:
            if hum_now != self._hum:
                self._hum = hum_now
                self._hum_changed = True
        else:
            self._hum_changed = False
        if txt_now:
            if txt_now != self._txt:
                self._txt = txt_now
                self._txt_changed = True
        else:
            self._txt_changed = False
        if wind_now:
            if wind_now != self._wind:
                self._wind = wind_now
                self._wind_changed = True
        else:
            self._wind_changed = False
        if loc_now:
            if loc_now != self._loc:
                self._loc = loc_now
                self._loc_changed = True
        else:
            self._loc_changed = False
        wasp.system.weatherinfo = {}
        self._update()

    def draw(self):
        """Redraw the display from scratch."""
        self._draw()

    def _draw(self):
        """Redraw the updated zones."""
        draw = wasp.watch.drawable
        if self._temp != -1:
            units = wasp.system.units
            temp = self._temp - 273.15
            wind = self._wind
            wind_units = "km/h"
            if units == "Imperial":
                temp = (temp * 1.8) + 32
                wind = wind / 1.609
                wind_units = "mph"
            temp = round(temp)
            wind = round(wind)
            if self._temp_changed:
                self._draw_label(str(temp), 54, 36)
            if self._hum_changed:
                self._draw_label("Humidity: {}%".format(self._hum), 160)
            if self._txt_changed:
                self._draw_label(self._txt, 12)
            if self._wind_changed:
                self._draw_label("Wind: {}{}".format(wind, wind_units), 120)
            if self._loc_changed:
                self._draw_label(self._loc, 200)
        else:
            if self._temp_changed:
                draw.fill()
                self._draw_label("No weather data.", 120)

    def _draw_label(self, label, pos, size = 24):
        """Redraw label info"""
        if label:
            draw = wasp.watch.drawable
            draw.reset()
            if size == 36:
                draw.set_font(fonts.sans36)
            
            draw.string(label, 0, pos, 240)

    def _update(self):
        self._draw()

    def update(self):
        pass
