from dataclasses import dataclass, field
from request_type import RequestType


@dataclass
class Req:
    type: int


@dataclass
class Resp:
    status: int


@dataclass
class RegisterReq(Req):
    type: int = field(default=RequestType.REGISTER.value, init=False)
    endpoint: tuple
    files: list


@dataclass
class RegisterResp(Resp):
    pass


@dataclass
class FileListReq(Req):
    type: int = field(default=RequestType.FILE_LIST.value, init=False)


@dataclass
class FileListResp(Resp):
    files: list


@dataclass
class FileLocationsReq(Req):
    type: int = field(default=RequestType.FILE_LOCATIONS.value, init=False)
    file_name: str


@dataclass
class FileLocationsResp(Resp):
    endpoints: dict
    hashes: list


@dataclass
class ChunkRegisterReq(Req):
    type: int = field(default=RequestType.CHUNK_REGISTER.value, init=False)
    endpoint: tuple
    file_name: str
    chunk: int


@dataclass
class ChunkRegisterResp(Resp):
    pass


@dataclass
class ChunkDownloadReq(Req):
    type: int = field(default=RequestType.CHUNK_DOWNLOAD.value, init=False)
    file_name: str
    chunk: int
