#!/usr/bin/env python3

import sys, os
import time, struct
import socket
import hashlib

from settings import read_settings
from connection import Connection

__version__ = "0.0"

# settings
default_settings_str = """{
    # such as "wolfebox.example.com"
    "SERVER_NAME": "",
    "SERVER_PORT": 61086,

    # seconds between checks
    "CHECK_INTERVAL": 60,

    # list of directories to synchronize
    "DIRS": [
        ### "~" is expanded to the user directory (with os.path.expanduser)
        ### synchronizes ~/example/ with the remote name of "example"
        # "~/example",
        ### synchronizes ~/example/ with the remote name of "different-name"
        # ("~/example", "different-name"),
    ],
}
"""
(settings_dir, settings_path, settings) = read_settings("wolfebox", default_settings_str)
if settings["SERVER_NAME"] == "":
    sys.exit("ERROR: wolfebox is not configured properly. SERVER_NAME is blank.\nedit " + settings_path)
dirs = []
for maybe_tuple in settings["DIRS"]:
    if type(maybe_tuple) == tuple:
        path, name = maybe_tuple
    else:
        path = maybe_tuple
        name = os.path.split(maybe_tuple)[1]
    path = os.path.expanduser(path)
    dirs.append((path, name))
if len(dirs) == 0:
    sys.stderr.write("WARNING: no dirs have been configured for synchronization\n")

class IndexEntry:
    def __init__(self, path, md5sum, modified_time):
        """
        path : str - relative to the monitored directory
        md5sum : str - can be "-" for deleted entries
        modified_time : time.struct_time - such as from time.mktime() or time.gmtime()
        """
        self.path = path
        self.md5sum = md5sum
        self.modified_time = modified_time
    def serialize(self):
        return " ".join([
            self.md5sum,
            ":".join(str(x) for x in self.modified_time),
            self.path,
        ])

def main():
    try:
        while True:
            for (path, name) in dirs:
                check_dir(path, name)
            time.sleep(settings["CHECK_INTERVAL"])
    except (): #KeyboardInterrupt:
        print("")

def parse_index(index_contents):
    def parse_index_entry(line):
        (md5sum, modified_time_str, path) = line.split(" ", 2)
        modified_time = time.struct_time(tuple(int(x) for x in modified_time_str.split(":")))
        return IndexEntry(path, md5sum, modified_time)
    entry_list = [parse_index_entry(line) for line in index_contents.split("\n") if line != ""]
    return {entry.path: entry for entry in entry_list}

def get_index_path(name):
    return os.path.join(settings_dir, name + ".index")
def get_local_index(name):
    index_path = get_index_path(name)
    try:
        with open(index_path) as index_file:
            index_contents = index_file.read()
    except IOError:
        index_contents = ""
    return parse_index(index_contents)
    write_local_index(local_index)
def write_local_index(name, local_index):
    index_path = get_index_path(name)
    with open(index_path, "w") as index_file:
        for line in sorted(entry.serialize() for entry in local_index.values()):
            index_file.write(line)
            index_file.write("\n")

def list_recursive(root_path):
    """always uses forward slashes"""
    root_path = os.path.abspath(root_path)
    for (dirpath, dirnames, filenames) in os.walk(root_path):
        folder = dirpath[len(root_path + "/"):].replace("\\", "/")
        if folder != "":
            folder += "/"
        for filename in filenames:
            yield folder + filename

def get_modified_time(root_path, relative_path):
    """throws OSError sometimes"""
    return time.gmtime(os.path.getmtime(root_path + "/" + relative_path))
def get_md5sum(root_path, relative_path):
    """throws IOError sometimes"""
    with open(root_path + "/" + relative_path, "rb") as file_handle:
        md5erator = hashlib.md5()
        while True:
            chunk = file_handle.read(128)
            if len(chunk) == 0:
                break
            md5erator.update(chunk)
    return md5erator.hexdigest()
def entry_for_path(root_path, relative_path):
    try:
        modified_time = get_modified_time(root_path, relative_path)
        md5sum = get_md5sum(root_path, relative_path)
    except (IOError, OSError):
        # file is deleted
        modified_time = time.gmtime()
        md5sum = "-"
    return IndexEntry(relative_path, md5sum, modified_time)



def update_local_index(local_index, root_path):
    existing_paths = set(list_recursive(root_path))
    for existing_path in list(existing_paths):
        try:
            try:
                entry = local_index[existing_path]
            except KeyError:
                # new file
                local_index[existing_path] = entry_for_path(root_path, existing_path)
                debug("add " + existing_path)
                continue
            # updated or normal
            modified_time = get_modified_time(root_path, existing_path)
            if modified_time == entry.modified_time:
                continue # assume unchanged
            # timestamp is different. make sure md5sum is up to date.
            entry.md5sum = get_md5sum(root_path, existing_path)
            debug("update " + existing_path)
        except (IOError, OSError):
            # race conditions! deleted while we were md5sum'ing a previous neighbor
            local_index[existing_path] = entry_for_path(root_path, existing_path)
            existing_paths.remove(entry.path)
            continue

def check_dir(root_path, name):
    local_index = get_local_index(name)
    update_local_index(local_index, root_path)
    write_local_index(name, local_index)

    remote_index = get_remote_index(name)
    if remote_index == None:
        return


def get_remote_index(name):
    connection = open_connection()
    if connection == None:
        return None
    connection.write(b"l")
    connection.write_string(name)
    error_message = connection.check()
    if error_message != None:
        debug("ERROR: " + error_message)
        return None
    remote_index = connection.read_string()
    return remote_index
def open_connection():
    server_tuple = (settings["SERVER_NAME"], settings["SERVER_PORT"])
    actual_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        actual_connection.connect(server_tuple)
    except socket.error:
        debug("ERROR: Can't connect to the wolfebox server at " + repr(server_tuple))
        return None
    return Connection(actual_connection)


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
    main()


