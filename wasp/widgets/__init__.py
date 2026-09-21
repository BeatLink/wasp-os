# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Widget library
~~~~~~~~~~~~~~~~~

The widget library allows common fragments of logic and drawing code to be
shared between applications.

Each widget lives in its own module so an application that only needs one
widget can import that module alone and keep the rest out of RAM. Importing
the package brings every widget into the widgets namespace.
"""

from widgets.battery_meter import BatteryMeter
from widgets.clock import Clock
from widgets.notification_bar import NotificationBar
from widgets.status_bar import StatusBar
from widgets.scroll_indicator import ScrollIndicator
from widgets.button import Button
from widgets.togglebutton import ToggleButton
from widgets.checkbox import Checkbox
from widgets.gfxbutton import GfxButton
from widgets.slider import Slider
from widgets.spinner import Spinner
from widgets.stopwatch import Stopwatch
from widgets.confirmation_view import ConfirmationView
from widgets.page import bounds, scroll_in, draw_indicator
