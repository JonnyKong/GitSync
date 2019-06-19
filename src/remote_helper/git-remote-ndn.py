#!/usr/bin/env python3

import sys
import os
import asyncio
import struct
import pickle
from ndngitsync.gitfetcher import GitFetcher, GitProducer, fetch_data_packet
from ndngitsync.storage import FileStorage
from pyndn import Face, Name, Interest, Data
from pyndn.security import KeyChain
from typing import Tuple
from ndngitsync.config import LOCAL_CMD_PREFIX


def parse_push(cmd: str, local_repo_path: str) -> Tuple[str, str, bool]:
    src, dst = cmd.split(" ")[1].split(":")
    forced = src[0] == "+"
    src = src.lstrip("+")
    filename = os.path.join(local_repo_path, ".git", src)
    with open(filename, "r") as f:
        commit = f.readline().strip()
    branch = dst.split("/")[-1]
    print("PARSE:", branch, commit, forced, file=sys.stderr)
    return branch, commit, forced


async def run(local_repo_path: str, repo_prefix: str):
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
    storage = FileStorage(os.path.join(local_repo_path, ".git"))
    producer = GitProducer(face, Name(repo_prefix).append("objects"), storage)
    refs = []

    empty_cnt = 0
    while empty_cnt < 2 and running:
        cmd = sys.stdin.readline().rstrip("\n\r")
        # print("<<", cmd, file=sys.stderr)
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
            interest = Interest(Name(repo_prefix).append("ref-list"))
            data = await fetch_data_packet(face, interest)
            if isinstance(data, Data):
                reflist = data.content.toBytes().decode("utf-8")
                print(reflist)

                if reflist.strip() == "":
                    refs = {}
                else:
                    refs = [item.split(" ")[1] for item in reflist.strip().split("\n")]
                    refs = {name.split("/")[-1] for name in refs}
            else:
                print("error: Couldn't connect to", repo_prefix, file=sys.stderr)
                running = False
                print("")
            sys.stdout.flush()
        elif cmd.startswith("fetch"):
            fetcher = GitFetcher(face, Name(repo_prefix).append("objects"), storage)
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
            while True:
                # Push commands
                # TODO: DELETE ALL HARDCODED THINGS
                # TODO: MAKE DATA AND INTEREST REAL
                branch, commit, _ = parse_push(cmd, local_repo_path)
                repo_name = repo_prefix.split("/")[-1]

                # Create Branch if not exist
                if branch not in refs:
                    print("Non-existing branch. Try to create...", file=sys.stderr)
                    interest = Interest(Name(LOCAL_CMD_PREFIX).append("create-branch").append(repo_name).append(branch))
                    data = await fetch_data_packet(face, interest)
                    if isinstance(data, Data):
                        result = struct.unpack("i", data.content.toBytes())[0]
                        if result == 1:
                            print("Creation succeeded", file=sys.stderr)
                        elif result == 2:
                            print("Creation is FAILED", file=sys.stderr)
                            print("error refs/heads/{} FAILED".format(branch))
                            break
                        else:
                            print("Creation is PENDING", file=sys.stderr)
                            print("error refs/heads/{} PENDING".format(branch))
                            break
                    else:
                        print("error: Couldn't connect to", interest.name.toUri(), file=sys.stderr)
                        break

                # BranchInfo Interest
                interest = Interest(Name(repo_prefix).append("branch-info").append(branch))
                data = await fetch_data_packet(face, interest)
                branchinfo = None
                if isinstance(data, Data):
                    branchinfo = pickle.loads(data.content.toBytes())
                if branchinfo is None or 'custodian' not in branchinfo.__dict__:
                    print("ERROR Interest got no response: ", interest.name, file=sys.stderr)
                    print("error refs/heads/{} DISCONNECTED".format(branch))
                    break

                # Push Interest
                interest = Interest(Name(branchinfo.custodian).append("push").append(repo_name).append(branch))
                interest.applicationParameters = commit.encode("utf-8")
                interest.appendParametersDigestToName()
                interest.interestLifetimeMilliseconds = 20000
                interest.mustBeFresh = True
                data = await fetch_data_packet(face, interest)
                if isinstance(data, Data):
                    result = struct.unpack("i", data.content.toBytes())[0]
                    if result == 1:
                        print("OK push succeeded", interest.name, file=sys.stderr)
                        print("ok refs/heads/{}".format(branch))
                    elif result == 2:
                        print("ERROR push failed", interest.name, file=sys.stderr)
                        print("error refs/heads/{} FAILED".format(branch))
                    else:
                        print("PROCESSING push is not finished yet", interest.name, file=sys.stderr)
                        print("error refs/heads/{} PENDING".format(branch))
                else:
                    print("ERROR Interest got no response: ", interest.name, file=sys.stderr)
                    print("error refs/heads/{} DISCONNECTED".format(branch))
                    break

                # Read commands for next fetch
                cmd = sys.stdin.readline().rstrip("\n\r")
                if not cmd.startswith("push"):
                    break

            print("")
            sys.stdout.flush()
        elif cmd == "":
            empty_cnt += 1
        else:
            pass

    producer.cancel()
    running = False
    await face_task


def main():
    if len(sys.argv) < 3:
        print("Usage:", sys.argv[0], "remote-name url", file=sys.stderr)
        return -1
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
