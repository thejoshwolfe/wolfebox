
class Connection:
    def __init__(self, actual_connection):
        self.connection = actual_connection
    def read(self, length):
        chunks = []
        while length != 0:
            chunk = self.connection.recv(length)
            if len(chunk) == 0:
                break
            chunks.append(chunk)
            length -= len(chunk)
        return "".join(chunks)
    def read_fmt(self, fmt):
        data = self.read(struct.calcsize(fmt))
        return struct.unpack(fmt, data)[0]
    def read_int(self):
        return self.read_fmt("I")
    def read_long(self):
        return self.read_fmt("Q")
    def read_string(self):
        length = self.read_int()
        return self.read(length)

    def write(self, data):
        self.connection.sendall(data)
    def write_fmt(self, fmt, value):
        data = struct.pack(fmt, value)
        self.write(data)
    def write_int(self, value):
        self.write_fmt("I", value)
    def write_long(self, value):
        self.write_fmt("Q", value)
    def write_string(self, value):
        self.write_int(len(value))
        self.write(value)

    def ok(self):
        self.write("w") # 'w' for "wolfebin"
