"""
This file defines your RDT protocol
"""
import udt

pkt_buffer = []    # The sender's packet buffer


def send(sock, rcv_addr):
    """
    This function implements the RDT send
    :param sock: Send data to this socket
    :param rcv_addr:  The socket of the receiver
    """
    global pkt_buffer

    total_num = len(pkt_buffer)
    print('Total # packet: ', total_num)

    for pkt in pkt_buffer:
        udt.send(sock, rcv_addr, pkt)

