#A python script to parse the usbmon and save ack latency as json file.

import serial
import threading
import binascii
import sys
import time
import socket
import struct
import json
import re

counter = 1;
serial_total_delay = {}

while (counter <= 127):
    file_name = "measurement_serial_data"+str(counter)+".json"
    f = open(file_name,'r')
    serial_total_delay[str(counter)] = json.load(f)
    f.close()
    counter = counter + 1
    print serial_total_delay

print "here is the complete dictionary"
print serial_total_delay

f = open("serial_total_delay_all.json",'w')
f.write(json.dumps(serial_total_delay))
f.close()
