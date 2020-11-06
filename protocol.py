import time
import random
import itertools
import socket
import threading
from packet import *

mutex = threading.Lock()
def print_info(*args):
    with mutex:
        print(*args)


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
        print_info('Writing data', data)


class DebugSocket(Socket):
    def __init__(self, socket):
        super().__init__()
        self.socket = socket

    def recv(self, bufsize=8192):
        packet = self.socket.recv(bufsize)
        print_info(self, 'recv', packet)
        return packet

    def send(self, data):
        print_info(self, 'send', data)
        return self.socket.send(data)


class DropoutSocket(Socket):
    def __init__(self, drop_rate, socket):
        super().__init__()
        self.socket = socket
        self.drop_rate = drop_rate

    def recv(self, bufsize=8192):
        packet = self.socket.recv(bufsize)
        if random.random() > self.drop_rate:
            return packet
        else:
            print_info("Dropped received packet", packet)
            return None

    def send(self, data):
        if random.random() > self.drop_rate:
            return self.socket.send(data)
        else:
            print_info("Dropped sending packet", data)


class DisorderSocket(Socket):
    def __init__(self, bufsize, socket):
        super().__init__()
        self.socket = socket
        self.bufsize = bufsize
        self.recv_buf = []
        self.send_buf = []
        self.releasing = False

    def recv(self, bufsize=8192):
        if not self.releasing:
            packet = self.socket.recv(bufsize)
            if packet:
                self.recv_buf.append(packet)
                if len(self.recv_buf) >= self.bufsize:
                    self.releasing = True
                    random.shuffle(self.recv_buf)
                    return self.recv_buf.pop()

            return None
        else:
            value = self.recv_buf.pop()
            if len(self.recv_buf) == 0:
                self.releasing = False
            return value

    def send(self, data):
        if not self.releasing:
            self.recv_buf.append(data)
            if len(self.recv_buf) >= self.bufsize:
                self.releasing = True
                random.shuffle(self.recv_buf)
                return self.recv_buf.pop()

            return None
        else:
            packet = self.recv_buf.pop()
            return self.socket.send(packet)


class SenderSlideWindow:
    def __init__(self, size):
        self.size = size
        self.buf = [None] * size
        self.write = 0
        self.confirmed = 0

    def get_packet(self, index):
        if self.confirmed < index <= self.write:
            packet = self.buf[index % self.size]
            return packet

    def put_packet(self, packet):
        self.write += 1
        packet.packet_id = self.write
        self.buf[self.write % self.size] = packet
        return packet

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
    def __init__(self, socket: Socket, server, name='Protocol'):
        super().__init__()
        self.send_window = SenderSlideWindow(10)
        self.recv_window = ReceiverSlideWindow(10)
        self.socket = socket
        self.open = True
        self.handler = self.handshaking_handler
        self.name = name
        self.last_ack_time = now()
        self.handshake_timeout = 1
        self.resend_timeout = 1
        self.handshake_received = False
        if not server:
            print_info(self.name, "Handshaking initiated")
            while self.handler == self.handshaking_handler:
                self._send(WindowPacket(self.recv_window.size))
                self.recv()
                time.sleep(.3)

    def _send(self, data, buffer=False):
        if not buffer:
            print_info(self.name, 'sending', data)
            self.socket.send(data.as_bytes())
        else:
            packet = self.send_window.put_packet(data)
            print_info(self.name, 'buffered', packet)

    def _recv(self):
        try:
            data = self.socket.recv(8192)
        except IOError as ex:
            if ex.errno == 11:
                return
            raise ex

        if not data:
            return
        packet = ByteBuf(data=data)
        # print_info(self.name, 'packet read:', packet)
        packet_type = packet.read_int()
        packet_class = PACKET_NAMES.get(packet_type)
        if not packet_class:
            print_info(self.name, 'packet type: unknown', packet_type)
            return

        packet = packet_class.from_bytes(packet)
        print_info(self.name, 'received', packet)
        return packet

    def recv(self, bufsize=8192):
        if not self.open:
            raise ConnectionResetError('Connection reset')
        return self.handler() or b''

    def handshaking_handler(self):
        if self.handshake_received and now() - self.last_ack_time > self.handshake_timeout:
            print_info(self.name, 'Timeout. Retry sending handshake data')
            self._send(AckPacket(self.recv_window.confirmed))
            self._send(WindowPacket(self.recv_window.size))

        packet = self._recv()
        if not packet:
            self.flush()
            return

        if isinstance(packet, AckPacket):
            self.last_ack_time = now()
            print_info(self.name, 'Handshaking done, switching to normal mode')
            self.handler = self.normal_handler
            self.send_window.update_confirmed(packet.confirmed_id)
        elif isinstance(packet, WindowPacket):
            print_info(self.name, 'recv window size on the other end:', packet.window_size)
            self._send(AckPacket(self.recv_window.confirmed))
            self._send(WindowPacket(self.recv_window.size))
        elif isinstance(packet, ClosePacket):
            self.open = False
        else:
            print_info(self.name, 'Unwanted packet type')

        self.flush()
        return None

    def normal_handler(self):
        if now() - self.last_ack_time > self.resend_timeout:
            print_info(self.name, 'Timeout. Retry sending unconfirmed data')
            self._send(AckPacket(self.recv_window.confirmed))
            self.flush()

        packet = self._recv()
        if not packet:
            return self.try_receive()

        if isinstance(packet, AckPacket):
            self.last_ack_time = now()
            self.send_window.update_confirmed(packet.confirmed_id)
        elif isinstance(packet, DataPacket):
            self.recv_window.put_packet(packet)
            self._send(AckPacket(self.recv_window.confirmed))
        elif isinstance(packet, WindowPacket):
            print_info(self.name, 'recv window size on the other end:', packet.window_size)
            self._send(AckPacket(self.recv_window.confirmed))
        else:
            print_info(self.name, 'Unwanted packet type')

        self.flush()
        return self.try_receive()

    def try_receive(self):
        packet = self.recv_window.get_packet()
        if isinstance(packet, DataPacket):
            return packet.data

        return None

    def flush(self):
        for i in range(self.send_window.confirmed + 1, self.send_window.write + 1):
            packet = self.send_window.get_packet(i)
            self._send(packet)

    def send(self, data):
        i = 0
        size = 512
        length = len(data)
        while i < length:
            self._send(DataPacket(0, data[i: i + size]), buffer=True)
            i += size


