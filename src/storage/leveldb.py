import plyvel
import os
from . import IStorage


class DBStorage(IStorage):
    def __init__(self, db: str, collection: str):
        """
        Init DB with unique index on hash
        """
        self._db = db
        self._collection = collection
        self._uri = os.path.join(os.path.expanduser('~/.' + db), collection)

        os.makedirs(self._uri, exist_ok=True)
        self.client = plyvel.DB(self._uri, create_if_missing=True)

    def put(self, key: str, value: bytes):
        """
        Insert document into MongoDB, overwrite if already exists.
        """
        self.client.put(key.encode(), value)

    def get(self, key: str) -> bytes:
        """
        Get document from MongoDB
        """
        return self.client.get(key.encode())

    def exists(self, key: str) -> bool:
        """
        Return whether document exists
        """
        return self.client.get(key.encode()) is None

    def remove(self, key: str) -> bool:
        """
        Return whether removal is successful
        """
        self.client.delete(key.encode())
        return True

    def keys(self):
        """
        Return a set of "primary" keys
        """
        return (item[0] for item in self.client)
