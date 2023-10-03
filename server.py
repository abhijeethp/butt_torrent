import socket
import threading
import json
from dataclasses import asdict, dataclass, field

from constants import BUFFER_SIZE, CHUNK_SIZE, SERVER_HOST, SERVER_PORT
from request_type import RequestType
from reponse_status import SUCCESS

from dto import RegisterReq, RegisterResp
from dto import FileListReq, FileListResp
from dto import FileLocationsReq, FileLocationsResp
from dto import ChunkRegisterReq, ChunkRegisterResp


class Server:

    # TODO: close the connection that i am opening here
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((SERVER_HOST, SERVER_PORT))
        self.s.listen(5)

        self.file_info = {}
        threading.Thread(target=self.run).start()

    def run(self):
        print(f"Server running on {SERVER_HOST}:{SERVER_PORT}")
        while True:
            conn, addr = self.s.accept()
            threading.Thread(target=self.handle_request, args=(conn,)).start()

    def handle_request(self, conn):
        data = conn.recv(BUFFER_SIZE).decode()
        req = json.loads(data)
        request_type = RequestType(req.pop('type'))

        handlers = {
            RequestType.REGISTER: self.register,
            RequestType.FILE_LIST: self.file_list,
            RequestType.FILE_LOCATIONS: self.file_locations,
            RequestType.CHUNK_REGISTER: self.register_chunk
        }

        response = handlers[request_type](req)

        conn.send(json.dumps(asdict(response)).encode())
        conn.close()

    def register(self, req) -> RegisterResp:
        req = RegisterReq(**req)
        host, port = req.endpoint

        for file in req.files:
            name, length, hashes = file["name"], file["length"], file["hashes"]
            num_chunks = -(-length // CHUNK_SIZE)
            chunks = list(range(num_chunks))

            if name in self.file_info:
                self.file_info[name]["chunks"] = {f"{host}:{port}": chunks}
                continue

            self.file_info[name] = {
                "length": length,
                "chunks": {f"{host}:{port}": chunks},
                "hashes": hashes
            }
            print(f"Registered : {name}({length}): -> {host}:{port}")
        return RegisterResp(status=SUCCESS)

    def file_list(self, req) -> FileListResp:
        files = []
        for name, info in self.file_info.items():
            files.append({"name": name, "length": info["length"]})
        return FileListResp(status=SUCCESS, files=files)

    def file_locations(self, req) -> FileLocationsResp:
        req = FileLocationsReq(**req)
        file_name = req.file_name
        endpoints = self.file_info[file_name]["chunks"]
        hashes = self.file_info[file_name]["hashes"]
        return FileLocationsResp(status=SUCCESS, endpoints=endpoints, hashes=hashes)

    def register_chunk(self, req) -> ChunkRegisterResp:
        req = ChunkRegisterReq(**req)

        host, port = req.endpoint
        file_name = req.file_name
        chunk = req.chunk

        self.file_info[file_name]["chunks"].setdefault(f"{host}:{port}", [])
        existing_chunks = self.file_info[file_name]["chunks"][f"{host}:{port}"]
        existing_chunks = set(existing_chunks)
        existing_chunks.add(chunk)
        existing_chunks = list(existing_chunks)
        self.file_info[file_name]["chunks"][f"{host}:{port}"] = existing_chunks

        print(f"Registered : Chunk {chunk} of file {file_name} present with {host}:{port}")
        return ChunkRegisterResp(status=SUCCESS)

if __name__ == '__main__':
    s = Server()