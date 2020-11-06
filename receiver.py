"""
This file defines the receiver
"""

import getopt
import socket
import sys


from packet import Packet


def recv(sock):
    """
    Receive data from a given socket
    :param sock: The socket that the receiver receive data from.
    """

    global rcv_pkt_buffer
    print('Receiver is running.')
    ack_num = -1  # The initial value of the cumulative ACK
    while True:
        '''Receive data from a socket'''
        pkt_byte, snd_addr = sock.recvfrom(1024)

        '''Decode the received packet'''
        pkt = Packet().decode(pkt_byte)
        print('-> Receive packet', pkt.seq_num)

        '''Check whether the received pkt is correct and with the desired ACK number'''
        if (pkt.seq_num == ack_num + 1) & (pkt.chk_sum == pkt.compute_checksum()):
            ack_num += 1  # Update the cumulative ACK number
            f.write(pkt.payload)  # Write data to the file
            rcv_pkt_buffer.append(pkt)  # Write data to the receiver's buffer

        '''Send Ack to the sender'''
        ack_pkt = Packet(ack_num=ack_num)
        sock.sendto(ack_pkt.encode(), snd_addr)
        print('<- Send ACK', ack_pkt.ack_num)


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
sent_file_name = 'doc1.txt'  # File name of the sent file
payload_len = 512    # Payload length
rcv_pkt_buffer = []    # Buffer to store the received packets

if __name__ == '__main__':
    '''Parse command line arguments'''
    parse_args(sys.argv[1:])
    
    ''''Open file-to-write and a UDP socket'''
    f = open(file_name, 'wb+')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('localhost', 8080))
    
    '''Start the receiver'''
    try:
        with f, sock:
            recv(sock)
    except KeyboardInterrupt:
        check()
        exit(0)
