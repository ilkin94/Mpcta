#This python script reads the packets from the serial port, builds the routing table based on them.

import socket
import serial
import threading
import binascii
import sys
import time
from ParserData import ParserData
from Routing import Routing
from UDPPacket import UDPPacket

command_set_dagroot = bytearray([0x7e,0x03,0x43,0x00])

command_get_node_type = bytearray([0x7e,0x03,0x43,0x01])

command_get_neighbor_count = bytearray([0x7e,0x03,0x43,0x02])

command_get_neighbors = bytearray([0x7e,0x03,0x43,0x03])

command_get_schedule = bytearray([0x7e,0x03,0x43,0x04])

command_add_tx_slot = bytearray([0x7e,0x03,0x43,0x05])

command_add_rx_slot = bytearray([0x7e,0x03,0x43,0x06])

command_get_buff_stat = bytearray([0x7e,0x03,0x43,0xff])

command_inject_udp_packet = bytearray([0x7e,0x03,0x44,0x00])

ping_packet = bytearray([0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,0xf1,0x7a,0x55,0x3a,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,
0x80,0x0,0x47,0x85,0x5,0xa8,0x0,0xd,0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9])


#I have to convert this ipv6 packet to 6LowPAN packet
ipv6_ping_packet  = [0x60,0x9,0xbe,0x7b,0x0,0x12,0x3a,0x40,0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,
0x80,0x0,0x3b,0x3d,0xb,0x9d,0x6,0x60,0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9]

ipv6_udp_packet =   [0x60,0xe,0x30,0x93,0x0,0xb,0x11,0x40,0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,
0xa7,0x64,0xf0,0xb2,0x0,0xb,0xe8,0x34,0x31,0x30,0x30]

lowpan_udp_packet = [0xf1,0x7a,0x55,0x11,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,0xd5,0x9c,0xf0,0xb2,0x0,0xb,0xba,0xc8,0x31,0x30,0x30]


outputBufLock   = False

outputBuf       = ''

isDAGRoot       = False

RoutingInstanceLock    = False

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
        
        self.parser_data = ParserData()
        
        self.routing_instance = Routing()

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
                outputBufLock = True
                self.serial.write(outputBuf)
                print "injecting: "+':'.join('{:02x}'.format(x) for x in outputBuf[1:])
                outputBuf = ''
                outputBufLock = False

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
                #time.sleep(0.1)
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
        if self.inputBuf[1].upper() == 'P':
            print "received packet: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
            data = [int(binascii.hexlify(x),16) for x in self.inputBuf]
            data_tuple = self.parser_data.parseInput(data[2:])
            self.routing_instance.meshToLbr_notify(data_tuple)
        elif self.inputBuf[1] == 'D':
            print "debug msg: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
        elif self.inputBuf[1] == 'R':
            print "command response: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
        elif self.inputBuf[1] == 'E':
            print "error msg: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
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
                    global isDAOReceived
                    if(isDAOReceived):
                        self.inject_data(data)
                except:
                    print "timeout exception"
                    continue
        except KeyboardInterrupt:
            self.close()
    
    def inject_data(self,data):
            
            global outputBuf
            global outputBufLock 
            sys.stdout.flush()
            test2                = UDPPacket()
            test2.setData("Yadhunandana")
            tmp2 = test2.getPacket()
            lowpan_packet2 = self.modeprobeobject.routing_instance.convert_to_iphc(tmp2)
            str_lowpanbytes2 = ''.join(chr(i) for i in lowpan_packet[0]+lowpan_packet[1])
            str_lowpanbytes2 = bytearray(str_lowpanbytes2)
            
            print ':'.join('{:02x}'.format(x) for x in str_lowpanbytes2)
            
            outputBufLock = True
            command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(str_lowpanbytes2)-1; #Here subtracting one because 0x7e is not included in the length
            outputBuf += command_inject_udp_packet+str_lowpanbytes2;
            outputBufLock  = False
    
    #This function is used for stopping this thread from the main thread
    def close(self):
        self.goOn = False
        

SendPacketMode = False


def checkSumCalc(pkt):
    p = sum(pkt)
    result = [0,0]
    #Following little endian because it becomes easy in C to convert to value.
    result[1] = p >> 8
    result[0] = p & 0xff
    #print "checksum: "+':'.join('{:02x}'.format(x) for x in result)
    return bytearray(result)


