# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Miguel Rochefort
"""Play 2048
~~~~~~~~~~~~

A popular sliding block puzzle game in which tiles are combined to make the
number 2048.

    .. figure:: apps/play2048/screenshot.png
        :width: 179

        Screenshot of the 2048 game application
"""

import wasp
import icons
import widgets
import random
import fonts
from micropython import const

SCREEN_SIZE = const(240)

GRID_PADDING = const(8)
GRID_SIZE = const(4)
CELL_SIZE = const(50)

GRID_BACKGROUND = const(0x942F)
CELL_BACKGROUND = [0x9CB1, 0xEF3B, 0xEF19, 0xF58F, 0xF4AC, 0xF3EB, 0xF2E7, 0xEE6E, 0xEE6C, 0xEE4A, 0xEE27, 0xEE05]
CELL_FOREGROUND = [0x9CB1, 0x736C, 0x736C, 0xFFBE, 0xFFBE, 0xFFBE, 0xFFBE, 0xFFBE, 0xFFBE, 0xFFBE, 0xFFBE, 0xFFBE]
CELL_LABEL = ['','2','4','8','16','32','64','128','256','512','1K','2K'] # TODO: Display 1024 and 2048 (text-wrapping)

# 1-bit RLE, 32x32, generated from apps/play2048/icon.png, 75 bytes
icon = (
    32, 32,
    b'B\x1c\x03\x1e\x01D\n\x04\n\x08\n\x04\n\x08\n\x04'
    b'\n\x08\n\x04\n\x08\n\x04\n\x08\n\x04\n\x08\n\x04'
    b'\n\x08\n\x04\n\x88\n\x04\n\x08\n\x04\n\x08\n\x04'
    b'\n\x08\n\x04\n\x08\n\x04\n\x08\n\x04\n\x08\n\x04'
    b'\n\x08\n\x04\nD\x01\x1e\x03\x1cB'
)

class Play2048App():
    """Let's play the 2048 game."""
    NAME = '2048'
    ICON = icon

    def __init__(self):
        """Initialize the application."""
        self._board = None
        self._state = 0
        self._confirmation_view = None

    def foreground(self):
        """Activate the application."""
        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.SWIPE_UPDOWN |
                                  wasp.EventMask.SWIPE_LEFTRIGHT)

        self._state = 0

        if not self._board:
            self._start_game()

        self._draw()

    def touch(self,event):
        """Notify the application of a touchscreen touch event."""
        if self._state == 0:
            if not self._confirmation_view:
                self._confirmation_view = widgets.ConfirmationView()
            self._confirmation_view.draw('Restart game?')
            self._state = 1
        elif self._state == 1:
            if self._confirmation_view.touch(event):
                if self._confirmation_view.value:
                    self._start_game()
                self._draw()
                self._state = 0

    def swipe(self, event):
        """Notify the application of a touchscreen swipe event."""
        moved = False

        if self._state == 0:
            if event[0] == wasp.EventType.UP:
                moved = self._shift(1,False)
            elif event[0] == wasp.EventType.DOWN:
                moved = self._shift(-1,False)
            elif event[0] == wasp.EventType.LEFT:
                moved = self._shift(1,True)
            elif event[0] == wasp.EventType.RIGHT:
                moved = self._shift(-1,True)

        if moved:
            self._add_tile()

    def _draw(self):
        """Draw the display from scratch."""
        board = self._board
        draw = wasp.watch.drawable
        draw.fill(GRID_BACKGROUND)
        draw.set_font(fonts.sans24)
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                self._update(draw, board[y][x], y, x)

    def _update(self, draw, cell, row, col):
        """Update the specified cell of the application display."""
        x = GRID_PADDING + (col * (CELL_SIZE + GRID_PADDING))
        y = GRID_PADDING + (row * (CELL_SIZE + GRID_PADDING))
        draw.set_color(CELL_FOREGROUND[cell], CELL_BACKGROUND[cell])
        draw.fill(CELL_BACKGROUND[cell], x, y, CELL_SIZE, CELL_SIZE)
        draw.string(CELL_LABEL[cell], x, y + 16, CELL_SIZE)

    def _start_game(self):
        """Start a new game."""
        self._board = self._create_board()
        self._add_tile()
        self._add_tile()

    def _create_board(self):
        """Create an empty 4x4 board."""
        board = []
        for _ in range(GRID_SIZE):
            board.append([0] * GRID_SIZE)
        return board

    def _add_tile(self):
        """Add a new tile to a random empty location on the board."""
        board = self._board
        randint = random.randint
        y = randint(0, GRID_SIZE-1)
        x = randint(0, GRID_SIZE-1)
        while board[y][x] != 0:
            y = randint(0, GRID_SIZE-1)
            x = randint(0, GRID_SIZE-1)
        board[y][x] = 1
        self._update(wasp.watch.drawable,1,y,x)

    def _shift(self, direction, orientation):
        """Shift and merge the tiles vertically."""
        draw = wasp.watch.drawable
        update = self._update
        board = self._board
        moved = False

        def read(y, x):
            if not orientation:
                y,x = x,y
            return board[y][x]

        def write(y, x, v):
            if not orientation:
                y,x = x,y

            board[y][x] = v
            update(draw, v, y, x)

        if direction > 0:
            s = 0 + 1
            e = GRID_SIZE
        else:
            s = GRID_SIZE - 1 - 1
            e = 0 - 1

        for y in range(GRID_SIZE):
            p = s - direction
            for x in range(s,e,direction):
                a = read(y,x)
                b = read(y,p)
                if a != 0:
                    if a == b:
                        write(y, p, a + 1)
                        write(y, x, 0)
                        moved = True
                        p += direction
                    else:
                        if b != 0:
                            p += direction
                        if x != p:
                            write(y, p, a)
                            write(y, x, 0)
                            moved = True
        return moved
