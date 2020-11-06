"""
This file defines the packet format
"""


class Packet:
    def __init__(self, payload=b"", seq_num=0, ack_num=0):
        """
        Constructor of class Packet
        :param payload: Data carried in this packet
        :param seq_num: Sequence number of this packet
        :param ack_num: ACK number of this packet
        """
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.payload = payload
        self.chk_sum = 0

    def encode(self):
        """
        Encode a packet into bytes
        :return: A byte stream
        """
        return b""

    def decode(self, packet):
        """
        Decode a packet from bytes
        :param packet: A packet in bytes
        :return: A Packet object
        """
        return self

    def compute_checksum(self):
        """
        Compute the checksum of a packet
        :return: The checksum of this packet
        """
        return 0

    def __str__(self):
        return f"{self.seq_num} {self.ack_num} {self.chk_sum} \n {self.payload.decode()}"


