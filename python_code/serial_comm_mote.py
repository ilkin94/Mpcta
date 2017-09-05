#A python script to communicate with 
# the mote.

import serial
import threading
import binascii
import sys
import time
import socket

command_set_dagroot = bytearray([0x7e,0x03,0x43,0x00])

command_get_neighbor_count = bytearray([0x7e,0x03,0x43,0x01])

command_get_neighbors = bytearray([0x7e,0x03,0x43,0x02])

command_inject_udp_packet = bytearray([0x7e,0x03,0x44,0x00])

#this is just a temporary hardcoded data, has to be read from
#sockets later
udp_packet_data = "Madhusudana"

outputBufLock = False

outputBuf     = ''

#Beginning of moteProbe Class definition

class moteProbe(threading.Thread):

    def __init__(self,serialport=None):

        # store params
        self.serialport           = serialport

        # local variables
        self.framelength        = 0
        self.busyReceiving      = False
        self.inputBuf             = ''
        self.dataLock             = threading.Lock()
        self.rxByte              = 0

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
                print ';'.join('{:02x}'.format(x) for x in outputBuf)
                outputBuf = ''

            try:
                self.rxByte = self.serial.read(1)
                if not self.rxByte:
                    continue
                #else:
                    #continue
            except Exception as err:
                print err
                time.sleep(1)
                break
            else:
                self.inputBuf           += self.rxByte
                #if not self.busyReceiving :
                    #self.busyReceiving       = True
                    #self.framelength = self.rxByte
                    #self.inputBuf   += self.rxByte
                #else:
                    #self.inputBuf           += self.rxByte
                    #if len(self.inputBuf) == int(binascii.hexlify(self.framelength),16):
                        #self.busyReceiving = False
                self._process_inputbuf()
    def _process_inputbuf(self):
        print ":".join("{:02x}".format(ord(c)) for c in self.inputBuf)
        self.inputBuf = ''

    def fill_outputbuf(self):
        #When user wants to send some data, data will be pushed to this buffer
        print __name__

    def close(self):
        self.goOn = False
        
#End of ModeProbe class definition



#Thread which continuosly receives data from UDP socket and writes into output buffer
class SocketThread(threading.Thread):
    
    def __init__(self,port_number=5005,host="127.0.0.1"):
        
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
                    data, addr = self.socket_handler.recvfrom(1024)
                    print "Received: "+ data +" Injecting the data to the mote"
                    global outputBuf
                    global outputBufLock
                    outputBufLock = True
                    command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(data)-1;
                    outputBuf += command_inject_udp_packet+data;
                    outputBufLock  = False
                except:
                    print "timeout exception"
                    continue
        except KeyboardInterrupt:
            self.close()
    
    #This function is used for stopping this thread from the main thread
    def close(self):
        self.goOn = False

if __name__=="__main__":
    moteProbe_object = moteProbe('/dev/ttyUSB1')
    socketThread_object = SocketThread()

    print "Interactive mode. Commands:"
    print "  N to get neighbors count"
    print "  G to get neighbors"
    print "  I to inject UDP packet"
    print "  T to test code block"
    print "  X to exit "
    
    try:
        while(1):
            sys.stdout.flush()
            cmd = raw_input('>> ')
            cmd = cmd.split()
            sys.stdout.flush()
            if cmd[0] == 'N':
                print "sending command get neighbors count"
                sys.stdout.flush()
                outputBufLock = True
                outputBuf += command_get_neighbors;
                outputBufLock  = False

            elif cmd[0] == 'G':
                print "sending command get neighbors command"
                sys.stdout.flush()
                outputBufLock = True
                outputBuf += command_get_neighbors;
                outputBufLock  = False
              
            elif cmd[0] == 'I':
                print "sending command Inject UDP packet"
                sys.stdout.flush()
                outputBufLock = True
                command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(udp_packet_data)-1;
                outputBuf += command_inject_udp_packet+udp_packet_data;
                outputBufLock  = False
              
            elif cmd[0] == 'T':
                print "This block is for testing the feature"
                print command_inject_udp_packet[0]
                print len(udp_packet_data)

            elif cmd[0] == 'X':
              print "exiting..."
              break

            else:
                print "No such command: " + ' '.join(cmd)
    except KeyboardInterrupt:
        socketThread_object.close()
        moteProbe_object.close()
        exit()

    moteProbe_object.close()
    socketThread_object.close()
    exit()
