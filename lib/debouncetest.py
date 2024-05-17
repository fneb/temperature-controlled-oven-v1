# SPDX-FileCopyrightText: 2019 Dave Astels for Adafruit Industries
# SPDX-License-Identifier: MIT

# pylint: disable=invalid-name

import board
import digitalio
from adafruit_debouncer import Debouncer

#button_a = board.GP12
#button_b = board.GP13
#button_x = board.GP14
#button_y = board.GP15

button_a = digitalio.DigitalInOut(board.GP12)
button_a.direction = digitalio.Direction.INPUT
button_a.pull = digitalio.Pull.UP
switch_a = Debouncer(button_a)

button_b = digitalio.DigitalInOut(board.GP13)
button_b.direction = digitalio.Direction.INPUT
button_b.pull = digitalio.Pull.UP
switch_b = Debouncer(button_b)

button_x = digitalio.DigitalInOut(board.GP14)
button_x.direction = digitalio.Direction.INPUT
button_x.pull = digitalio.Pull.UP
switch_x = Debouncer(button_x)

button_y = digitalio.DigitalInOut(board.GP15)
button_y.direction = digitalio.Direction.INPUT
button_y.pull = digitalio.Pull.UP
switch_y = Debouncer(button_y)

while True:
    switch_a.update()
    if switch_a.fell:
        print("A Just pressed")
    if switch_a.rose:
        print("A Just released")
    #if not switch_a.value:
    #    print("A pressed")
    #else:
    #    print("B pressed")
    switch_b.update()
    if switch_b.fell:
        print("B Just pressed")
    if switch_b.rose:
        print("B Just released")
    #if not switch_b.value:
    #    print("B pressed")
    #else:
    #    print("B pressed")
    switch_x.update()
    if switch_x.fell:
        print("X Just pressed")
    if switch_x.rose:
        print("X Just released")
    #if not switch_x.value:
    #    print("X pressed")
    #else:
    #    print("X pressed")
    switch_y.update()
    if switch_y.fell:
        print("Y Just pressed")
    if switch_y.rose:
        print("Y Just released")
    #if not switch_y.value:
    #    print("Y pressed")
    #else:
        #print("Y pressed")