"""
This file defines the UDT send/receive interfaces
DO NOT modify this file
"""
from packet import Packet


def send(sock, addr, packet):
    """
    UDT send interface
    :param sock: A UDP socket
    :param addr: Receiver's IP address
    :param packet: Packet-to-send
    """
    print('<- Send packet', packet.seq_num)
    sock.sendto(packet.encode(), addr)


def recv(sock):
    """
    UDT receive interface
    :param sock:
    """
    pkt_byte, addr = sock.recvfrom(1024)
    packet = Packet().decode(pkt_byte)
    print('-> Receive ACK', packet.ack_num)
    return packet, addr
