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

    def recv(self, bufsize=8192):
        pass

    def send(self, data):
        pass


class ArraySocket(Socket):
    def __init__(self, array):
        super().__init__()
        self.array = array
        self.index = 0

    def recv(self, bufsize=8192):
        if self.index < len(self.array):
            data = self.array[self.index]
            self.index += 1
            return data.as_bytes()
        raise ConnectionResetError()

    def send(self, data):
        print('Writing data', data)


class DebugSocket(Socket):
    def __init__(self, socket):
        super().__init__()
        self.socket = socket

    def recv(self, bufsize=8192):
        packet = self.socket.recv(bufsize)
        print(self, 'recv', packet)
        return packet

    def send(self, data):
        print(self, 'send', data)
        return self.socket.send(data)


class SenderSlideWindow:
    def __init__(self, size):
        self.size = size
        self.buf = [None] * size
        self.write = 0
        self.confirmed = 0

    def get_packet(self, index):
        if self.confirmed <= index < self.write:
            packet = self.buf[index % self.size]
            return packet

    def put_packet(self, packet):
        self.buf[self.write % self.size] = packet
        self.write += 1

    def update_confirmed(self, index):
        self.confirmed = min(self.write, max(self.confirmed, index))


class ReceiverSlideWindow:
    def __init__(self, size):
        self.size = size
        self.buf = [None] * size
        self.read = 0
        self.confirmed = 0

    def get_packet(self):
        if self.read == self.confirmed:
            return None

        self.read += 1
        packet = self.buf[self.read % self.size]
        self.buf[self.read % self.size] = None
        return packet

    def put_packet(self, packet):
        if self.read <= packet.packet_id <= self.read + self.size:
            self.buf[packet.packet_id % self.size] = packet

            for i in range(self.confirmed + 1, self.read + self.size):
                if self.buf[i % self.size]:
                    self.confirmed += 1
                else:
                    break


class Protocol(Socket):
    def __init__(self, socket: Socket, server):
        super().__init__()
        self.send_window = SenderSlideWindow(10)
        self.send_window.read = self.send_window.write = rng()
        self.recv_window = None
        self.socket = socket
        self.handshaking = True
        self.open = True

        if not server:
            print("Handshaking initiated on client side")
            while self.handshaking:
                self.send_window.put_packet(WindowPacket(self.send_window.write, 10))
                self.flush()
                self.recv()

    def recv(self, bufsize=8192):
        try:
            data = self.socket.recv(bufsize)
        except IOError as ex:
            if ex.errno == 11:
                return self.try_receive()
            raise ex

        if not data:
            return self.try_receive()

        packet = ByteBuf(data=data)
        print('packet read:', packet)
        packet_type = packet.read_int()
        packet_class = PACKET_NAMES.get(packet_type)
        if not packet_class:
            print('packet type: unknown', packet_type)
            return

        packet = packet_class.from_bytes(packet)
        print('packet type:', packet_type, str(packet_class))

        if isinstance(packet, AckPacket):
            if self.handshaking:
                if packet.confirmed_id == self.send_window.write - 1:
                    print('Handshaking done')
                    self.handshaking = False
                else:
                    print('Handshaking error: incorrect packet id', packet.confirmed_id)
            else:
                pass
            self.send_window.update_confirmed(packet.confirmed_id)
        elif isinstance(packet, DataPacket):
            self.recv_window.put_packet(packet)
            self.socket.send(AckPacket(self.recv_window.confirmed).as_bytes())
        elif isinstance(packet, WindowPacket):
            self.recv_window = ReceiverSlideWindow(packet.window_size)
            self.recv_window.put_packet(packet)

            print('new window size on the other end:', packet.window_size)
            self.socket.send(AckPacket(self.recv_window.confirmed).as_bytes())

            if self.handshaking:
                self.send_window.put_packet(WindowPacket(self.send_window.write, self.send_window.size))
        self.flush()

        return self.try_receive()

    def try_receive(self):
        if self.recv_window:
            packet = self.recv_window.get_packet()
            if isinstance(packet, DataPacket):
                return packet.data

        return None

    def flush(self):
        for i in range(self.send_window.confirmed + 1, self.send_window.write):
            packet = self.send_window.get_packet(i)
            self.socket.send(packet.as_bytes())

    def send(self, data):
        i = 0
        size = 512
        length = len(data)
        while i < length:
            self.send_window.put_packet(DataPacket(self.send_window.write, data[i: i + size]))
            i += size
        self.flush()


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
    protocol = Protocol(socket, True)
    while True:
        protocol.recv()


def test_send_data():
    global now, rng
    now = itertools.count(start=1, step=1)
    rng = lambda: 1
    socket = ArraySocket([
        WindowPacket(1, 10),
        AckPacket(1),
        DataPacket(2, b'hello')
    ])
    protocol = Protocol(socket, True)
    while True:
        if data := protocol.recv():
            print(data)


def real_udp_connections():
    global now, rng
    now = itertools.count(start=1, step=1)
    rng = lambda: 1
    import socket

    SERVER_IP = "127.0.0.1"
    SERVER_PORT = 5005

    CLIENT_IP = "127.0.0.1"
    CLIENT_PORT = 5006

    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.setblocking(False)
    server.bind(('0.0.0.0', SERVER_PORT))
    server.connect((CLIENT_IP, CLIENT_PORT))
    server_protocol = Protocol(DebugSocket(server), server=True)

    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.setblocking(False)
    client.bind(('0.0.0.0', CLIENT_PORT))
    client.connect((SERVER_IP, SERVER_PORT))
    client_protocol = Protocol(DebugSocket(client), server=True)

    print('Handshaking on client side')
    client_protocol.send_window.put_packet(WindowPacket(client_protocol.send_window.write, 10))
    client_protocol.flush()

    print(server_protocol.recv())

    print(client_protocol.recv())

    print(client_protocol.recv())

    print(server_protocol.recv())

    client_protocol.send(b'hello')

    print(server_protocol.recv())
    print(server_protocol.recv())


if __name__ == '__main__':
    real_udp_connections()
