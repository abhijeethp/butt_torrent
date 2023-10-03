import socket
import json
import threading
import time
import random
import os
import hashlib
from collections import Counter
from dataclasses import asdict

from constants import BUFFER_SIZE, SERVER_HOST, SERVER_PORT, CLIENT_PORT_START, CHUNK_SIZE
from request_type import RequestType

from dto import RegisterReq, RegisterResp
from dto import FileListReq, FileListResp
from dto import FileLocationsReq, FileLocationsResp
from dto import ChunkRegisterReq, ChunkRegisterResp
from dto import ChunkDownloadReq


def find_unused_port(start=CLIENT_PORT_START, end=9998):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((SERVER_HOST, port))
                return port
            except OSError:
                pass
    raise Exception(f"No port available in the range(${start}, ${end}).")


class Client:

    # TODO: close the connection that i am opening here
    def __init__(self, dir_name):
        port = find_unused_port()
        self.endpoint = (SERVER_HOST, port)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind(self.endpoint)
        self.s.listen(5)

        threading.Thread(target=self.run).start()

        self.mount_dir = f"storage/{dir_name}"
        self.mount()
        self.download_progress = {}

    def run(self):
        self.log(f"Client running on {self.endpoint[0]}:{self.endpoint[1]}")
        while True:
            conn, addr = self.s.accept()
            threading.Thread(target=self.handle_request, args=(conn,)).start()

    def handle_request(self, conn):
        data = conn.recv(BUFFER_SIZE).decode()
        req = json.loads(data)
        request_type = RequestType(req.pop('type'))

        if request_type != RequestType.CHUNK_DOWNLOAD:
            # TODO - return error or throw error
            return

        self.upload_chunk(conn, req)
        conn.close()

    def mount(self):
        self.log(f"Mounted {self.mount_dir}")
        file_names = os.listdir(self.mount_dir)
        file_paths = [os.path.join(self.mount_dir, f) for f in file_names]

        files = [f for f in file_paths if os.path.isfile(f)]

        def file_meta(f):
            file_name = os.path.basename(f)
            file_length = os.path.getsize(f)
            num_chunks = -(-file_length // CHUNK_SIZE)

            return {
                "name": file_name,
                "length": file_length,
                "hashes": [self.hash(self.chunk_data(file_name, i)) for i in range(num_chunks)]
            }

        files = [file_meta(f) for f in files]
        if len(files) > 0:
            self.register(files)

    def register(self, files):
        resp = self.request_server(RegisterReq(endpoint=self.endpoint, files=files))
        resp = RegisterResp(**resp)
        self.log(resp.status)

    def file_list(self):
        resp = self.request_server(FileListReq())
        resp = FileListResp(**resp)
        self.log(resp.status, ",", resp.files)
        return resp

    def file_locations(self, file_name) -> FileLocationsResp:
        resp = self.request_server(FileLocationsReq(file_name=file_name))
        resp = FileLocationsResp(**resp)
        self.log(resp.status, ",", resp.endpoints)
        return resp

    def register_chunk(self, file_name, chunk):
        response = self.request_server(ChunkRegisterReq(endpoint=self.endpoint, file_name=file_name, chunk=chunk))
        response = ChunkRegisterResp(**response)
        self.log(response.status)

    def download_file(self, file_name):
        self.log(f"Downloading file {file_name}")

        files = self.file_list().files
        file_length = next((f['length'] for f in files if f['name'] == file_name), None)
        self.download_progress[file_name] = {'downloaded': 0, 'total': -(-file_length // CHUNK_SIZE)}
        self.create_empty_file(file_name, file_length)

        file_locations = self.file_locations(file_name)
        endpoints = file_locations.endpoints
        chunk_counts = Counter(chunk for chunks in endpoints.values() for chunk in chunks)
        rarest_chunks = sorted(chunk_counts, key=chunk_counts.get)

        concurrency = 4
        semaphore = threading.Semaphore(concurrency)

        for chunk in rarest_chunks:
            threading.Thread(target=self.download_chunk, args=(file_name, chunk, semaphore)).start()

        while self.get_download_progress(file_name) < 100:
            time.sleep(1)

        self.log(f"File {file_name} downloaded successfully.")

    def create_empty_file(self, file_name, length):
        file_path = os.path.join(self.mount_dir, file_name)
        with open(file_path, 'wb') as file:
            file.write(b'\x00' * length)

    def download_chunk(self, file_name, chunk, semaphore):
        with semaphore:
            file_locations = self.file_locations(file_name)
            peers_with_chunk = [p for p, c in file_locations.endpoints.items() if chunk in c]
            while True:
                if len(peers_with_chunk) <= 0:
                    msg = f"No more valid peers with chunk {chunk} of {file_name}."
                    self.log(msg)
                    raise ValueError(msg)

                peer = random.choice(peers_with_chunk)
                peers_with_chunk.remove(peer)
                expected_hash = file_locations.hashes[chunk]
                from_host, from_port = peer.split(":")
                from_endpoint = (from_host, int(from_port))
                request = ChunkDownloadReq(file_name=file_name, chunk=chunk)
                self.log(f"Downloading {file_name}[{chunk}] from {from_endpoint}")
                chunk_data = self.send_request(from_endpoint, request)

                if self.hash(chunk_data) == expected_hash:
                    break

                self.log(f"Integrity Check Failed for chunk {chunk} of {file_name} from {from_endpoint}. Discarding...")

            file_path = os.path.join(self.mount_dir, file_name)
            with open(file_path, 'r+b') as file:
                file.seek(chunk * CHUNK_SIZE)
                file.write(chunk_data)

            self.register_chunk(file_name, chunk)
            self.download_progress[file_name]['downloaded'] += 1

    def get_download_progress(self, file_name):
        progress = self.download_progress.get(file_name)
        prcnt = round((progress['downloaded'] / progress['total']) * 100, 2)
        return prcnt

    def upload_chunk(self, conn, req):
        req = ChunkDownloadReq(**req)
        chunk_data = self.chunk_data(req.file_name, req.chunk)
        conn.send(chunk_data)

    def chunk_data(self, file_name, chunk):
        file_path = os.path.join(self.mount_dir, file_name)
        with open(file_path, 'rb') as f:
            f.seek(chunk * CHUNK_SIZE)
            chunk_data = f.read(CHUNK_SIZE)
        return chunk_data

    def hash(self, data):
        return hashlib.sha1(data).hexdigest()

    def request_server(self, request):
        endpoint = (SERVER_HOST, SERVER_PORT)
        response_data = self.send_request(endpoint, request).decode()
        return json.loads(response_data)

    def send_request(self, endpoint, request):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(endpoint)
            s.send(json.dumps(asdict(request)).encode())
            response_data = s.recv(BUFFER_SIZE)
            return response_data

    def log(self, *args):
        print(args)
        return