if __name__=="__main__":
    moteProbe_object    = moteProbe('/dev/ttyUSB0')
    test                = UDPPacket() 
    #socketThread_object = SocketThread()
    
    UDP_IP = "127.0.0.1"
    UDP_PORT = 5005
    
    socket_handler = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    socket_handler.bind((UDP_IP, UDP_PORT))
    #Setting timeout as five seconds
    socket_handler.settimeout(15)
    
    print "Interactive mode. Commands:"
    print "  root to make mote DAGroot"
    print "  inject to inject packet"
    print "  ipv6 to inject one packet"
    print "  sch to get mote schedule"
    print "  tx to add tx slot"
    print "  rx to add rx slot"
    print "  quit to exit "
    
    try:
        while(1):
            sys.stdout.flush()
            cmd = raw_input('>> ')
            sys.stdout.flush()
            if cmd == "root":
                print "sending set DAG root command"
                sys.stdout.flush()
                command_set_dagroot[1] = len(command_set_dagroot)-1 + 2 #excluding 0x7e and including 2 byte checksum in the len
                chsum = checkSumCalc(command_set_dagroot[1:]) #Excluding 0x7e for checksum calculation
                outputBufLock = True
                outputBuf += command_set_dagroot + chsum;
                outputBufLock  = False
            elif cmd=="inject":
                print "Entering packet inject mode"
                sys.stdout.flush()
                SendPacketMode = True
            elif cmd == "ipv6":
                print "injecting one packet udp packet by converting lowpan packet"
                sys.stdout.flush()
                test.setData("Yadhunandana")
                tmp = test.getPacket()
                lowpan_packet = moteProbe_object.routing_instance.convert_to_iphc(tmp)
                if lowpan_packet is None:
                    print "Unable to inject packet"
                    continue
                str_lowpanbytes = ''.join(chr(i) for i in lowpan_packet[0]+lowpan_packet[1])
                print "injecting: "+":".join("{:02x}".format(ord(c)) for c in str_lowpanbytes)

                outputBufLock = True
                command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(str_lowpanbytes)-1; #Here subtracting one because 0x7e is not included in the length
                outputBuf += bytearray(str(command_inject_udp_packet)+str_lowpanbytes)
                outputBufLock  = False
            elif cmd == "sch":
                print "sending get schedule command"
                sys.stdout.flush()
                command_get_schedule[1] = len(command_get_schedule)-1 + 2 #excluding 0x7e and including 2 byte checksum in the len
                chsum = checkSumCalc(command_get_schedule[1:]) #Excluding 0x7e for checksum calculation
                outputBufLock = True
                outputBuf += command_get_schedule + chsum;
                outputBufLock  = False
            elif cmd == "tx":
                print "sending add tx slot command"
                sys.stdout.flush()
                command_add_tx_slot[1] = len(command_add_tx_slot)-1 + 2 #excluding 0x7e and including 2 byte checksum in the len
                chsum = checkSumCalc(command_add_tx_slot[1:]) #Excluding 0x7e for checksum calculation
                outputBufLock = True
                outputBuf += command_add_tx_slot + chsum;
                outputBufLock  = False
            elif cmd == "rx":
                print "sending add rx slot command"
                sys.stdout.flush()
                command_add_rx_slot[1] = len(command_add_rx_slot)-1 + 2 #excluding 0x7e and including 2 byte checksum in the len
                chsum = checkSumCalc(command_add_rx_slot[1:]) #Excluding 0x7e for checksum calculation
                outputBufLock = True
                outputBuf += command_add_rx_slot + chsum;
                outputBufLock  = False
            elif cmd == "quit":
                print "exiting"
                break;
            else:
                print "getting buff status"
                sys.stdout.flush()
                outputBufLock = True
                outputBuf += command_get_buff_stat;
                outputBufLock  = False
            while(SendPacketMode):
                    #try:
                        #data, addr = socket_handler.recvfrom(3)
                    #except socket.timeout:
                        #print "timeout exception"
                        #continue
                    #except KeyboardInterrupt:
                        #moteProbe_object.close()
                        #exit()
                    data = "100"
                    sys.stdout.flush()
                    test.setData(data)
                    tmp = test.getPacket()
                    #print "ipv6: "+':'.join(hex(i) for i in tmp)
                    lowpan_packet = moteProbe_object.routing_instance.convert_to_iphc(tmp)
                    if lowpan_packet is None:
                        #This happens when we don't have a route to the mote
                        print "Unable to inject packet"
                        continue
                    #str_lowpanbytes = lowpan_udp_packet
                    str_lowpanbytes = ''.join(chr(i) for i in lowpan_packet[0]+lowpan_packet[1])
                    #Here subtracting one because 0x7e is not included in the length, Adding to two to include checksum bytes.
                    command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(str_lowpanbytes)-1 + 2;
                    #Here I will calculate 16-bit checksum for the whole packet then, I will attach it to end of the packet.
                    chsum = checkSumCalc(bytearray(str(command_inject_udp_packet[1:])+str_lowpanbytes))
                    if not outputBufLock:
                        outputBufLock = True
                        outputBuf += bytearray(str(command_inject_udp_packet)+str_lowpanbytes+str(chsum))
                        outputBufLock  = False
                    time.sleep(0.05)
    except KeyboardInterrupt:
        #socketThread_object.close()
        moteProbe_object.close()
        exit()

    moteProbe_object.close()
    #socketThread_object.close()
    exit()
    
