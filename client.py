import socket
from collections import Counter
import json
import threading
from dataclasses import asdict
import os

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


    def run(self):
        print(f"Client running on {self.endpoint[0]}:{self.endpoint[1]}")
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
        print(f"Mounted {self.mount_dir}")
        file_names = os.listdir(self.mount_dir)
        file_paths = [os.path.join(self.mount_dir, f) for f in file_names]

        files = [f for f in file_paths if os.path.isfile(f)]
        files = [{"name": os.path.basename(f), "length": os.path.getsize(f)} for f in files]

        if len(files) > 0:
            self.register(files)

    def register(self, files):
        resp = self.request_server(RegisterReq(endpoint=self.endpoint, files=files))
        resp = RegisterResp(**resp)
        print(resp.status)

    def file_list(self):
        resp = self.request_server(FileListReq())
        resp = FileListResp(**resp)
        print(resp.status,",",resp.files)
        return resp

    def file_locations(self, file_name) -> FileLocationsResp:
        resp = self.request_server(FileLocationsReq(file_name=file_name))
        resp = FileLocationsResp(**resp)
        print(resp.status,",",resp.endpoints)
        return resp

    def register_chunk(self, file_name, chunk):
        response = self.request_server(ChunkRegisterReq(endpoint=self.endpoint, file_name=file_name, chunk=chunk))
        response = ChunkRegisterResp(**response)
        print(response.status)

    def download_file(self, file_name):
        print(f"Downloading file {file_name}")

        files = self.file_list().files
        file_length = next((f['length'] for f in files if f['name'] == file_name), None)
        self.create_empty_file(file_name, file_length)
        file_locations = self.file_locations(file_name).endpoints

        chunk_counts = Counter(chunk for chunks in file_locations.values() for chunk in chunks)
        rarest_chunks = sorted(chunk_counts, key=chunk_counts.get)

        concurrency_limit = 4
        semaphore = threading.Semaphore(concurrency_limit)

        def download_with_semaphore(from_endpoint, file_name, chunk):
            with semaphore:
                self.download_chunk(from_endpoint, file_name, chunk)

        threads = []
        for chunk in rarest_chunks:
            peer = next(peer for peer, chunks in file_locations.items() if chunk in chunks)
            from_host, from_port = peer.split(":")
            from_endpoint = (from_host, int(from_port))

            task = threading.Thread(target=download_with_semaphore, args=(from_endpoint, file_name, chunk))
            threads.append(task)

        for task in threads:
            task.start()

        for task in threads:
            task.join()

        print(f"File {file_name} downloaded successfully.")

    def create_empty_file(self, file_name, length):
        file_path = os.path.join(self.mount_dir, file_name)
        with open(file_path, 'wb') as file:
            file.write(b'\x00' * length)

    def download_chunk(self, from_endpoint, file_name, chunk):
        request = ChunkDownloadReq(file_name=file_name, chunk=chunk)
        chunk_data = self.send_request(from_endpoint, request)

        file_path = os.path.join(self.mount_dir, file_name)
        with open(file_path, 'r+b') as file:
            file.seek(chunk * CHUNK_SIZE)
            file.write(chunk_data)

        self.register_chunk(file_name, chunk)

    def upload_chunk(self, conn, req):
        req = ChunkDownloadReq(**req)
        file_path = os.path.join(self.mount_dir, req.file_name)
        with open(file_path, 'rb') as f:
            f.seek(req.chunk * CHUNK_SIZE)
            chunk_data = f.read(CHUNK_SIZE)
        conn.send(chunk_data)

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

