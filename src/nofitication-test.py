#!/usr/bin/env python3

import asyncio
from pyndn import Face, Name, Interest, Data
from ndngitsync.gitfetcher import fetch_data_packet


async def run():
    async def face_loop():
        nonlocal face, running
        while running:
            face.processEvents()
            await asyncio.sleep(0.01)

    running = True
    face = Face()
    event_loop = asyncio.get_event_loop()
    face_task = event_loop.create_task(face_loop())

    interest = Interest(Name("/localhost/gitsync/notif/temprepo/master"))
    interest.mustBeFresh = True
    interest.canBePrefix = True
    interest.interestLifetimeMilliseconds = 60000
    data = await fetch_data_packet(face, interest)
    if isinstance(data, Data):
        print("Notif", data.content.toBytes().decode())
    else:
        print("Failed")

    running = False
    await face_task


def main():
    event_loop = asyncio.get_event_loop()
    try:
        event_loop.run_until_complete(run())
    finally:
        event_loop.close()


if __name__ == "__main__":
    main()
