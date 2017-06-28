'''
Created on Jun 22, 2017

@author: Val Blant
'''

#
# General Configuration
#
LED_PIN     = 3
SWITCH_PIN  = 11
PING_EVERY_SEC=120


import sys
import os
import signal
import threading
import time

#
# Logging Setup
#
import logging
logging.basicConfig(format='%(asctime)s %(message)s')
log = logging.getLogger('simple_example')
log.setLevel(logging.INFO)

#
# Network Setup
#
from wireless import Wireless
network = Wireless('wlan0')

##########################################
#         PIGPIO CONTROLLER STUFF        #
##########################################

# Setup pigpio
#
import pigpio
gpio = pigpio.pi()
if not gpio.connected:
    log.info("pigpio could not be initialized!")
    exit()
else:
    log.info("pigpio init successful.")
    gpio.set_mode           (LED_PIN, pigpio.OUTPUT)
    gpio.set_pull_up_down   (LED_PIN, pigpio.PUD_DOWN)  # Pull the pin to GND when its not 1, so no current flow to LED
    gpio.write              (LED_PIN, 0)
    
    gpio.set_mode           (SWITCH_PIN, pigpio.INPUT);
    gpio.set_pull_up_down   (SWITCH_PIN, pigpio.PUD_UP) # Pull the PIN up to 3.3V, unless the switch connects it to GND
    gpio.set_glitch_filter  (SWITCH_PIN, 1000) # Debounce the switch by waiting 1ms before reporting signal change

# Setup button press callback
#
gpioCallbackControl = None
def start_gpio_monitor():
    global gpioCallbackControl
    gpioCallbackControl = gpio.callback(SWITCH_PIN, pigpio.FALLING_EDGE, switch_pressed_callback)

def stop_gpio_monitor():
    global gpioCallbackControl
    gpioCallbackControl.cancel()
    gpioCallbackControl = None



############################
#         MAIN LOOP        #
############################

# This flag is used to flash the LED on boot up or after we lost the WiFi signal 
connectionInterrupted = True

# The Main loop
#
def main_loop():
    log.info("Starting main loop...")
    
    # Loop forever
    while True:
        if check_wifi():
            log.info("Connection to GCM confirmed. Sleeping easy...")
            led_on()
            
            if not gpioCallbackControl:
                # Start monitoring GPIO pin for a falling edge
                start_gpio_monitor()    
        else:
            BlinkyThread( blink_ping_failed ).start()   # ALARM! Connectivity lost...
            stop_gpio_monitor()
        
        # Wake up after this interval to check the connectivity again
        time.sleep(PING_EVERY_SEC)

def switch_pressed_callback(gpio, level, tick):
    log.info("==============================================")
    log.info(">>>>>>>>>>>>>>>>>> ALARM! <<<<<<<<<<<<<<<<<<<<")
    log.info(">>>>>>>>>>>>> MEDICAL EMERGENCY! <<<<<<<<<<<<<")
    log.info("==============================================")


##############################
#         LED CONTROL        #
##############################
           
# Ping-in-progress blink
def blink_pinging():
    gpio.write(LED_PIN, 1)
    time.sleep(0.7)
    gpio.write(LED_PIN, 0)
    time.sleep(0.7)

# Ping failed error blink
def blink_ping_failed():
    gpio.write(LED_PIN, 1)
    time.sleep(0.1)
    gpio.write(LED_PIN, 0)
    time.sleep(0.1)
    
def led_on():
    led_control(1)

def led_off():
    led_control(0)

# Tells the blinky thread to die and then sets the LED state     
def led_control(state):
    global executeBlinkProgramFlag
    global currentBlinkyThread
    
    executeBlinkProgramFlag = 0 # Die blinky tread, die!
    
    if currentBlinkyThread:
        currentBlinkyThread.join() # Wait for thread death 
    
    gpio.write(LED_PIN, state) # Set the LED state


################################
#         BLINKY THREAD        #
################################

# Blinky thread global control variables and flags
#    
threadLock = threading.Lock()
executeBlinkProgramFlag = 0
currentBlinkyThread = None
    
class BlinkyThread (threading.Thread):
    def __init__(self, blink_function):
        threading.Thread.__init__(self)
        global executeBlinkProgramFlag
        global currentBlinkyThread
        
        # The blink function is passed into the constructor
        self.blink_function = blink_function
        
        with threadLock:
            led_off()
            
            executeBlinkProgramFlag = 1     # Commence the blinky loop
            currentBlinkyThread = self      # This is how we achieve singleton behavior for the blinky class 
            
        
    def run(self):
        global executeBlinkProgramFlag
        
        with threadLock:
            log.debug("Starting " + self.name)
            while executeBlinkProgramFlag:
                self.blink_function()       # Do the blinking until the global flag tells us to stop
            log.debug("Exiting " + self.name)
################################################################


# 
# Make sure we are connected to wifi and that we can ping Google
#
def check_wifi():
    # If previous state was disconnected, give the 3 second slow blink signal 
    # to indicate that we are about to try pinging again
    #
    global connectionInterrupted
    if connectionInterrupted:
        BlinkyThread( blink_pinging ).start()
        time.sleep(3)
    
    ssid = get_current_ssid()
    connectionIsGood = False
    
    log.info("Currently connected to: %s" % (ssid))
    if ssid:
        response = os.system("ping -c 1 www.google.ca")
        if response == 0:
            connectionIsGood = True
        else:
            log.error("Google ping failed!")
    else:
        log.error("There's no wifi connection!")

    connectionInterrupted = not connectionIsGood
    return connectionIsGood

# Returns SSID of current WiFi network
def get_current_ssid():
    return network.current().split(' ', 1)[0]


####################################
#         BOILER PLATE CRAP        #
####################################

#
# Graceful Exit
#
def ctrl_c_handler(signal, frame):
    log.info('Cleaning up...')
    stop_gpio_monitor()
    led_off()
    gpio.stop()
    sys.exit(0)
    

signal.signal(signal.SIGINT, ctrl_c_handler)
    
if __name__ == '__main__':
    try:
        main_loop()
    finally:
        ctrl_c_handler(None, None)
