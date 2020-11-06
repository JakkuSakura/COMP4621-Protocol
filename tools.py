import threading
mutex = threading.Lock()

def print_info(*args):
    with mutex:
        print(*args)


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
        return bytes(data)

    def write_data(self, data):
        l = len(data)
        self.write_int(l)
        self.buffer[self.write: self.write + l] = data
        self.write += l

    def as_bytes(self):
        return bytes(self.buffer[self.read: self.write])

    def read_bytes(self):
        data = self.buffer[self.read: self.write]
        self.read = self.write
        return bytes(data)

    def checksum(self):
        mask = (1 << 16) - 1
        sum = 0
        for i in range(self.read, self.write):
            sum = sum * 256 + self.buffer[i]
            sum = (sum >> 16) + sum & mask
        return sum & mask

    def __str__(self):
        return str(self.as_bytes())

