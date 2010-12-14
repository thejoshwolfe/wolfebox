
class Connection:
    def __init__(self, actual_connection):
        self.connection = actual_connection
    def __del__(self):
        self.connection.close()
    def read(self, length):
        chunks = []
        while length != 0:
            chunk = self.connection.recv(length)
            if len(chunk) == 0:
                break
            chunks.append(chunk)
            length -= len(chunk)
        return b"".join(chunks)
    def read_fmt(self, fmt):
        data = self.read(struct.calcsize(fmt))
        return struct.unpack(fmt, data)[0]
    def read_int(self):
        return self.read_fmt("I")
    def read_long(self):
        return self.read_fmt("Q")
    def read_string(self):
        length = self.read_int()
        return str(self.read(length), "utf8")

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
        value = bytes(value, "utf8")
        self.write_int(len(value))
        self.write(value)

    def ok(self):
        """sent by the server after all the parameters have been received and validated"""
        self.write(b"w") # 'w' for "wolfebin"
    def check(self):
        """read by the client"""
        status_code = self.read(1)
        if status_code == b"w":
            return None
        elif status_code == b"b":
            return self.read_string()
        else:
            return "fatal: corrupt network communication " + repr(status_code + self.read(0x10))

