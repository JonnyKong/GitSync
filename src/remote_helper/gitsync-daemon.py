#!/usr/bin/env python3

import asyncio
from ndngitsync.server import Server
from pyndn import Face
from pyndn.security import KeyChain


def main():
    event_loop = asyncio.get_event_loop()
    face = Face()
    keychain = KeyChain()
    face.setCommandSigningInfo(keychain, keychain.getDefaultCertificateName())
    server = Server(face, "/localhost/gitdaemon")

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

