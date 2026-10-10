# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2023 Tony Robinson

"""Four in a Row
~~~~~~~~~~~~~~~~
 
This is the classic two player board game called Four In A Row or Connect4.  You play against the computer.

.. figure:: apps/four_in_a_row/screenshot.png
    :width: 179

    Screenshot of Four In A Row

There is in intro/menu screen which has very brief instructions, allows you to set the opponent level and gives some stats on the number of games you have won.  Touching the screen sets the level from 0 to 6 which corresponds to the number of lookahead plies.  Swiping down enters the main game.  On your turn a red square counter will appear on the top row.  Touch the screen to move to the desired column, optionally touch again if you don't like your choice then swipe down to commit to playing that column.  The computer will reply with a yellow counter after a delay (dependent on level).  Your aim is to get four in a row before the computer does.  At end of game swipe down to return to the intro/menu screen.

This app is powered by a compact version of the Alpha Beta pruning algorithm.  For technical details see https://en.wikipedia.org/wiki/Connect_Four and https://kaggle.com/competitions/connectx/.  There isn't space for a transposition table in RAM, so MTDf isn't implmented, nevertheless it can play a challenging game.

"""

import wasp, array
import cards
import fonts
from micropython import const

# parameters of the 'Four in a Row' game
_NROW    = const(6)
_NCOLUMN = const(7)
# assert _NCOLUMN == _NROW + 1 # need square, top row is where counters are placed
_NMIDDLE = const((_NCOLUMN - 1) // 2)
_NBOARD  = const(_NROW * _NCOLUMN)

# colours
_BLUE  = const(0x0010) # Blue: half way to full blue
_BLACK = const(0x0000) # Black
_cPLAY = const(0xF800) # Red: colour for human PLAYer - becuase I like playing red
_cCOMP = const(0xFFE0) # Yellow: colour for COMPputer pieces

# basics of the display
_NPIXEL  = const(240)
_NCELL   = const(_NPIXEL // _NCOLUMN)
_NBORDER = const((_NPIXEL - _NCELL * _NCOLUMN) // 2)
_NPAD    = const(2)

# states of game
_INTRO, _PLAY, _GAMEOVER = const(0), const(1), const(2)
_NLEVEL = const(7)

# The menu is three stacked cards: the title, the level picker and the score.
_MENU_H = cards.size(3)
_MENU_Y = cards.edges((_MENU_H,) * 3)
# The level picker holds one pill per level inside its card.
_PILL_W = const(28)
_PILL_H = const(43)
_PILL_PITCH = const(31)
_PILL_X0 = const(13)
# The result card sits over the row the counter is chosen in.
_RESULT_Y = const(2)
_RESULT_H = const(30)

def _gameOver(bitmap):
    for s in [1, _NCOLUMN, _NCOLUMN+2, _NCOLUMN+1]:
        b = bitmap & (bitmap >> s)
        if b & (b >> 2 * s):
            return True
    return False

def _bitmapGet(bitmap, x, y):
    return (bitmap >> (y * (_NCOLUMN + 1) + x)) & 1

def _bitmapSet(bitmap, x, y):
    return bitmap | 1 << (y * (_NCOLUMN + 1) + x)

_searchOrder = bytearray(sorted(range(_NCOLUMN), key=lambda x:abs(x - _NMIDDLE)))

def _swapmin(bitNext, bitLast, low, depth, lob, upb):
    sumLow = sum(low)

    # list all the legal moves
    legal = [ n for n in _searchOrder if low[n] != _NROW ]
    
    # see if we can win                                                           
    for x in legal:
        if _gameOver(_bitmapSet(bitNext, x, low[x])):
            return (_NBOARD - sumLow + 1) // 2, x 

    # easy wins done, quit now if at search depth or end of board
    if depth == 0 or sumLow == _NBOARD:
        return 0, -1 # -1 is not right but DRAW will catch it

    # if can't win then see if we have to block                                                                     
    for x in legal:
        if _gameOver(_bitmapSet(bitLast, x, low[x])):
            legal = [ x ]
            break

    bestv = _NBOARD
    for x in legal:
        lowp = bytearray(low) # bytearray used as copy.copy()
        lowp[x] += 1
        v, _ = _swapmin(bitLast, _bitmapSet(bitNext, x, low[x]), lowp, depth-1, -upb, -lob)
        if v < bestv:
            bestv, bestx = v, x
            upb = min(upb, bestv)
            if bestv <= lob:
                break

    return -bestv, bestx

def rndColumn():
    return int(wasp.watch.rtc.uptime) % _NCOLUMN  # time used as RNG to save space

# 1-bit RLE, 32x32, generated from apps/four_in_a_row/icon.png, 75 bytes
icon = (
    32, 32,
    b'\x0c\x08\x15\x0e\x10\x12\r\x14\x0b\x16\t\x18\x07\x1a\x05\x1c'
    b'\x04\x1c\x03\x1e\x02\r\x04\r\x02\x0b\x08\x0b\x01\x0b\n\x16'
    b'\n\x15\x0c\x14\x0c\x14\x0c\x14\x0c\x15\n\x16\n\x0b\x01\x0b'
    b'\x08\x0b\x02\r\x04\r\x02\x1e\x03\x1c\x04\x1c\x05\x1a\x07\x18'
    b'\t\x16\x0b\x14\r\x12\x10\x0e\x15\x08\x0c'
)

class FourInARowApp():
    NAME = '4 ina row'
    ICON = icon

    def __init__(self):
        self.screen = _INTRO
        self.level = 0
        self.nwin  = array.array('H', [0] * _NLEVEL)
        self.ngame = array.array('H', [0] * _NLEVEL)

    def _showLevel(self):
        draw = wasp.watch.drawable
        y = _MENU_Y[1]
        draw.rounded_rect(cards.MARGIN, y, cards.SPAN, _MENU_H, cards.COLOR)
        draw.set_font(fonts.sans24)
        y += (_MENU_H - _PILL_H) // 2
        for i in range(_NLEVEL):
            x = _PILL_X0 + i * _PILL_PITCH
            if i == self.level:
                bg = wasp.system.theme('ui')
                draw.rounded_rect(x, y, _PILL_W, _PILL_H, bg, cards.COLOR)
                draw.set_color(wasp.system.theme('bright'), bg)
            else:
                draw.set_color(wasp.system.theme('mid'), cards.COLOR)
            label = str(i)
            w = draw.bounding_box(label)[0]
            draw.string(label, x + (_PILL_W - w) // 2, y + (_PILL_H - 24) // 2)

    def _showStats(self):
        draw = wasp.watch.drawable
        nwin  = self.nwin[self.level]
        ngame = self.ngame[self.level]
        pc = int(100 * nwin / ngame + 0.5) if ngame > 0 else 0
        y = _MENU_Y[2]
        draw.rounded_rect(cards.MARGIN, y, cards.SPAN, _MENU_H, cards.COLOR)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans24)
        draw.string('Won %d%%' % pc, cards.MARGIN + 12, y + 14, width=cards.SPAN - 24)
        draw.set_color(wasp.system.theme('mid'), cards.COLOR)
        draw.set_font(fonts.sans18)
        draw.string('at level %d' % self.level, cards.MARGIN + 12, y + 44, width=cards.SPAN - 24)

    def _showResult(self, message):
        draw = wasp.watch.drawable
        draw.rounded_rect(cards.MARGIN, _RESULT_Y, cards.SPAN, _RESULT_H, cards.COLOR)
        draw.set_color(wasp.system.theme('bright'), cards.COLOR)
        draw.set_font(fonts.sans24)
        w = draw.bounding_box(message)[0]
        draw.string(message, (_NPIXEL - w) // 2, _RESULT_Y + (_RESULT_H - 24) // 2)

    def _place(self, x, y, colour):
        wasp.watch.drawable.fill(x=_NBORDER + x*_NCELL + _NPAD, y=_NBORDER + (_NROW-y)*_NCELL + _NPAD, w=_NCELL - 2*_NPAD, h=_NCELL - 2*_NPAD, bg=colour)

    def foreground(self):
        draw = wasp.watch.drawable

        # draw board from state
        draw.fill(0)
        if self.screen == _INTRO:
            y = _MENU_Y[0]
            draw.rounded_rect(cards.MARGIN, y, cards.SPAN, _MENU_H, cards.COLOR)
            draw.set_color(wasp.system.theme('bright'), cards.COLOR)
            draw.set_font(fonts.sans24)
            draw.string('Four in a Row', cards.MARGIN + 12, y + 14, width=cards.SPAN - 24)
            draw.set_color(wasp.system.theme('mid'), cards.COLOR)
            draw.set_font(fonts.sans18)
            draw.string('Swipe down to play', cards.MARGIN + 12, y + 44, width=cards.SPAN - 24)
            self._showLevel()
            self._showStats()
        else:
            draw.fill(x=0, y=_NBORDER+_NCELL, w=_NPIXEL, h=_NPIXEL-_NCELL, bg=_BLUE)
            for x in range(_NCOLUMN):
                for y in range(_NROW):
                    if _bitmapGet(self.bPLAY, x, y):
                        self._place(x, y, _cPLAY)
                    elif _bitmapGet(self.bCOMP, x, y):
                        self._place(x, y, _cCOMP)
            self._place(self.x, _NROW, _cPLAY)

        wasp.system.request_event(wasp.EventMask.TOUCH | wasp.EventMask.SWIPE_UPDOWN)

    # touch to set the drop column
    def touch(self, event):
        if self.screen == _INTRO:
            # The x position picks the level, as a slider would.
            self.level = min(max((event[1] - _PILL_X0) // _PILL_PITCH, 0), _NLEVEL - 1)
            self._showLevel()
            self._showStats()
        elif self.screen == _PLAY:
            self._place(self.x, _NROW, _BLACK)
            self.x = min(max((event[1] - _NBORDER) // _NCELL, 0), _NCOLUMN-1)
            self._place(self.x, _NROW, _cPLAY)

    def _drop(self, x, colour):
        if self.low[x] == _NROW:
            wasp.watch.vibrator.pulse() # can't move here!
        else:
            y = self.low[x]
            for i in range(_NROW, y, -1):
                self._place(x, i-1, colour)
                self._place(x, i, _BLUE if i != _NROW else _BLACK)
                wasp.watch.time.sleep(0.1)
            if colour == _cPLAY:
                self.bPLAY = _bitmapSet(self.bPLAY, x, y)
            else:
                self.bCOMP = _bitmapSet(self.bCOMP, x, y)
            self.low[x] += 1

    # swipe down to drop, swipe left/right to exit
    def swipe(self, event):
        if event[0] == wasp.EventType.DOWN:
            if self.screen == _INTRO:
                self.x = _NMIDDLE
                self.bPLAY = 0
                self.bCOMP = 0
                self.low   = bytearray(_NCOLUMN)
                self.screen = _PLAY
                self.foreground()
                if self.ngame[self.level] % 2:
                    self._drop(rndColumn(), _cCOMP)
            elif self.screen == _PLAY and self.low[self.x] != _NROW:
                # play human PLAYer
                self._drop(self.x, _cPLAY)
                if _gameOver(self.bPLAY):
                    self._showResult('You win!')
                    self.nwin[self.level] += 1
                    self.screen = _GAMEOVER
                    return

                if sum(self.low) < 3:
                    x = rndColumn()
                else:
                    depth = self.level + 1
                    if depth == 2 and sum(self.low) < 8:
                        depth += 1
                    v, x = _swapmin(self.bCOMP, self.bPLAY, self.low, depth, -_NBOARD, _NBOARD)
                self._drop(x, _cCOMP)
                    
                if _gameOver(self.bCOMP):
                    self._showResult('You lose!')
                    self.screen = _GAMEOVER
                    return

                self._place(self.x, _NROW, _cPLAY)
            elif self.screen == _GAMEOVER:
                self.ngame[self.level] += 1
                self.screen = _INTRO
                self.foreground()
