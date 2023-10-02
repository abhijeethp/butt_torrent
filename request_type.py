from enum import Enum


class RequestType(Enum):
    REGISTER = 1
    FILE_LIST = 2
    FILE_LOCATIONS = 3
    CHUNK_REGISTER = 4
