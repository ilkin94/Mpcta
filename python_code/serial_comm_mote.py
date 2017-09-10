#A python script to communicate with 
# the mote.

import serial
import threading
import binascii
import sys
import time
import socket
import struct

command_set_dagroot = bytearray([0x7e,0x03,0x43,0x00])

command_get_neighbor_count = bytearray([0x7e,0x03,0x43,0x01])

command_get_neighbors = bytearray([0x7e,0x03,0x43,0x02])

command_inject_udp_packet = bytearray([0x7e,0x03,0x44,0x00])

#this is just a temporary hardcoded data, has to be read from
#sockets later
udp_packet_data = "200"

outputBufLock = False

outputBuf     = ''

H2R_PACKET_FORMAT = 'f'
H2R_PACKET_SIZE = struct.calcsize(H2R_PACKET_FORMAT)

#Beginning of moteProbe Class definition

#Beginning of moteProbe Class definition

class moteProbe(threading.Thread):

    def __init__(self,serialport=None):

        # store params
        self.serialport           = serialport

        # local variables
        self.framelength         = 0
        self.busyReceiving       = False
        self.inputBuf            = ''
        self.dataLock            = threading.Lock()
        self.rxByte              = 0
        self.prevByte            = 0


        # flag to permit exit from read loop
        self.goOn                 = True

        # initialize the parent class
        threading.Thread.__init__(self)

        # give this thread a name
        self.name                 = 'moteProbe@'+self.serialport
        
        try:
            self.serial = serial.Serial(self.serialport,'115200',timeout=1)
        except Exception as err:
            print err

        # start myself
        self.start()
        print "serial thread: "+self.name+" started successfully"
        #======================== thread ==========================================
    
    def run(self):
        while self.goOn: # read bytes from serial port
            #Sending commands to mote
            #Here I am using global variables
            global outputBuf
            global outputBufLock
            if (len(outputBuf) > 0) and not outputBufLock:
                self.serial.write(outputBuf)
                outputBuf = ''

            try:
                self.rxByte = self.serial.read(1)
                if not self.rxByte:
                    continue
                elif (int(binascii.hexlify(self.rxByte),16) == 0x7e) and not self.busyReceiving:
                    self.busyReceiving       = True
                    self.prevByte = self.rxByte
                    continue
            except Exception as err:
                print err
                time.sleep(1)
                break
            else:
                if self.busyReceiving and (int(binascii.hexlify(self.prevByte),16) == 0x7e):
                    #Converting string to integer to make comparison easier
                    self.framelength = int(binascii.hexlify(self.rxByte),16)
                    self.inputBuf           += self.rxByte
                    self.prevByte   = self.rxByte
                    continue
                else:
                    self.inputBuf           += self.rxByte
                    if len(self.inputBuf) == self.framelength:
                        self.busyReceiving = False
                        self._process_inputbuf()
    def _process_inputbuf(self):
        print type(self.inputBuf)
        if self.inputBuf[1].upper() == 'P':
            print "received packet: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
            data = [int(binascii.hexlify(x),16) for x in self.inputBuf]
            data_tuple = self.parser_data.parseInput(data[2:])
            global isDAOReceived
            if not isDAOReceived:
             isDAOReceived = self.routing_instance.meshToLbr_notify(data_tuple)
        elif self.inputBuf[1] == 'D':
            print "debug msg: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
        elif self.inputBuf[1] == 'R':
            print "command response: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
        self.inputBuf = ''

    def _process_packet(self,packet):
        print "process_packet_func"

    def _fill_outputbuf(self):
        #When user wants to send some data, data will be pushed to this buffer
        print __name__

    def close(self):
        self.goOn = False
        
    def prepare_UDP_packet(self,payload):
        print "prepare_UDP_packet"
#End of ModeProbe class definition



#Thread which continuosly receives data from UDP socket and writes into output buffer
class SocketThread(threading.Thread):
    
    def __init__(self,port_number=8889,host="127.0.0.1"):
        
        self.goOn                 = True

        self.UDP_IP = host
        self.UDP_PORT = port_number
        
        
        # initialize the parent class, This is equivalent to calling the constructor of the parent class
        threading.Thread.__init__(self)
        
        self.socket_handler = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket_handler.bind((self.UDP_IP, self.UDP_PORT))
        #Setting timeout as five seconds
        self.socket_handler.settimeout(15)
        self.start()
    
    
    def run(self):
        try:
            while self.goOn:
                #print "sending data to server"
                #self.socket_handler.sendto("Hello World",(self.UDP_IP,self.UDP_PORT))
                # buffer size is 1024 bytes
                try:
                    a = 200
                    #packed_a = struct.pack('f',a)
                    #data, addr = self.socket_handler.recvfrom(1024)
                    #float_data = struct.unpack(H2R_PACKET_FORMAT, data)
                    #print ("Control command received: %f" % a)
                    print "sending: "+"yadhu"
                    global outputBuf
                    global outputBufLock
                    outputBufLock = True
                    command_inject_udp_packet[1] = len(command_inject_udp_packet) + len("yadhu")-1;
                    outputBuf += command_inject_udp_packet+"yadhu";
                    outputBufLock  = False
                    time.sleep(0.1)
                except socket.timeout:
                    print "timeout exception"
                    continue
        except KeyboardInterrupt:
            self.close()
    
    #This function is used for stopping this thread from the main thread
    def close(self):
        self.goOn = False

SendPacketMode = False

if __name__=="__main__":
    moteProbe_object    = moteProbe('/dev/ttyUSB1')
    print "Interactive mode. Commands:"
    print "  root to make mote DAGroot"
    print "  inject to inject packet"
    print "  ipv6 to inject one packet"
    print "  quit to exit "
    
    try:
        while(1):
            sys.stdout.flush()
            cmd = raw_input('>> ')
            sys.stdout.flush()
            if cmd == "root":
                print "sending set DAG root command"
                sys.stdout.flush()
                outputBufLock = True
                outputBuf += command_set_dagroot;
                outputBufLock  = False
            elif cmd=="inject":
                print "Entering packet inject mode"
                sys.stdout.flush()
                SendPacketMode = True
            elif cmd == "ipv6":
                print "injecting one packet udp packet"
                sys.stdout.flush()
                print "sending: "+udp_packet_data
                outputBufLock = True
                command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(udp_packet_data)-1;
                outputBuf += command_inject_udp_packet+udp_packet_data;
                outputBufLock  = False
            elif cmd == "quit":
                print "exiting"
                sys.stdout.flush()
                break;
            while(SendPacketMode):
                    a = 200
                    print "sending: "+str(a)
                    sys.stdout.flush()
                    outputBufLock = True
                    command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(str(a))-1;
                    outputBuf += command_inject_udp_packet+str(a)
                    outputBufLock  = False
                    time.sleep(1)
    except KeyboardInterrupt:
        #socketThread_object.close()
        moteProbe_object.close()
        exit()

    moteProbe_object.close()
    #socketThread_object.close()
    exit()
