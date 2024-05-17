# Fneb's temperature controlled oven
# It's probably pretty iffy and still needs work, especially around safeguards. Also I need to properly tune it but that's a me problem.

import time
import board
import busio
import adafruit_mcp9600
import terminalio
import displayio
import gc
import digitalio

try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire
from adafruit_display_text import label
from adafruit_display_text.scrolling_label import ScrollingLabel
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.rect import Rect
from adafruit_st7789 import ST7789
import adafruit_rgbled
from adafruit_debouncer import Debouncer



# set up temp sensor and variables
i2c = busio.I2C(board.GP3, board.GP2, frequency=200000)
mcp = adafruit_mcp9600.MCP9600(i2c)
lasttempread = -1
lasttempdisplayupdate = -1
tempupdate = 0.1
targettemp = 0

tempdisplayupdate = 0.5
chambertemp = 0
electronicstemp = 0

#set up display
displayio.release_displays()

tft_cs = board.GP17
tft_dc = board.GP16
spi_mosi = board.GP19
spi_clk = board.GP18
spi = busio.SPI(spi_clk, spi_mosi)
backlight = board.GP20

display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs)

display = ST7789(
    display_bus, rotation=90, width=320, height=240, backlight_pin=backlight
)
#set up display RGB LED
red_led = board.GP6
green_led = board.GP7
blue_led = board.GP8
led = adafruit_rgbled.RGBLED(red_led, green_led, blue_led, invert_pwm = True)
led.color = (0, 0, 20)

#set up buttons
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

# SSR control
ovenssr1 = digitalio.DigitalInOut(board.GP10)
ovenssr1.direction = digitalio.Direction.OUTPUT
ovenssr1.value = False
relaystate = False
relaycheckintimer = 0.1

# with thanks to github.com/veebch/heat-o-matic
# PID temperature control bits
lasterror = 0
integral = 0
# Explanation Stolen From Reddit: In terms of steering a ship:
# Kp is steering harder the further off course you are,
# Ki is steering into the wind to counteract a drift
# Kd is slowing the turn as you approach your course
Kp=100   # Proportional term - Basic steering (This is the first parameter you should tune for a particular setup)
Ki=.03   # Integral term - Compensate for heat loss by vessel
Kd=700.  # Derivative term - to prevent overshoot due to inertia - if it is zooming towards setpoint this
         # will cancel out the proportional term due to the large negative gradient