#if __name__=="__main__":
    #moteProbe_object    = moteProbe('/dev/ttyUSB0')
    #test                = UDPPacket() 
    #socketThread_object = SocketThread()

    #print "Interactive mode. Commands:"
    #print "  root to make mote DAGroot"
    #print "  motetype to get motetype"
    #print "  nbrcount to get neighbors count"
    #print "  getnbr to get neighbors"
    #print "  ping to ping the neighbor"
    #print "  inject to inject packet"
    #print "  test to test code block"
    #print "  quit to exit "
    
    #try:
        #while(1):
            #global outputBuf
            #global outputBufLock 
            #sys.stdout.flush()
            #cmd = raw_input('>> ')
            #sys.stdout.flush()
            #if cmd == "root":
                #print "sending set DAG root command"
                #sys.stdout.flush()
                #outputBufLock = True
                #outputBuf += command_set_dagroot;
                #outputBufLock  = False
            #elif cmd == "motetype":
                #print "sending command to get node type"
                #sys.stdout.flush()
                #outputBufLock = True
                #outputBuf += command_get_node_type;
                #outputBufLock  = False
            #elif cmd == "nbrcount":
                #print "sending command get neighbors count"
                #sys.stdout.flush()
                #outputBufLock = True
                #outputBuf += command_get_neighbor_count;
                #outputBufLock  = False
            #elif cmd == "getnbr":
                #print "sending command get neighbors command"
                #sys.stdout.flush()
                #outputBufLock = True
                #outputBuf += command_get_neighbors;
                #outputBufLock  = False
              
            #elif cmd == "ping":
                #print "sending command ping packet"
                #sys.stdout.flush()
                #outputBufLock = True
                #command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(ping_packet)-1; #Here subtracting one because 0x7e is not included in the length
                #outputBuf += command_inject_udp_packet+ping_packet;
                #outputBufLock  = False
            #elif cmd == "inject":
                #print "injecting udp packet by converting lowpan packet"
                #sys.stdout.flush()
                #test.setData("Yadhunandana")
                #tmp = test.getPacket()
                #lowpan_packet = moteProbe_object.routing_instance.convert_to_iphc(tmp)
                #print type(lowpan_packet[0][1])
                
                #str_lowpanbytes = ''.join(chr(i) for i in lowpan_packet[0]+lowpan_packet[1])
                #str_lowpanbytes = bytearray(str_lowpanbytes)
                #print ':'.join('{:02x}'.format(x) for x in str_lowpanbytes)
                
                #outputBufLock = True
                #command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(str_lowpanbytes)-1; #Here subtracting one because 0x7e is not included in the length
                #outputBuf += command_inject_udp_packet+str_lowpanbytes;
                #outputBufLock  = False
                
            #elif cmd == "test":
                #print "This block is for testing the feature put random code in here"
                #sys.stdout.flush()
                #test.setData("sample")
                #tmp = test.getPacket()
                #lowpan_packet = moteProbe_object.routing_instance.convert_to_iphc(tmp)
                #print type(lowpan_packet[0][1])
                
                #str_lowpanbytes = ''.join(chr(i) for i in lowpan_packet[0]+lowpan_packet[1])
                #str_lowpanbytes = bytearray(str_lowpanbytes)
                #print ':'.join('{:02x}'.format(x) for x in str_lowpanbytes)
                
                #outputBufLock = True
                #command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(str_lowpanbytes)-1; #Here subtracting one because 0x7e is not included in the length
                #outputBuf += command_inject_udp_packet+str_lowpanbytes;
                #outputBufLock  = False

            #elif cmd == "quit":
              #print "exiting..."
              #break

            #else:
                #print "No such command: " + ' '.join(cmd)
    #except KeyboardInterrupt:
        #socketThread_object.close()
        #moteProbe_object.close()
        #exit()

    #moteProbe_object.close()
    #socketThread_object.close()
    #exit()
