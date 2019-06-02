import os
import sys
import pymongo
from pymongo import MongoClient

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
        file_path = self.path_from_hash(hash_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
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

class DBStorage(IStorage):
    def __init__(self, db: str, collection: str):
        """
        Init DB with unique index on hash
        """
        self._db = db
        self._collection = collection
        self._uri = 'mongodb://localhost:27017/'

        client = MongoClient(self._uri)
        c_db = client[self._db]
        c_collection = c_db[self._collection]
        c_collection.create_index('key', unique=True)
    
    def put(self, key: str, value: bytes):
        """
        Insert document into MongoDB, overwrite if already exists.
        """
        client = MongoClient(self._uri)
        c_db = client[self._db]
        c_collection = c_db[self._collection]
        document = {
            "key": key,
            "value": value
        }
        try:
            c_collection.insert_one(document).inserted_id
        except pymongo.errors.DuplicateKeyError:
            c_collection.update_one({"key": key}, {"$set": {"value": value}})
    
    def get(self, value: str) -> bytes:
        """
        Get document from MongoDB
        """
        client = MongoClient(self._uri)
        c_db = client[self._db]
        c_collection = c_db[self._collection]
        ret = c_collection.find_one({"value": value})
        if ret:
            return ret["value"]
        else:
            return None

    def exists(self, key: str) -> bool:
        """
        Return whether document exists
        """
        client = MongoClient(self._uri)
        c_db = client[self._db]
        c_collection = c_db[self._collection]
        if c_collection.find_one({"key": key}):
            return True
        else:
            return False
    
    def remove(self, key: str) -> bool:
        """
        Return whether removal is successful
        """
        client = MongoClient(self._uri)
        c_db = client[self._db]
        c_collection = c_db[self._collection]        
        return c_collection.delete_one({"key": key}).deleted_count > 0

    def keys(self):
        """
        Return a set of "primary" keys
        """
        client = MongoClient(self._uri)
        c_db = client[self._db]
        c_collection = c_db[self._collection]
        return (doc["key"] for doc in c_collection.find())

# For testing
if __name__ == "__main__":
    s = DBStorage("gitsync", "objects")
    hash_name = "cf23df2207d99a74fbe169e3eba035e633b65d94"
    data = b'\x01\x02\x03\x04\x05'
    s.put(hash_name, data)