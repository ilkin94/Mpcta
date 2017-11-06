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


print "This is the name of the script: ", sys.argv[1]
#dictionary containing chip ack delay
chip_ack_delay_dict = {}
# file-output.py
f = open(sys.argv[1],'r')
line_galu = [i.rstrip('\n') for i in f]
f.close()
counter = 1;
#print line_galu
while (counter <= 127):
    useful_lines = []
    chip_ack_delay = []
    for i in line_galu:
        if((i.split()[3] == 'Bo:1:006:1' and i.split()[4] == '0' and i.split()[5] == str(counter)) or (i.split()[3] == 'Bo:1:006:1' and i.split()[4] == '-115' and i.split()[5] == str(counter))):
            if(i.split()[0] == 'ffff88040911d540'):
                print i
                useful_lines.append(i)
        else:
            continue

    index = 0
    while index < len(useful_lines):
        out_time = int(useful_lines[index].split()[1])
        ack_time = int(useful_lines[index+1].split()[1])
        chip_ack_delay.append(ack_time - out_time)
        index = index+2

    print len(chip_ack_delay)

    print chip_ack_delay[:500]

    chip_ack_delay_dict[str(counter)] = chip_ack_delay[:500]
    counter = counter+1

print chip_ack_delay_dict
#file_name = "chip_ack_delay" + re.search(r'\d+', sys.argv[1]).group() + '.json'

f = open("chip_ack_delay_dict_all.json",'w')
f.write(json.dumps(chip_ack_delay_dict))
f.close()
