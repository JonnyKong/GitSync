import os


class IStorage:
    def put(self, hash_name: str, data: bytes):
        raise NotImplementedError

    def get(self, hash_name: str) -> bytes:
        raise NotImplementedError

    def exists(self, hash_name: str) -> bool:
        raise NotImplementedError

    def remove(self, hash_name: str) -> bool:
        raise NotImplementedError


class FileStorage(IStorage):
    def __init__(self, path_prefix: str):
        self.path = path_prefix

    @staticmethod
    def path_from_hash(hash_name: str):
        return os.path.join("objects", hash_name[:2], hash_name[2:])

    def put(self, hash_name: str, data: bytes):
        raise NotImplementedError

    def get(self, hash_name: str) -> bytes:
        raise NotImplementedError

    def exists(self, hash_name: str) -> bool:
        raise NotImplementedError

    def remove(self, hash_name: str) -> bool:
        raise NotImplementedError
