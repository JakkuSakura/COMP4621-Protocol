from tools import ByteBuf

class Packet:
    def __init__(self):
        pass

    def as_bytes(self):
        pass


class AckPacket(Packet):
    ID = 0x01

    def __init__(self, confirmed_id):
        super().__init__()
        self.confirmed_id = confirmed_id

    def as_bytes(self):
        buf = ByteBuf()
        buf.write_int(AckPacket.ID)
        buf.write_int(self.confirmed_id)
        return buf.as_bytes()

    @staticmethod
    def from_bytes(data):
        return AckPacket(data.read_int())

    def __repr__(self):
        return f'AckPacket({self.confirmed_id})'


class ClosePacket(Packet):
    ID = 0x02

    def __init__(self):
        super().__init__()

    def as_bytes(self):
        buf = ByteBuf()
        buf.write_int(ClosePacket.ID)
        return buf.as_bytes()

    @staticmethod
    def from_bytes(data):
        return ClosePacket()

    def __repr__(self):
        return 'ClosePacket()'


class DataPacket(Packet):
    ID = 0x03

    def __init__(self, packet_id, data):
        super().__init__()
        self.packet_id = packet_id
        self.data = data

    def as_bytes(self):
        buf = ByteBuf()
        buf.write_int(DataPacket.ID)
        buf.write_int(self.packet_id)
        buf.write_data(self.data)
        return buf.as_bytes()

    @staticmethod
    def from_bytes(data):
        return DataPacket(data.read_int(), data.read_data())

    def __repr__(self):
        return f'DataPacket({self.packet_id})'


class WindowPacket:
    ID = 0x04

    def __init__(self, window_size):
        self.window_size = window_size

    def as_bytes(self):
        buf = ByteBuf()
        buf.write_int(WindowPacket.ID)
        buf.write_int(self.window_size)
        return buf.as_bytes()

    @staticmethod
    def from_bytes(data):
        return WindowPacket(data.read_int())

    def __repr__(self):
        return f'WindowPacket({self.window_size})'


PACKET_NAMES = {AckPacket.ID: AckPacket,
                ClosePacket.ID: ClosePacket,
                DataPacket.ID: DataPacket,
                WindowPacket.ID: WindowPacket}