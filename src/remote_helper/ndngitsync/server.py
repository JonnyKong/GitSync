from pyndn import Face, Name, Data, Interest
from .sync import Sync
from .gitfetcher import GitFetcher, GitProducer
from .storage import DBStorage, IStorage
import pickle
import sys
import asyncio
import struct
import logging


DATABASE_NAME = "gitsync"
GIT_PREFIX = "git"
OBJECTS_COLL_NAME = "~objects"
REPOS_COLL_NAME = "~repos"

PUSH_RESPONSE_PENDING = 0
PUSH_RESPONSE_SUCCESS = 1
PUSH_RESPONSE_FAILURE = 2


class BranchInfo:
    def __init__(self, branch_name):
        self.name = branch_name
        self.custodian = ""
        self.key = ""
        self.timestamp = 0
        self.head = ""
        self.head_data = b""


class Server:
    class Repo:
        def __init__(self, objects_db: IStorage, repo_name: str, face: Face):
            self.repo_db = DBStorage(DATABASE_NAME, repo_name)
            self.objects_db = objects_db
            self.repo_prefix = Name(GIT_PREFIX).append(repo_name)
            self.sync = Sync(face=face,
                             prefix=Name(self.repo_prefix).append("sync"),
                             on_update=self.on_sync_update)
            self.producer = GitProducer(face=face,
                                        prefix=Name(self.repo_prefix).append("objects"),
                                        storage=objects_db)
            self.face = face
            self.branches = {}
            self.load_refs()

            face.registerPrefix(Name(self.repo_prefix).append("refs"),
                                self.on_refs_interest,
                                self.on_register_failed)
            face.registerPrefix(Name(self.repo_prefix).append("ref-list"),
                                self.on_reflist_interest,
                                self.on_register_failed)

        def on_sync_update(self, branch: str, timestamp: int):
            if branch in self.branches:
                branch_info = self.branches[branch]
                if branch_info.timestamp < timestamp:
                    # TODO: Update branch
                    print("TODO: Update branch", branch, timestamp)
                    branch_info.timestamp = timestamp
            else:
                return  # TODO: fetch branch metainfo

        def on_refs_interest(self, _prefix, interest: Interest, face, _filter_id, _filter):
            name = interest.name
            if name[-1].isTimestamp:
                timestamp = name[-1].toTimestamp()
                name = name[:-1]
            else:
                timestamp = None
            branch = name[-1]
            if branch not in self.branches:
                return
            if timestamp is not None and timestamp != self.branches[branch].timestamp:
                return

            data = Data()
            raw_data = pickle.loads(self.repo_db.get(branch))
            data.wireDecode(raw_data.head_data)
            face.putData(data)

        def on_reflist_interest(self, _prefix, interest: Interest, face, _filter_id, _filter):
            result = '\n'.join("{} refs/heads/{}".format(info.head, name)
                               for name, info in self.branches.items())
            result = result + '\n'

            print("On reflist -> return:", result)

            data = Data(interest.name)
            data.content = result.encode("utf-8")
            face.putData(data)

        def on_register_failed(self, prefix):
            logging.error("Prefix registration failed: %s", prefix)

        def load_refs(self):
            logging.info("Loading %s {", self.repo_prefix[-1])
            for branch in self.repo_db.keys():
                raw_data = self.repo_db.get(branch)
                self.branches[branch] = pickle.loads(raw_data)
                # Drop the data packet from memory
                self.branches[branch].head_data = b""
                logging.info("  branch: %s head: %s", self.branches[branch].name, self.branches[branch].head)
            # Set Sync's initial state
            self.sync.state = {name: info.timestamp for name, info in self.branches.items()}
            logging.info("}")

        def fetch(self, commit):
            fetcher = GitFetcher(self.face, self.repo_prefix.append("objects"), self.objects_db)
            fetcher.fetch(commit, "commit")
            return fetcher

        def push(self, branch, commit, timeout):
            # TODO Check if new head is legal
            fetcher = self.fetch(commit)
            result = False

            async def checkout():
                nonlocal fetcher, result
                await fetcher.wait_until_finish()
                timestamp = await self.sync.publish_data(branch)
                self.branches[branch].timestamp = timestamp
                self.branches[branch].head = commit

                # Fix the database
                head_data_name = Name(self.repo_prefix).append("refs")
                head_data_name = head_data_name.append(branch).appendTimestamp(timestamp)
                head_data = Data(head_data_name)
                head_data.content = commit.encode("utf-8")
                # TODO Sign data
                self.branches[branch].head_data = head_data.wireEncode().toBytes()
                self.repo_db.put(branch, self.branches[branch])
                self.branches[branch].head_data = b""
                result = True

            event_loop = asyncio.get_event_loop()
            try:
                asyncio.wait_for(fetcher.wait_until_finish(), timeout)
            except asyncio.TimeoutError:
                event_loop.create_task(checkout())
                return PUSH_RESPONSE_PENDING

            asyncio.wait_for(checkout(), None)
            if result:
                return PUSH_RESPONSE_SUCCESS
            else:
                return PUSH_RESPONSE_FAILURE

    def __init__(self, face: Face, cmd_prefix: str):
        self.running = True
        self.face = face
        self.repos = {}
        self.objects_db = DBStorage(DATABASE_NAME, OBJECTS_COLL_NAME)
        self.repos_db = DBStorage(DATABASE_NAME, REPOS_COLL_NAME)
        self.cmd_prefix = Name(cmd_prefix)

        self.face.registerPrefix(self.cmd_prefix, None, self.on_register_failed)
        self.face.setInterestFilter(Name(self.cmd_prefix).append("push"), self.on_push)
        self.load_repos()

    def load_repos(self):
        logging.info("Loading repos......")
        for repo in self.repos_db.keys():
            self.repos[repo] = self.Repo(self.objects_db, repo, self.face)
        logging.info("All repos loaded.")

    def on_register_failed(self, prefix):
        logging.error("Prefix registration failed: %s", prefix)

    def on_push(self, _prefix, interest: Interest, face, _filter_id, _filter):
        # TODO Length check for all
        repo = interest.name[-3]
        branch = interest.name[-2]
        if repo not in self.repos:
            return
        commit = interest.applicationParameters.toBytes().decode("utf-8")
        timeout = interest.interestLifetimeMilliseconds / 1000.0 / 2.0
        result = self.repos[repo].push(branch, commit, timeout)

        data = Data(interest.name)
        data.content = struct.pack("i", result)
        face.putData(data)

    def stop(self):
        self.running = False
