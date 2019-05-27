#!/usr/bin/env python3

from typing import Callable
import os
import time
import zlib
import hashlib
import asyncio
from pyndn import Face, Interest, Data, NetworkNack, Name
from pyndn.security import KeyChain
from ndngitsync.gitfetcher import path_from_hash


class Server:
    def __init__(self, root_path, repo):
        # type: (str, str) -> None
        self.root_path = root_path
        self.repo = repo
        self.face = Face()
        keychain = KeyChain()
        self.face.setCommandSigningInfo(keychain, keychain.getDefaultCertificateName())
        self.face.registerPrefix(Name("/git").append(repo).append("objects"),
                                 self.on_objects_interest,
                                 None)

    def run(self):
        while True:
            self.face.processEvents()
            time.sleep(0.01)

    def on_objects_interest(self, _prefix, interest: Interest, face: Face, _filter_id, _filter):
        hash_name = interest.name[3].toEscapedString()
        #if interest.name[-1].isSequenceNumber():
        #    interest.name[-1].toSequenceNumber()
        print(interest.name.toUri())
        file_path = os.path.join("temprepo/.git", path_from_hash(hash_name))
        if os.path.exists(file_path):
            data = Data(interest.name)
            with open(file_path, "rb") as f:
                data.content = f.read()
            face.putData(data)
        else:
            print("Not exist!")


def main():
    server = Server(os.getcwd(), "temprepo")
    try:
        server.run()
    except KeyboardInterrupt:
        print("Stopped by Ctrl+C.")


if __name__ == "__main__":
    main()
