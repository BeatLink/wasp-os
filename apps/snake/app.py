# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Johannes Wache

"""Snake Game
~~~~~~~~~~~~~

This is a classic arcade game called snake.

.. figure:: apps/snake/screenshot.png
    :width: 179

    Screenshot of the snake game

You have to direct the white snake to the food block (blue dot) by swiping in the desired direction. You must not hit the border or the snake's body itself.
Every time the snake eats the food, its length increases by 1. (In the current version there is an error that the length of the snake is not increased by 1 when the snake gets the food for the first time. This has to be fixed).

Once the game is over, you can try again by tapping on the screen and then swipe in the direction you want to move. If you want to leave the game, simply wipe in any direction once the game is over.

And now: Have fun playing! :)
"""

# 1-bit RLE, 48x48, generated from apps/snake/icon.png, 201 bytes
snake_icon = (
    48, 48,
    b'\x1e\t%\r"\x10\x1f\x11\x1e\x13\x1d\x13\x1c\n\x03\x08'
    b'\x1b\t\x04\x08\x1b\t\x04\x08\x1b\t\x04\x08\x1b\x15\x1b\x15'
    b'\x1c\x14\x1c\x14\x1d\x13\x0f\x07\x08\x12\r\x0c\x06\x11\x0b\x0f'
    b'\x07\x0f\n\x11\x0c\t\t\x13\x0b\t\x08\x15\n\t\x08\x16'
    b'\t\t\x07\x17\t\t\x07\x18\x08\t\x06\x0b\x04\n\x08\t'
    b'\x06\n\x06\t\x08\t\x06\t\x07\t\x08\t\x06\t\x07\t'
    b'\x08\t\x06\t\x07\n\x07\t\x06\t\x07\n\x07\t\x06\t'
    b'\x07\n\x07\t\x06\t\x07\n\x07\t\x06\t\x07\n\x07\t'
    b'\x06\t\x07\n\x07\t\x06\t\x07\n\x07\t\x06\t\x08\t'
    b'\x07\t\x06\t\x08\t\x07\t\x06\t\x08\t\x06\n\x06\t'
    b'\x08\n\x04\x0b\x06\t\x08\x18\x07\t\t\x17\x07\t\t\x16'
    b'\x08\t\n\x15\x08\t\x0b\x13\t\t\x0c\x11\n\x08\x0e\x0f'
    b'\x0c\x07\x0f\x0c\x0f\x05\x13\x07\x0c'
)

import wasp, time
from random import randint

class SnakeApp():
    NAME = 'Snake'
    ICON = snake_icon

    def __init__(self):
        self.running = True
        self.snake = Snake()
        self.food_location()
        self.highscore = 1


    def foreground(self):
        """Activate the application."""
        wasp.watch.drawable.fill()
        if self.running:
            self.update()
        else: 
            self.snake.show()
            wasp.watch.drawable.fill(x=self.food[0],y=self.food[1],w=15,h=15,bg=0x00ff)
        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.SWIPE_UPDOWN |
                                  wasp.EventMask.SWIPE_LEFTRIGHT)
        wasp.system.request_tick(250)

    def touch(self,event):
        if not self.running:
            self.running = True
            wasp.watch.drawable.fill()

    def swipe(self, event):
      if self.running:
        """Notify the application of a touchscreen swipe event."""
        if event[0] == wasp.EventType.UP:
            self.snake.set_dir(0,-15)
        elif event[0] == wasp.EventType.DOWN:
            self.snake.set_dir(0,15)
        elif event[0] == wasp.EventType.LEFT:
            self.snake.set_dir(-15,0)
        elif event[0] == wasp.EventType.RIGHT:
            self.snake.set_dir(15,0)
      else:
        return True

    def tick(self, ticks):
        """Notify the application that its periodic tick is due."""
        self.update()

    def food_location(self):
        x = randint(0,15) * 15
        y = randint(0,15) * 15
        self.food = [x,y]

    def update(self):
        draw = wasp.watch.drawable
        """Draw the display from scratch."""

        if (self.snake.eat(self.food)):
            self.food_location()
        self.snake.update()
        if (self.snake.end_game()):
                if len(self.snake.body) > self.highscore:
                    self.highscore = len(self.snake.body)
                self.running = False
                wasp.watch.vibrator.pulse()
                self.snake = Snake()
                draw.fill()
                draw.set_color(0xf000)
                draw.string('GAME', 0, 60, width=240)
                draw.string('OVER', 0, 98, width=240)
                draw.string('Highscore: '+str(self.highscore-1),0,180,width=240)
                draw.reset()
                return True
        if self.running:
            self.snake.show()
            draw.fill(x=self.food[0],y=self.food[1],w=15,h=15,bg=0x00ff)
        return True


# Based on https://www.youtube.com/watch?v=OMoVcohRgZA
class Snake():
    def __init__(self):
        self.body = [[120,120]]
        self.xdir = 0
        self.ydir = 0
        self.justate = False
        self.oldtail = [0,0]

    def set_dir(self,x,y):
        self.xdir = x
        self.ydir = y

    def update(self):     
        self.oldtail = self.body[0].copy()
        head = self.body[-1].copy()
        if not self.justate: 
            self.body = self.body[1:]
        self.justate = False
        head[0] += self.xdir
        head[1] += self.ydir
        self.body.append(head)

    def eat(self,pos):
        x = self.body[-1][0]
        y = self.body[-1][1]
        if (x == pos[0] and y == pos[1]):
            self.justate = True
            # Color food white so it appears as a body part:
            wasp.watch.drawable.fill(x=(self.body[-1][0]),y=(self.body[-1][1]),w=15,h=15,bg=0x0000)
            wasp.watch.drawable.fill(x=self.body[-1][0]+1,y=self.body[-1][1]+1,w=13,h=13,bg=0xffff)
            return True
        return False

    def end_game(self):
        x = self.body[-1][0]
        y = self.body[-1][1]
        if (x >= 240 or x < 0) or (y >= 240 or y < 0):
            return True
        for i in range(len(self.body)-1):
            part = self.body[i]
            if (part[0] == x and part[1] == y):
                return True
        return False

    def show(self):
        draw = wasp.watch.drawable
        draw.fill(x=self.oldtail[0],y=self.oldtail[1],w=15,h=15,bg=0x0000)
        draw.fill(x=self.body[-1][0]+1,y=self.body[-1][1]+1,w=13,h=13,bg=0xffff)
