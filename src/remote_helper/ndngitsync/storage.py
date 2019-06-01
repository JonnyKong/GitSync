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

    def path_from_hash(self, hash_name: str) -> str:
        return os.path.join(self.path, "objects", hash_name[:2], hash_name[2:])

    def put(self, hash_name: str, data: bytes):
        with open(self.path_from_hash(hash_name), "wb") as f:
            f.write(data)

    def get(self, hash_name: str) -> bytes:
        with open(self.path_from_hash(hash_name), "rb") as f:
            raw_data = f.read()
        return raw_data

    def exists(self, hash_name: str) -> bool:
        return os.path.exists(self.path_from_hash(hash_name))

    def remove(self, hash_name: str) -> bool:
        try:
            os.remove(self.path_from_hash(hash_name))
            return True
        except OSError:
            return False

