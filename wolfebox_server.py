#!/usr/bin/env python3

import sys
import threading
import socketserver

from settings import read_settings
from connection import Connection

__version__ = "0.0"

default_settings_str = """{
    # usually the IP address of this server. such as "192.168.1.1".
    "SERVER_NAME": "",
    "SERVER_PORT": 61086,

    # directory containing all wolfebox data
    "DATA_ROOT": "~/wolfebox_server",
}
"""
(settings_dir, settings_path, settings) = read_settings("wolfebox_server", default_settings_str)
if settings["SERVER_NAME"] == "":
    sys.exit("ERROR: wolfebox is not configured properly. SERVER_NAME is blank.\nedit " + settings_path)
files_dir = os.path.join(settings["DATA_ROOT"], "files")
if not os.path.isdir(files_dir):
    os.makedirs(files_dir)

def get_index_path(name):
    return os.path.join(settings_dir, name + ".index")

def read_file_or_blank(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except IOError:
        return ""

lock_map_lock = threading.RLock()
lock_map = {}
def get_lock(name):
    with lock_map_lock:
        try:
            return lock_map[name]
        except KeyError:
            lock = threading.RLock()
            lock_map[name] = lock
            return lock

def list(connection):
    name = connection.read_string()
    if name.find("/") != -1 or name.find("\x00") != -1:
        connection.write(b"b")
        connection.write_string("bad name")
        return
    connection.ok()
    index_path = get_index_path(name)
    with get_lock(name):
        contents = read_file_or_blank(index_path)
    connection.write_string(contents)

def server_forever():
    class ConnectionHandler(socketserver.BaseRequestHandler):
        def handle(self):
            connection = Connection(self.request)
            command = connection.read(1)
            if command == "l":
                list(connection)
            else:
                sys.stderr.write("bad command: " + repr(command) + "\n")
                connection.write(b"b")
                connection.write_string("you suck")
    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        pass
    server = ThreadedTCPServer((settings["SERVER_NAME"], settings["SERVER_PORT"]), ConnectionHandler)
    server.serve_forever()

verbose = True
def debug(message):
    if not verbose:
        return
    print(message)
if __name__ == "__main__":
    import optparse
    parser = optparse.OptionParser(version=__version__)
    parser.add_option("-v", "--verbose", action="store_true", default=False)
    (options, args) = parser.parse_args()
    verbose = options.verbose
    server_forever()

