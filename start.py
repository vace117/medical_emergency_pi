'''
Created on Jun 22, 2017

@author: Val Blant
'''

import sys
import os
import signal
from wireless import Wireless

#
# Network Setup
#
network = Wireless('wlan0')

#
# Setup pigpio
#
import pigpio
gpio = pigpio.pi()
if not gpio.connected:
    print "pigpio could not be initialized!"
    exit()
else:
    print "pigpio init successful."
    

#
# The Main loop
#
def main_loop():
    print "READY!"
    

# 
# Make sure we are connected to GoPro's wifi
#
def check_wifi():
    ssid = get_current_ssid()
    connectionIsGood = False
    
    print "Currently connected to: %s" % (ssid)
    if ssid:
        response = os.system("ping -c 1 www.google.ca")
        if response == 0:
            connectionIsGood = True
        else:
            print "Google ping failed!"
    else:
        print "There's no wifi connection!"

    return connectionIsGood

def get_current_ssid():
    return network.current().split(' ', 1)[0]

#
# Graceful Exit
#
def ctrl_c_handler(signal, frame):
    print 'Cleaning up...'
    gpio.stop()
    sys.exit(0)
    

signal.signal(signal.SIGINT, ctrl_c_handler)
    
if __name__ == '__main__':
    try:
        if check_wifi():
            main_loop()
    finally:
        ctrl_c_handler(None, None)