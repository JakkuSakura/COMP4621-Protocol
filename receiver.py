"""
This file defines the receiver
"""

import getopt
import socket
import sys


from packet import Packet


def check():
    """
    Check whether receiver correctly receives the file
    """

    true_pkt_buffer = _collect_pkt(sent_file_name)  # Read the file that is sent to this receiver and store data in a buffer

    '''If the receiver's buffer has the different length with the true buffer, something must be wrong'''
    if len(true_pkt_buffer) != len(rcv_pkt_buffer):
        print('Fail')
        return

    '''Check whether received packets are correct'''
    for i in range(len(true_pkt_buffer)):
        if true_pkt_buffer[i].payload != rcv_pkt_buffer[i].payload:
            print('Fail')
            return

    '''If no error occurs'''
    print('Pass')


def _collect_pkt(file_name):
    """
    Read data from the sent file and store data in a buffer. This buffer is served as the ground truth
    :param file_name: Name of the sent file
    :return: The ground truth buffer
    """
    try:
        file = open(file_name, 'rb')
        with file:
            cnt = 0
            buffer = []
            while True:
                chunk = file.read(payload_len)
                if not chunk:
                    break
                buffer.append(Packet(chunk, cnt))
                cnt += 1
    except IOError:
        print('File does not exist', file_name)
        return
    return buffer


def parse_args(argv):
    """
    Read the command line arguments
    :param argv: The command line arguments
    """
    global file_name    # File to write the received data
    global sent_file_name    # File name of the sent file
    global payload_len    # Payload length. This parameter should be the same as that of the sender in order to check
                          # the correctness of the received file.

    hlp_msg = 'receiver.py -f <file name> -s <sent file name> -l <payload length> '
    try:
        opts, args = getopt.getopt(argv, "hf:s:l:",
                                   ["file_name=", "sent_name=", "payload_len="])
    except getopt.GetoptError:
        print(hlp_msg)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(hlp_msg)
            sys.exit()
        elif opt in ("-f", "--file_name"):
            file_name = arg
        elif opt in ("-s", "--sent_name"):
            sent_file_name = arg
        elif opt in ('-l', '--payload_len'):
            payload_len = int(arg)


file_name = 'recv.txt'    # File to write the received data
sent_file_name = 'doc2.txt'  # File name of the sent file
payload_len = 512    # Payload length
rcv_pkt_buffer = []    # Buffer to store the received packets
from protocol import Protocol
from adaptors import UdtAdaptor
import time
if __name__ == '__main__':
    '''Parse command line arguments'''
    parse_args(sys.argv[1:])
    
    ''''Open file-to-write and a UDP socket'''
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(('localhost', 8080))
    server.setblocking(False)

    server_protocol = Protocol(UdtAdaptor(server, None), server=True, name='receiver')
    '''Start the receiver'''
    try:
        with open(file_name, 'wb+') as f:
            while server_protocol.open:
                packet = server_protocol.recv()
                if packet:
                    packet = Packet(payload=packet)
                    rcv_pkt_buffer.append(packet)
                    f.write(packet.payload)
    except KeyboardInterrupt:
        pass


    check()
    exit(0)
