# Echo server program
import socket
import sys
import time

#UDP echo server application, sends back the received data to client 

UDP_IP = "127.0.0.1"                 # Symbolic name meaning all available interfaces
UDP_PORT = 5005              # Arbitrary non-privileged port
s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

counter = 0

try:
    while True:
        counter = counter+1
        message = "  Sample data:  "+str(counter)+" "
        print "Now sending data"
        s.sendto(message, (UDP_IP, UDP_PORT))
        time.sleep(1)
        
except KeyboardInterrupt:
    exit()
