#A python script to communicate with 
# the mote.

import serial
import threading
import binascii
import sys
import time
from datetime import datetime

command_test = bytearray([
0xff,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
#0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
#0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0xee
])
#command_test1 = bytearray([0xff,0x02,0x02,0x02,0xee])
latency = [0.0,0.0]
min_value = 10000000
max_value = 0.0


def running_mean(x):
    global min_value
    global max_value
    if latency[1] == 1:
        min_value = max_value = x
    else:
        if x < min_value:
            min_value = x
        if x > max_value:
            max_value = x
    #tmp = latency[0] * max(latency[1]-1,1) + x
    #latency[0] = tmp / latency[1]

if __name__=="__main__":
    print "Interactive mode. Commands:"
    print "  root to make mote DAGroot"
    print "  inject to inject packet"
    print "  ipv6 to inject one packet"
    print "  sch to get mote schedule"
    print "  tx to add tx slot"
    print "  rx to add rx slot"
    print "  reset to reset the board"
    print "  quit to exit "
    
    try:
        serial = serial.Serial("/dev/ttyUSB0",'115200',timeout=100)
    except Exception as err:
        print err
    counter = 0
    try:
        while(1):
            #sys.stdout.flush()
            #cmd = raw_input('>> ')
            #sys.stdout.flush()
            #if cmd == "test":
                #print "sending test command"
                #a = datetime.now()
                #serial.write(command_test1)
                #try:
                    #rxByte = serial.read(1)
                #except Exception as err:
                    #print err
                #try:
                    #rxByte1 = serial.read(1)
                    #b = datetime.now()
                #except Exception as err:
                    #print err
                #b = datetime.now()
                #c = b - a
                #print c.microseconds
                #print len(command_test1)-1
                #print int(binascii.hexlify(rxByte),16)
                #print int(binascii.hexlify(rxByte1),16)
            #elif cmd == "quit":
                #print "exiting"
                #break;
            #else:
                #print "unknown command"
            a = datetime.now()
            #print int(round(time.time()))
            serial.write(command_test)
            #if counter == 0:
            rxByte = serial.read(1)
            #counter = counter + 1
            b = datetime.now()
            c = b - a
            if c.microseconds < min_value:
				min_value = c.microseconds
            print "c.microseconds: "+ str(c.microseconds)
            print len(command_test)
            #print int(binascii.hexlify(rxByte),16)
            #latency[1] = latency[1] + 1.0
            #running_mean(c.microseconds)
            #print "latency: "+ str(latency[0])
            print "min value: "+ str(min_value)
            #print "max_value: "+ str(max_value)
            #rxByte = serial.read(1)
            #time.sleep(0.0000005);
            #break
    except KeyboardInterrupt:
        exit()

    exit()

