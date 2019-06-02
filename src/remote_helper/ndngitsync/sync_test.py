#!/usr/bin/env python3

import asyncio
from sync import Sync
from pyndn import Face, Interest, Data, NetworkNack, Name
from pyndn.security import KeyChain


def on_update(branch: str, timestamp: int):
    print("%s: %d" % (branch, timestamp))


async def run():
    async def face_loop():
        nonlocal face, running
        while running:
            face.processEvents()
            await asyncio.sleep(0.01)
    event_loop = asyncio.get_event_loop()
    event_loop.create_task(face_loop())

    running = True
    face = Face()
    keychain = KeyChain()
    face.setCommandSigningInfo(keychain, keychain.getDefaultCertificateName())

    sync = Sync(prefix=Name("/git"), face=face, on_update=on_update)
    sync.run()

    while True:
        await sync.publish_data(branch="test_branch", timestamp=None)
        await asyncio.sleep(5)

if __name__ == "__main__":
    event_loop = asyncio.get_event_loop()
    try:
        event_loop.run_until_complete(run())
    finally:
        event_loop.close()
