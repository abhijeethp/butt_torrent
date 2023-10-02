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
    def __init__(self, host: str, port: int):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host, self.port = host, port
        self.s.bind((host, port))
        self.s.listen(5)

        self.file_info = {}

    def register(self, req) -> RegisterResp:
        req = RegisterReq(**req)
        host, port = req.endpoint

        for file_meta in req.files:
            name, length = file_meta["name"], file_meta["length"]
            num_chunks = -(-length // CHUNK_SIZE)
            self.file_info[name] = {
                "length": length,
                "chunks": {f"{host}:{port}": list(range(num_chunks))}
            }
            print(f"Registered : {name}({length}): -> {host}:{port} -> {list(range(num_chunks))}")
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
        return FileLocationsResp(status=SUCCESS, endpoints=endpoints)

    def register_chunk(self, req) -> ChunkRegisterResp:
        req = ChunkRegisterReq(**req)

        host, port = req.endpoint
        file_name= req.file_name
        chunk = req.chunk

        existing_chunks = self.file_info[file_name]["chunks"][f"{host}:{port}"]
        existing_chunks = set(existing_chunks)
        existing_chunks.add(chunk)
        existing_chunks = list(existing_chunks)
        self.file_info[file_name]["chunks"][f"{host}:{port}"] = existing_chunks

        print(f"Registered : Chunk {chunk} of file {file_name} present with {host}:{port}")
        return ChunkRegisterResp(status=SUCCESS)

    def socket_target(self, conn):
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

    def run(self):
        print(f"Server running on {SERVER_HOST}:{SERVER_PORT}")
        while True:
            conn, addr = self.s.accept()
            threading.Thread(target=self.socket_target, args=(conn,)).start()


if __name__ == "__main__":
    server = Server(SERVER_HOST, SERVER_PORT)
    server.run()