import random
from tools import print_info


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
            return data.encode()
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
            print_info('Dropped received packet', packet)
            return None

    def send(self, data):
        if random.random() > self.drop_rate:
            return self.socket.send(data)
        else:
            print_info('Dropped sending packet', data)


class CorruptedSocket(Socket):
    def __init__(self, drop_rate, socket):
        super().__init__()
        self.socket = socket
        self.corrupt_rate = drop_rate

    def recv(self, bufsize=8192):
        packet = self.socket.recv(bufsize)
        if random.random() > self.corrupt_rate:
            return packet
        else:
            packet = bytearray(packet)
            print_info('Messing sending packet', packet)
            random.shuffle(packet)
            return packet

    def send(self, data):
        if random.random() > self.corrupt_rate:
            return self.socket.send(data)
        else:
            data = bytearray(data)
            print_info('Messing sending packet', data)
            random.shuffle(data)
            return self.socket.send(data)


class DisorderSocket(Socket):
    def __init__(self, flush_rate, socket):
        super().__init__()
        self.socket = socket
        self.flush_rate = flush_rate
        self.recv_buf = []
        self.send_buf = []
        self.releasing_recv = False

    def recv(self, bufsize=8192):
        packet = self.socket.recv(bufsize)
        if packet:
            self.recv_buf.append(packet)
        if random.random() < self.flush_rate:
            random.shuffle(self.recv_buf)
            return self.recv_buf.pop()

    def send(self, data):
        self.send_buf.append(data)
        if random.random() < self.flush_rate:
            random.shuffle(self.send_buf)
            packet = self.send_buf.pop()
            return self.socket.send(packet)


import udt
from packet import Packet


class UdtAdaptor(Socket):
    def __init__(self, sock, addr):
        super().__init__()
        self.sock = sock
        self.addr = addr

    def send(self, data):
        if self.addr:
            return udt.send(self.sock, self.addr, Packet().decode(data))

    def recv(self, bufsize=8192):
        packet, addr = udt.recv(self.sock)
        self.addr = addr
        return packet.encode()
