import time
import random
import itertools


class ByteBuf:
    def __init__(self, size=8192, data=None):
        self.buffer = data or bytearray(size)
        self.size = (data and len(data)) or size
        self.read = 0
        self.write = data and len(data) or 0

    def read_int(self):
        i = int.from_bytes(self.buffer[self.read:self.read + 4], byteorder='big', signed=True)
        self.read += 4
        return i

    def write_int(self, val):
        self.buffer[self.write:self.write + 4] = val.to_bytes(4, byteorder='big', signed=True)
        self.write += 4

    def read_data(self):
        l = self.read_int()
        data = self.buffer[self.read: self.read + l]
        self.read += l
        return data

    def write_data(self, data):
        l = len(data)
        self.write_int(l)
        self.buffer[self.write: self.write + l] = data
        self.write += l

    def as_bytes(self):
        return self.buffer[self.read: self.write]

    def read_bytes(self):
        data = self.buffer[self.read: self.write]
        self.read = self.write
        return data

    def __str__(self):
        return str(self.as_bytes())


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


class NckPacket(Packet):
    ID = 0x02

    def __init__(self, confirmed_id):
        super().__init__()
        self.confirmed_id = confirmed_id

    def as_bytes(self):
        buf = ByteBuf()
        buf.write_int(NckPacket.ID)
        buf.write_int(self.confirmed_id)
        return buf.as_bytes()

    @staticmethod
    def from_bytes(data):
        return NckPacket(data.read_int())


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


class WindowPacket:
    ID = 0x04

    def __init__(self, packet_id, window_size):
        self.packet_id = packet_id
        self.window_size = window_size

    def as_bytes(self):
        buf = ByteBuf()
        buf.write_int(WindowPacket.ID)
        buf.write_int(self.packet_id)
        buf.write_int(self.window_size)
        return buf.as_bytes()

    @staticmethod
    def from_bytes(data):
        return WindowPacket(data.read_int(), data.read_int())


PACKET_NAMES = {AckPacket.ID: AckPacket,
                NckPacket.ID: NckPacket,
                DataPacket.ID: DataPacket,
                WindowPacket.ID: WindowPacket}
now = time.time
rng = lambda: random.randint(0, 1000000)


class ProtocolServer:
    def __init__(self):
        pass


class Socket:
    def __init__(self):
        pass

    def read(self):
        pass

    def write(self, data):
        pass

    def is_open(self):
        pass


class ArraySocket(Socket):
    def __init__(self, array):
        super().__init__()
        self.array = array
        self.index = 0

    def read(self):
        if self.index < len(self.array):
            data = self.array[self.index]
            self.index += 1
            return data.as_bytes()
        return None

    def write(self, data):
        print('Writing data', data)

    def is_open(self):
        return self.index < len(self.array)


class SlideWindow:
    def __init__(self, size):
        self.size = size
        self.buf = [None] * size
        self.write = 0
        self.read = 0
        self.confirmed = 0

    def in_range(self, id):
        return self.write - self.size <= id < self.write

    def get_packet(self, id):
        if not self.in_range(id):
            return None
        return self.buf[id % self.size]

    def put_packet(self, packet, auto_confirm):
        self.buf[self.write] = packet
        self.write += 1
        if auto_confirm:
            if self.confirmed == self.write - 2:
                self.confirmed = self.write
                return True
        return False


class Protocol(Socket):
    def __init__(self, socket: Socket):
        super().__init__()
        self.send_window = SlideWindow(10)
        self.send_window.read = self.send_window.write = rng()
        self.recv_window = None
        self.socket = socket
        self.handshaking = True

    def read(self):
        data = self.socket.read()
        if not data:
            return
        packet = ByteBuf(data=data)
        print('packet read:', packet)
        packet_type = packet.read_int()
        packet_class = PACKET_NAMES.get(packet_type)
        if not packet_class:
            print('packet type: unknown', packet_type)
            return

        packet = packet_class.from_bytes(packet)
        print('packet type:', packet_type, str(packet_class))

        result = None
        if isinstance(packet, AckPacket):
            if self.handshaking:
                if packet.confirmed_id == self.send_window.write - 1:
                    print('Handshaking done')
                    self.handshaking = False
                else:
                    print('Handshaking error: incorrect packet id', packet.confirmed_id)
            else:
                pass
        elif isinstance(packet, NckPacket):
            self.send_window.read = packet.confirmed_id
        elif isinstance(packet, DataPacket):
            if self.recv_window.put_packet(packet, True):
                self.socket.write(AckPacket(self.recv_window.confirmed).as_bytes())
                result = packet.data
            else:
                self.socket.write(NckPacket(self.recv_window.confirmed).as_bytes())
        elif isinstance(packet, WindowPacket):
            self.recv_window = SlideWindow(packet.window_size)
            self.recv_window.put_packet(packet, True)

            print('new window size on the other end:', packet.window_size)
            self.socket.write(AckPacket(self.recv_window.confirmed).as_bytes())
            self.send_window.put_packet(WindowPacket(self.recv_window.write, self.send_window.size), False)
        self.flush()

        return result

    def flush(self):
        for i in range(self.send_window.read, self.send_window.write):
            packet = self.send_window.get_packet(i)
            self.socket.write(packet.as_bytes())
        self.send_window.read = self.send_window.write

    def write(self, data):
        pass

    def is_open(self):
        return self.socket.is_open()


def test_byte_buf():
    buf = ByteBuf()
    buf.write_int(666)
    print(buf.read_int())
    buf.write_data(b'hello, world')
    print(buf.read_data())


def test_handshaking():
    global now, rng
    now = itertools.count(start=1, step=1)
    rng = lambda: 1
    socket = ArraySocket([
        WindowPacket(1, 10),
        AckPacket(1)
    ])
    protocol = Protocol(socket=socket)
    while protocol.is_open():
        protocol.read()


def test_send_data():
    global now, rng
    now = itertools.count(start=1, step=1)
    rng = lambda: 1
    socket = ArraySocket([
        WindowPacket(1, 10),
        AckPacket(1),
        DataPacket(2, b'hello')
    ])
    protocol = Protocol(socket=socket)
    while protocol.is_open():
        if data := protocol.read():
            print(data)


if __name__ == '__main__':
    test_send_data()
