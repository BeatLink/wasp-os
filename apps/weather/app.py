# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson
# Copyright (C) 2020 Carlos Gil

"""Weather for GadgetBridge and wasp-os companion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. figure:: apps/weather/screenshot.png
        :width: 179

        Screenshot of the Weather application

The place, temperature and sky sit on the top card, with the wind and the
humidity on two cards below it.
"""

import wasp
import cards
import fonts

from micropython import const

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

# A wide card over two square ones.
_HALF = cards.size(2)
_TOP_Y, _LOW_Y = cards.edges((_HALF, _HALF))
_LOW_X = cards.edges((_HALF, _HALF))
# Text keeps clear of the rounded corners of its card.
_INSET = const(12)

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
        self._data_shown = False

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
        wasp.watch.drawable.fill(0)
        self._data_shown = self._temp != -1
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
        """Redraw the cards whose contents changed."""
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
            if not self._data_shown:
                # Coming from the empty page, every card has to be drawn.
                wasp.watch.drawable.fill(0)
                self._data_shown = True
                self._temp_changed = True
                self._hum_changed = True
                self._txt_changed = True
                self._wind_changed = True
                self._loc_changed = True
            if self._temp_changed or self._txt_changed or self._loc_changed:
                self._draw_main(str(temp))
            if self._wind_changed:
                self._draw_value(0, "Wind", str(wind), wind_units)
            if self._hum_changed:
                self._draw_value(1, "Humidity", str(self._hum), "%")
        elif self._temp_changed:
            draw = wasp.watch.drawable
            draw.fill(0)
            draw.rounded_rect(cards.MARGIN, cards.MARGIN, cards.SPAN,
                              cards.SPAN, cards.COLOR)
            draw.set_font(fonts.sans24)
            draw.set_color(wasp.system.theme('mid'), cards.COLOR)
            draw.string("No weather data.", cards.MARGIN + _INSET, 108,
                        width=cards.SPAN - 2 * _INSET)
            self._data_shown = False

    def _draw_main(self, temp):
        """Draw the place, the temperature and the sky on the top card."""
        draw = wasp.watch.drawable
        draw.rounded_rect(cards.MARGIN, _TOP_Y, cards.SPAN, _HALF, cards.COLOR)
        x = cards.MARGIN + _INSET
        w = cards.SPAN - 2 * _INSET
        draw.set_font(fonts.sans18)
        draw.set_color(wasp.system.theme('mid'), cards.COLOR)
        draw.string(self._fit(self._loc, w), x, _TOP_Y + 12, width=w)
        draw.set_font(fonts.sans36)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.string(temp, x, _TOP_Y + 36, width=w)
        draw.set_font(fonts.sans18)
        draw.string(self._fit(self._txt, w), x, _TOP_Y + _HALF - 30, width=w)

    def _draw_value(self, col, label, value, unit):
        """Draw a label, a large value and its unit on one of the lower cards."""
        draw = wasp.watch.drawable
        x = _LOW_X[col]
        draw.rounded_rect(x, _LOW_Y, _HALF, _HALF, cards.COLOR)
        x += _INSET
        w = _HALF - 2 * _INSET
        draw.set_font(fonts.sans18)
        draw.set_color(wasp.system.theme('mid'), cards.COLOR)
        draw.string(label, x, _LOW_Y + 12, width=w)
        draw.string(unit, x, _LOW_Y + _HALF - 30, width=w)
        draw.set_font(fonts.sans36)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.string(value, x, _LOW_Y + 39, width=w)

    def _fit(self, text, width):
        """Return as much of the text as fits on one line."""
        if not text:
            return ''
        return text[:wasp.watch.drawable.wrap(text, width)[1]].rstrip()

    def _update(self):
        self._draw()

    def update(self):
        pass