# Make the display context
main_group = displayio.Group()
# Make a background color fill
color_bitmap = displayio.Bitmap(display.width, display.height, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0x0
bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
bg_group = displayio.Group()
bg_group.append(bg_sprite)
main_group.append(bg_group)
display.root_group = main_group

# create the main UI area, with nothing in it right now, and add it to the main_group
mainui = displayio.Group()
main_group.append(mainui)
currentscreen = "0"

# set up top bar
topbarfill = Rect(0, 0, 320, 15, fill=0x020973)
currenttempdisplay = label.Label(terminalio.FONT, text="C: "+str(chambertemp)+"/"+str(targettemp)+" "*5, color=0xFFFFFF)
relayindicator = Circle(5, 7, 4, fill=0x000000)
electronicstempdisplay = label.Label(terminalio.FONT, text="E: "+str(electronicstemp), color=0xFFFFFF)
currenttempdisplay.x = 10
currenttempdisplay.y = 7
electronicstempdisplay.x = 90
electronicstempdisplay.y = 7
topbar = displayio.Group()
topbarcolor = displayio.Group()
topbarcolor.append(topbarfill)
topbarcurrenttemp = displayio.Group()
topbarcurrenttemp.append(currenttempdisplay)
topbarelectronicstemp = displayio.Group()
topbarelectronicstemp.append(electronicstempdisplay)
topbar.append(topbarcolor)
topbar.append(relayindicator)
topbar.append(topbarcurrenttemp)
topbar.append(topbarelectronicstemp)
topbar.scale = 2
main_group.append(topbar)


def temp_display():
    if chambertemp >= 50:
        topbarfill.fill=0x730204
        led.color = (100, 0, 0)
    else:
        topbarfill.fill=0x020973
        led.color = (0, 0, 20)
    if relaystate == True:
        relayindicator.fill=0xFFFFFF
    else:
        relayindicator.fill=0x000000
    currenttempdisplay.text = "C: "+str(chambertemp)+"/"+str(targettemp)
    electronicstempdisplay.text = "E: "+str(electronicstemp)
    gc.collect()
    

def tempupdater():
    global chambertemp
    global electronicstemp
    global targettemp
    chambertemp = round(mcp.temperature, 1)
    electronicstemp = round(mcp.ambient_temperature, 1)
    #print(chambertemp)
    global lasttempread
    global tempnow
    #again, bits coming from heat-o-matic
    global relaycheckintimer
    global Kp
    global Ki
    global Kd
    global integral
    global lasterror
    global relaystate
    if targettemp != 0:
        
        dt = tempnow - lasttempread

        if dt > relaycheckintimer:
            
            error = targettemp - chambertemp
            integral = integral + dt * error
            derivative = (error - lasterror)/dt
            pidoutput = Kp * error + Ki * integral + Kd * derivative
            if pidoutput > 0 and targettemp != 0:  
                ovenssr1.value = True
                relaystate = True
            else:
                ovenssr1.value = False
                relaystate = False
            lasterror = error
            lasttempread = tempnow
    else:
        ovenssr1.value = False
#        lasterror = 0
#        integral = 0
    gc.collect()

def mainmenu():
    print("drawing main menu")
    mainmenuscreen = displayio.Group()
    mainmenuscreen.scale = 2
    mainmenu_option1 = label.Label(terminalio.FONT, text="A: Fixed temp", color=0xFFFFFF)
    mainmenu_option1.x = 7
    mainmenu_option1.y = 30
    mainmenuscreen.append(mainmenu_option1)
    mainmenu_option2 = label.Label(terminalio.FONT, text="B: Not yet", color=0xFFFFFF)
    mainmenu_option2.x = 7
    mainmenu_option2.y = 90
    mainmenuscreen.append(mainmenu_option2)
    mainui.insert(0, mainmenuscreen)
    global currentscreen
    currentscreen = "mainmenu"

def fixedtemp():
    fixedtempscreen = displayio.Group()
    fixedtempscreen.scale = 2
    global targettemp
    global targettempunconfirmed
    if targettemp != 0:
        targettempunconfirmed = targettemp
    if targettemp == 0:
        targettempunconfirmed = 100
    fixedtempscreen_ok = label.Label(terminalio.FONT, text="A: OK/Set", color=0xFFFFFF)
    fixedtempscreen_ok.x = 7
    fixedtempscreen_ok.y = 30
    fixedtempscreen.append(fixedtempscreen_ok)
    fixedtempscreen_cd = label.Label(terminalio.FONT, text="B: Cooldown", color=0xFFFFFF)
    fixedtempscreen_cd.x = 7
    fixedtempscreen_cd.y = 90
    fixedtempscreen.append(fixedtempscreen_cd)
    fixedtempscreen_plus5 = label.Label(terminalio.FONT, text="X: +5", color=0xFFFFFF)
    fixedtempscreen_plus5.x = 130
    fixedtempscreen_plus5.y = 30
    fixedtempscreen.append(fixedtempscreen_plus5)
    fixedtempscreen_minus5 = label.Label(terminalio.FONT, text="Y: -5", color=0xFFFFFF)
    fixedtempscreen_minus5.x = 130
    fixedtempscreen_minus5.y = 90
    fixedtempscreen.append(fixedtempscreen_minus5)
    global fixedtempscreen_target
    fixedtempscreen_target = label.Label(terminalio.FONT, text="Current Target: "+str(targettemp), color=0xFFFFFF)
    fixedtempscreen_target.x = 20
    fixedtempscreen_target.y = 40
    fixedtempscreen.append(fixedtempscreen_target)
    global fixedtempscreen_unconfirmedtarget
    fixedtempscreen_unconfirmedtarget = label.Label(terminalio.FONT, text="New Target: "+str(targettempunconfirmed), color=0xFFFFFF)
    fixedtempscreen_unconfirmedtarget.x = 20
    fixedtempscreen_unconfirmedtarget.y = 60
    fixedtempscreen.append(fixedtempscreen_unconfirmedtarget)
    mainui.insert(0, fixedtempscreen)
    global currentscreen
    currentscreen = "fixedtemp"

    
def changemainui(currentscreen):
    print("changing screen")
    print(currentscreen)
    global mainui
    mainui.pop(0)
    if currentscreen == "fixedtemp":
        fixedtemp()
    if currentscreen == "mainmenu":
        mainmenu()
    

def buttons():
    global currentscreen
    if currentscreen == "mainmenu":
        global switch_y
        switch_y.update()
        if switch_y.fell:
            print("changing to fixed temp menu")
            global currentscreen
            currentscreen = "fixedtemp"
            changemainui(currentscreen)
        global switch_x
        switch_x.update()
        if switch_x.fell:
            print("X Just pressed")
        global switch_b
        switch_b.update()
        if switch_b.fell:
            print("B Just pressed")
        global switch_a
        switch_a.update()
        if switch_a.fell:
            print("A Just pressed")
    if currentscreen == "fixedtemp":
        global switch_y
        switch_y.update()
        if switch_y.fell:
            #print("OK")
            global targettemp
            global targettempunconfirmed
            targettemp = targettempunconfirmed
            global fixedtempscreen_target
            fixedtempscreen_target.text = "Current Target: "+str(targettemp)
        global switch_x
        switch_x.update()
        if switch_x.fell:
            #print("Cooldown")
            global targettemp
            targettemp = 0
            global fixedtempscreen_target
            fixedtempscreen_target.text = "Current Target: "+str(targettemp)
        global switch_b
        switch_b.update()
        if switch_b.fell:
            #print("+5")
            global targettempunconfirmed
            targettempunconfirmed += 5
            global fixedtempscreen_unconfirmedtarget
            fixedtempscreen_unconfirmedtarget.text = "New Target: "+str(targettempunconfirmed)
            currenttempdisplay.text = "C: "+str(chambertemp)+"/"+str(targettemp)
        global switch_a
        switch_a.update()
        if switch_a.fell:
            #print("-5")
            global targettempunconfirmed
            if targettempunconfirmed >= 5:
                targettempunconfirmed -= 5
                global fixedtempscreen_unconfirmedtarget
                fixedtempscreen_unconfirmedtarget.text = "New Target: "+str(targettempunconfirmed)
            


while True:
    if currentscreen == "0":
        fixedtemp()
        #mainmenu()
    tempnow = time.monotonic()
    buttons()
    if tempnow >= lasttempread + tempupdate:
        tempupdater()
    tempdisplaynow = time.monotonic()
    if tempdisplaynow >= lasttempdisplayupdate + tempdisplayupdate:
        temp_display()
        lasttempdisplayupdate = tempdisplaynow


