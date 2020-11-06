import time
import random
import itertools
import socket
import threading
from packet import *
from adaptors import Socket
from tools import print_info

now = time.time
rng = lambda: random.randint(0, 1000000)


class SenderSlideWindow:
    def __init__(self, size):
        self.size = size
        self.buf = [None] * size
        self.write = -1
        self.confirmed = -1

    def get_packet(self, index):
        if self.confirmed < index <= self.write:
            packet = self.buf[index % self.size]
            return packet

    def put_packet(self, packet):
        self.write += 1
        packet.seq_num = self.write
        self.buf[self.write % self.size] = packet
        return packet

    def update_confirmed(self, index):
        self.confirmed = min(self.write, max(self.confirmed, index))


class ReceiverSlideWindow:
    def __init__(self, size):
        self.size = size
        self.buf = [None] * size
        self.read = 0
        self.confirmed = -1

    def get_packet(self):
        if self.read > self.confirmed:
            return None

        packet = self.buf[self.read % self.size]
        self.buf[self.read % self.size] = None
        self.read += 1
        return packet

    def put_packet(self, packet):
        if self.read <= packet.seq_num <= self.read + self.size:
            self.buf[packet.seq_num % self.size] = packet

            for i in range(self.confirmed + 1, self.read + self.size):
                if self.buf[i % self.size]:
                    self.confirmed += 1
                else:
                    break


class Protocol(Socket):
    def __init__(self, socket: Socket, name='Protocol', segment_size=512):
        super().__init__()
        self.send_window = SenderSlideWindow(10000)
        self.recv_window = ReceiverSlideWindow(10000)
        self.socket = socket
        self.open = True
        self.handler = self.normal_handler
        self.name = name
        self.last_ack_time = now()
        self.handshake_timeout = 1
        self.resend_timeout = 1
        self.segment_size = segment_size

    def _send(self, packet, buffer=False):
        packet.ack_num = self.recv_window.confirmed
        if not buffer:
            print_info(self.name, 'sending', packet)
            self.socket.send(packet.encode())
        else:
            packet = self.send_window.put_packet(packet)
            print_info(self.name, 'buffered', packet)

    def _recv(self):
        if not self.open:
            raise ConnectionResetError('Connection reset')

        try:
            data = self.socket.recv(8192)
        except IOError as ex:
            if ex.errno == 11:
                return
            raise ex
        if not data:
            return

        packet = Packet().decode(data)
        if packet.chk_sum != packet.compute_checksum():
            return

        print_info(self.name, 'received', packet)
        return packet

    def recv(self, bufsize=8192):
        packet = self.try_receive()
        if packet:
            return packet

        self.handler(self._recv())

        return self.try_receive()

    def normal_handler(self, packet):
        if now() - self.last_ack_time > self.resend_timeout:
            self.last_ack_time = now()
            self._flush()

        if not packet:
            return

        if packet.seq_num == -1:
            self.open = False
            return self.try_receive()

        self.last_ack_time = now()
        self.send_window.update_confirmed(packet.ack_num)

        if packet.payload:
            self.recv_window.put_packet(packet)
            self._send(Packet(ack_num=self.recv_window.confirmed))

    def try_receive(self):
        packet = self.recv_window.get_packet()
        if packet and packet.payload:
            return packet.payload

        return None

    def flush(self):
        while self.open and self.send_window.confirmed < self.send_window.write:
            self._flush()
            while self.open and self.send_window.confirmed < self.send_window.write:
                data = self._recv()
                if not data:
                    break
                self.handler(data)

            time.sleep(self.resend_timeout)

    def _flush(self):
        self._send(Packet(ack_num=self.recv_window.confirmed))
        for i in range(self.send_window.confirmed + 1, self.send_window.write + 1):
            packet = self.send_window.get_packet(i)
            self._send(packet)

    def send(self, data):
        for i in range(0, len(data), self.segment_size):
            self._send(Packet(payload=data[i: i + self.segment_size]), buffer=True)

    def close(self):
        self._send(Packet(seq_num=-1))
        self.open = False


def test_byte_buf():
    buf = ByteBuf()
    buf.write_int(666)
    print_info(buf.read_int())
    buf.write_data(b'hello, world')
    print_info(buf.read_data())


SERVER_IP = "127.0.0.1"
SERVER_PORT = 5005

CLIENT_IP = "127.0.0.1"
CLIENT_PORT = 5006

print_count = 0

endpoint_mutex = threading.Lock()
yield_time = 0.1


def start_server():
    global print_count
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.setblocking(False)
    server.bind(('0.0.0.0', SERVER_PORT))
    server.connect((CLIENT_IP, CLIENT_PORT))
    server_protocol = Protocol(server, name='server')
    while server_protocol.open:
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
    client_protocol = Protocol(socket_f(client), name='client')
    return client_protocol


def two_ends():
    from adaptors import DropoutSocket
    server = threading.Thread(target=start_server, args=())
    server.setDaemon(True)
    server.start()
    client_protocol = start_client(lambda x: DropoutSocket(0.5, x))

    client_protocol.send(b'hello, world1')
    client_protocol.send(b'hello, world2')
    client_protocol.send(b'hello, world3')
    client_protocol.send(b'hello, world4')
    client_protocol.flush()

    client_protocol.close()
    print_info('done')


if __name__ == '__main__':
    two_ends()
