from tools import ByteBuf


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

    def encode(self, get_bytes=True):
        """
        Encode a packet into bytes
        :return: A byte stream
        """
        self.compute_checksum()

        buf = ByteBuf()
        buf.write_int(self.seq_num)
        buf.write_int(self.ack_num)
        buf.write_int(self.chk_sum)
        buf.write_data(self.payload)

        if get_bytes:
            return buf.as_bytes()
        else:
            return buf

    def decode(self, packet):
        """
        Decode a packet from bytes
        :param packet: A packet in bytes
        :return: A Packet object
        """
        buf = ByteBuf(packet)
        self.seq_num = buf.read_int()
        self.ack_num = buf.read_int()
        self.chk_sum = buf.read_int()
        self.payload = buf.read_data()
        return self

    def compute_checksum(self):
        """
        Compute the checksum of a packet
        :return: The checksum of this packet
        """

        buf = ByteBuf()
        buf.write_int(self.seq_num)
        buf.write_int(self.ack_num)
        buf.write_int(0)
        buf.write_data(self.payload)
        self.chk_sum = buf.checksum()

        return self.chk_sum

    def __str__(self):
        return f"Packet seq={self.seq_num} ack={self.ack_num} chk={self.chk_sum} payload={self.payload[:20]}"
