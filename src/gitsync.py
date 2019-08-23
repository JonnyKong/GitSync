#!/usr/bin/env python3

import sys
import asyncio
import struct
from ndngitsync.gitfetcher import fetch_data_packet
from pyndn import Face, Name, Interest, Data
from pyndn.security import KeyChain
from ndngitsync.config import LOCAL_CMD_PREFIX


async def run(cmd: str):
    async def face_loop():
        nonlocal face, running
        while running:
            face.processEvents()
            await asyncio.sleep(0.01)

    running = True
    face = Face()
    keychain = KeyChain()
    face.setCommandSigningInfo(keychain, keychain.getDefaultCertificateName())
    event_loop = asyncio.get_event_loop()
    face_task = event_loop.create_task(face_loop())

    if cmd == "track-repo":
        if len(sys.argv) < 3:
            print("Usage:", sys.argv[0], "track-repo <repo>", file=sys.stderr)
        else:
            repo = sys.argv[2]
            interest = Interest(Name(LOCAL_CMD_PREFIX).append("track-repo").append(repo))
            data = await fetch_data_packet(face, interest)
            if isinstance(data, Data):
                result = struct.unpack("i", data.content.toBytes())[0]
                if result == 1:
                    print("OK")
                elif result == 2:
                    print("FAILED")
                else:
                    print("PENDING")
            else:
                print("error: Couldn't connect to", interest.name.toUri(), file=sys.stderr)
    elif cmd == "create-branch":
        if len(sys.argv) < 4:
            print("Usage:", sys.argv[0], "create-branch <repo> <branch>", file=sys.stderr)
        else:
            repo = sys.argv[2]
            branch = sys.argv[3]
            interest = Interest(Name(LOCAL_CMD_PREFIX).append("create-branch").append(repo).append(branch))
            data = await fetch_data_packet(face, interest)
            if isinstance(data, Data):
                result = struct.unpack("i", data.content.toBytes())[0]
                if result == 1:
                    print("OK")
                elif result == 2:
                    print("FAILED")
                else:
                    print("PENDING")
            else:
                print("error: Couldn't connect to", interest.name.toUri(), file=sys.stderr)
    elif cmd == "mount":
        if len(sys.argv) < 4:
            print("Usage:", sys.argv[0], "mount <repo> <branch>", file=sys.stderr)
        else:
            repo = sys.argv[2]
            branch = sys.argv[3]
            interest = Interest(Name(LOCAL_CMD_PREFIX).append("mount").append(repo).append(branch))
            data = await fetch_data_packet(face, interest)
            if isinstance(data, Data):
                print("Finished.")
            else:
                print("error: Couldn't connect to", interest.name.toUri(), file=sys.stderr)
    else:
        print("Unrecognized command:", cmd, file=sys.stderr)

    running = False
    await face_task


def main():
    if len(sys.argv) < 2:
        print("Usage:", sys.argv[0], "command [args]", file=sys.stderr)
        return -1
    else:
        cmd = sys.argv[1]
    event_loop = asyncio.get_event_loop()
    try:
        event_loop.run_until_complete(run(cmd))
    finally:
        event_loop.close()


if __name__ == "__main__":
    main()
