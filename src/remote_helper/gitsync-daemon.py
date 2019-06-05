#!/usr/bin/env python3

import asyncio
import logging
import sys
from ndngitsync.server import Server
from pyndn import Face
from pyndn.security import KeyChain


def main():
    if len(sys.argv) < 2:
        print("Usage:", sys.argv[0], "command-prefix", file=sys.stderr)
        return -1
    else:
        command_prefix = sys.argv[1]

    logging.basicConfig(format='[%(asctime)s]%(levelname)s:%(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)

    event_loop = asyncio.get_event_loop()
    face = Face()
    keychain = KeyChain()
    face.setCommandSigningInfo(keychain, keychain.getDefaultCertificateName())
    server = Server(face, command_prefix)

    async def face_loop():
        nonlocal face, server
        while server.running:
            face.processEvents()
            await asyncio.sleep(0.01)

    try:
        event_loop.run_until_complete(face_loop())
    finally:
        event_loop.close()


if __name__ == "__main__":
    main()

