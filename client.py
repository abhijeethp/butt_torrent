import socket
import json
from dataclasses import asdict
import os
import sys

from constants import BUFFER_SIZE, SERVER_HOST, SERVER_PORT, CLIENT_PORT_START
from dto import RegisterReq, RegisterResp
from dto import FileListReq, FileListResp
from dto import FileLocationsReq, FileLocationsResp
from dto import ChunkRegisterReq, ChunkRegisterResp

def find_unused_port(start=CLIENT_PORT_START, end=9998):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                pass
    raise Exception(f"No port available in the range(${start}, ${end}).")

def count_lines(filename):
    with open(filename, 'r') as f:
        return sum(1 for _ in f)


class Client:

    def __init__(self):
        port = find_unused_port()
        endpoint = (SERVER_HOST, port)
        self.endpoint = endpoint
        print(f"Client running on {endpoint[0]}:{endpoint[1]}")

    def send_request(self, request):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SERVER_HOST, SERVER_PORT))
            s.send(json.dumps(asdict(request)).encode())
            response_data = s.recv(BUFFER_SIZE).decode()
            return json.loads(response_data)

    def mount(self, dir_name):
        mount_dir = f"storage/{dir_name}"

        file_names = os.listdir(mount_dir)
        file_paths = [os.path.join(mount_dir, f) for f in file_names]

        files = [f for f in file_paths if os.path.isfile(f)]
        files = [{"name": os.path.basename(f), "length": count_lines(f)} for f in files]

        if len(files) > 0:
            self.register(files)

    def register(self, files):
        resp = self.send_request(RegisterReq(endpoint=self.endpoint, files=files))
        resp = RegisterResp(**resp)
        print(resp.status)

    def file_list(self):
        response = self.send_request(FileListReq())
        response = FileListResp(**response)
        print(response.status,",",response.files)

    def file_locations(self, file_name):
        response = self.send_request(FileLocationsReq(file_name=file_name))
        response = FileLocationsResp(**response)
        print(response.status,",",response.endpoints)

    def register_chunk(self, file_name, chunk):
        response = self.send_request(ChunkRegisterReq(endpoint=self.endpoint,file_name=file_name,chunk=chunk))
        response = ChunkRegisterResp(**response)
        print(response.status)

    def download_file(self, file_name):
        # TODO
        pass
