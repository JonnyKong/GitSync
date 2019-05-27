#!/usr/bin/env python3

import sys
import os
import asyncio
from ndngitsync.gitfetcher import GitFetcher
from pyndn import Face, Name


async def run(local_repo_path: str, repo_prefix: str):
    async def face_loop():
        nonlocal face, running
        while running:
            face.processEvents()
            await asyncio.sleep(0.01)

    running = True
    face = Face()
    event_loop = asyncio.get_event_loop()
    face_task = event_loop.create_task(face_loop())

    empty_cnt = 0
    while empty_cnt < 10 and running:
        cmd = sys.stdin.readline().rstrip("\n\r")
        print("<<", cmd, file=sys.stderr)
        if cmd == "capabilities":
            print("push")
            print("fetch")
            print("option")
            print("")
            sys.stdout.flush()
        elif cmd.startswith("option"):
            print("unsupported")
            sys.stdout.flush()
        elif cmd == "list" or cmd == "list for-push":
            # TODO
            print("6bc2f219de91083adea75a97fd423acaf9b854ca refs/heads/master")
            print("")
            sys.stdout.flush()
        elif cmd.startswith("fetch"):
            fetcher = GitFetcher(face, Name(repo_prefix).append("objects"), os.path.join(local_repo_path, ".git"))
            while True:
                # Fetch files
                hash_name, ref_name = cmd.split()[1:]
                fetcher.fetch(hash_name, "commit")
                await fetcher.wait_until_finish()
                # Read commands for next fetch
                cmd = sys.stdin.readline().rstrip("\n\r")
                if not cmd.startswith("fetch"):
                    break
            print("")
            sys.stdout.flush()
        elif cmd.startswith("push"):
            # TODO
            while cmd.startswith("push"):
                cmd = sys.stdin.readline().rstrip("\n\r")
                print("<<push<<", cmd, file=sys.stderr)
            print("ok refs/heads/master")
            print("")
            sys.stdout.flush()
            # pretend to push data
        elif cmd == "":
            empty_cnt += 1
        else:
            pass

    running = False
    await face_task


def main():
    if len(sys.argv) < 3:
        print("Usage:", sys.argv[0], "remote-name url", file=sys.stderr)
        # exit(-1)
        local_repo_path = os.path.join(os.getcwd(), "testrepo")
        repo_prefix = "/git/temprepo"
    else:
        local_repo_path = os.getcwd()
        repo_prefix = sys.argv[2]
    event_loop = asyncio.get_event_loop()
    try:
        event_loop.run_until_complete(run(local_repo_path, repo_prefix))
    finally:
        event_loop.close()


if __name__ == "__main__":
    main()
