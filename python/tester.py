#!/usr/bin/env python3

from typing import Callable
import os
import time
import zlib
import hashlib
import asyncio
from pyndn import Face, Interest, Data, NetworkNack, Name
from pyndn.security import KeyChain
from ndngitsync.gitfetcher import GitProducer
from ndngitsync.storage import FileStorage


class Server:
    def __init__(self, root_path, repo):
        # type: (str, str) -> None
        self.root_path = root_path
        self.repo = repo
        self.face = Face()
        keychain = KeyChain()
        self.face.setCommandSigningInfo(keychain, keychain.getDefaultCertificateName())
        self.storage = FileStorage("temprepo/.git")
        self.producer = GitProducer(self.face,
                                    Name("/git").append(repo).append("objects"),
                                    self.storage)

    def run(self):
        while True:
            self.face.processEvents()
            time.sleep(0.01)


def main():
    server = Server(os.getcwd(), "temprepo")
    try:
        server.run()
    except KeyboardInterrupt:
        print("Stopped by Ctrl+C.")


if __name__ == "__main__":
    main()