def test_byte_buf():
    buf = ByteBuf()
    buf.write_int(666)
    print_info(buf.read_int())
    buf.write_data(b'hello, world')
    print_info(buf.read_data())


def test_handshaking():
    global now, rng
    now = itertools.count(start=1, step=1)
    rng = lambda: 1
    socket = ArraySocket([
        WindowPacket(10),
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
        WindowPacket(10),
        AckPacket(1),
        DataPacket(2, b'hello')
    ])
    protocol = Protocol(socket, True)
    while True:
        if data := protocol.recv():
            print_info(data)


SERVER_IP = "127.0.0.1"
SERVER_PORT = 5005

CLIENT_IP = "127.0.0.1"
CLIENT_PORT = 5006


def real_udp_connections():
    global now, rng
    now = itertools.count(start=1, step=1)
    rng = lambda: 1

    import socket

    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.setblocking(False)
    server.bind(('0.0.0.0', SERVER_PORT))
    server.connect((CLIENT_IP, CLIENT_PORT))
    server_protocol = Protocol(DebugSocket(server), server=True, name='server')

    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.setblocking(False)
    client.bind(('0.0.0.0', CLIENT_PORT))
    client.connect((SERVER_IP, SERVER_PORT))
    client_protocol = Protocol(DebugSocket(client), server=True, name='client')

    print_info('Handshaking on client side')
    client_protocol.socket.send(WindowPacket(client_protocol.recv_window.size).as_bytes())

    print_info(server_protocol.recv())

    print_info(client_protocol.recv())

    print_info(client_protocol.recv())

    print_info(server_protocol.recv())

    client_protocol.send(b'hello')

    print_info(server_protocol.recv())
    print_info(server_protocol.recv())


print_count = 0

endpoint_mutex = threading.Lock()
yield_time = 0.1


def start_server():
    global print_count
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.setblocking(False)
    server.bind(('0.0.0.0', SERVER_PORT))
    server.connect((CLIENT_IP, CLIENT_PORT))
    server_protocol = Protocol(server, server=True, name='server')
    while True:
        with endpoint_mutex:
            print_info("Server round")
            packet = server_protocol.recv()
            if packet:
                print_info('Server', packet)
                print_count += 1
        time.sleep(yield_time)


def start_client(socket_f):
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.setblocking(False)
    client.bind(('0.0.0.0', CLIENT_PORT))
    client.connect((SERVER_IP, SERVER_PORT))
    client_protocol = Protocol(socket_f(client), server=False, name='client')
    return client_protocol


def two_ends():
    server = threading.Thread(target=start_server, args=())
    server.setDaemon(True)
    server.start()
    client_protocol = start_client(lambda x: DropoutSocket(0.5, x))
    for i in range(10):
        client_protocol.recv()

    client_protocol.send(b'hello, world1')
    client_protocol.send(b'hello, world2')
    client_protocol.send(b'hello, world3')
    client_protocol.send(b'hello, world4')

    client_protocol.socket.drop_rate = 0.5
    client_protocol.flush()

    while print_count < 4:
        with endpoint_mutex:
            print_info("Client round")
            packet = client_protocol.recv()
            if packet:
                print_info(packet)
        time.sleep(yield_time)

    print_info('done')


if __name__ == '__main__':
    two_ends()
