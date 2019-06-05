from pyndn import Face, Name, Data, Interest
from .sync import Sync
from .gitfetcher import GitFetcher, GitProducer, fetch_data_packet
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
            face.registerPrefix(Name(self.repo_prefix).append("branch-info"),
                                self.on_branchinfo_interest,
                                self.on_register_failed)
            self.sync.run()

        def on_sync_update(self, branch: str, timestamp: int):
            event_loop = asyncio.get_event_loop()
            event_loop.create_task(self.sync_update(branch, timestamp))

        async def sync_update(self, branch: str, timestamp: int):
            commit = ""
            data = Data()

            def update_db():
                nonlocal commit
                # Fix the database
                if timestamp <= self.branches[branch].timestamp:
                    return
                self.branches[branch].timestamp = timestamp
                self.branches[branch].head = commit
                self.branches[branch].head_data = data.wireEncode().toBytes()
                self.repo_db.put(branch, pickle.dumps(self.branches[branch]))
                self.branches[branch].head_data = b""

            if branch in self.branches:
                # Update existing branch
                branch_info = self.branches[branch]
                if branch_info.timestamp < timestamp:
                    interest = Interest(Name(self.repo_prefix).append("refs").append(branch).appendTimestamp(timestamp))
                    print("ON SYNC UPDATE", interest.name.toUri())
                    data = await fetch_data_packet(self.face, interest)
                    if isinstance(data, Data):
                        commit = data.content.toBytes().decode("utf-8")
                    else:
                        print("error: Couldn't fetch refs")
                        return
                    
                    fetcher = self.fetch(commit)
                    await asyncio.wait_for(fetcher.wait_until_finish(), None)
                    update_db()
                    print("Update branch", branch, timestamp)
            else:
                # Fetch new branch
                interest = Interest(Name(self.repo_prefix).append("branch-info").append(branch))
                print("ON NEW BRANCH", interest.name.toUri())
                data = await fetch_data_packet(self.face, interest)
                if isinstance(data, Data):
                    branchinfo = pickle.loads(data.content.toBytes())
                else:
                    print("error: Couldn't fetch branch-info")
                    return
                self.branches[branch] = branchinfo
                await self.sync_update(branch, timestamp)

        def on_branchinfo_interest(self, _prefix, interest: Interest, face, _filter_id, _filter):
            name = interest.name
            print("ON BRANCH INFO INTEREST", name.toUri())
            branch = name[-1].toEscapedString()
            if branch not in self.branches:
                return
            data = Data(interest.name)
            data.content = pickle.dumps(self.branches[branch])
            face.putData(data)

        def on_refs_interest(self, _prefix, interest: Interest, face, _filter_id, _filter):
            name = interest.name
            print("ON REFS INTEREST", name.toUri())
            if name[-1].isTimestamp:
                timestamp = name[-1].toTimestamp()
                name = name[:-1]
            else:
                timestamp = None
            branch = name[-1].toEscapedString()
            if branch not in self.branches:
                return
            if timestamp is not None and timestamp != self.branches[branch].timestamp:
                if timestamp > self.branches[branch].timestamp:
                    self.on_sync_update(branch, timestamp)
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
            fetcher = GitFetcher(self.face, Name(self.repo_prefix).append("objects"), self.objects_db)
            fetcher.fetch(commit, "commit")
            return fetcher

        def create_branch(self, branch, custodian):
            if branch in self.branches:
                return False
            branch_info = BranchInfo(branch)
            branch_info.head = "?"
            branch_info.timestamp = 0
            branch_info.custodian = custodian
            self.branches[branch] = branch_info
            self.repo_db.put(branch, pickle.dumps(self.branches[branch]))
            asyncio.create_task(self.sync.publish_data(branch, 0))
            return True

        async def push(self, branch, commit, timeout, face, name):
            # TODO Check if new head is legal
            fetcher = self.fetch(commit)
            result = False

            async def checkout():
                nonlocal fetcher, result
                await fetcher.wait_until_finish()
                if not fetcher.success:
                    return

                # TODO W-A-W conflict
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
                self.repo_db.put(branch, pickle.dumps(self.branches[branch]))
                self.branches[branch].head_data = b""
                result = True

            event_loop = asyncio.get_event_loop()
            response = None

            if branch not in self.branches:
                response = PUSH_RESPONSE_FAILURE

            if response is None:
                try:
                    await asyncio.wait_for(fetcher.wait_until_finish(), timeout)
                except asyncio.TimeoutError:
                    event_loop.create_task(checkout())
                    response = PUSH_RESPONSE_PENDING

            if response is None:
                await asyncio.wait_for(checkout(), None)
                if result:
                    response = PUSH_RESPONSE_SUCCESS
                else:
                    response = PUSH_RESPONSE_FAILURE

            logging.info("Push Result: %s", response)
            data = Data(name)
            data.content = struct.pack("i", response)
            face.putData(data)

    def __init__(self, face: Face, cmd_prefix: str):
        self.running = True
        self.face = face
        self.repos = {}
        self.objects_db = DBStorage(DATABASE_NAME, OBJECTS_COLL_NAME)
        self.repos_db = DBStorage(DATABASE_NAME, REPOS_COLL_NAME)
        self.cmd_prefix = Name(cmd_prefix)

        self.face.registerPrefix(self.cmd_prefix, None, self.on_register_failed)
        self.face.setInterestFilter(Name(self.cmd_prefix).append("push"), self.on_push)
        self.face.setInterestFilter(Name(self.cmd_prefix).append("create-branch"), self.on_create_branch)
        self.face.setInterestFilter(Name(self.cmd_prefix).append("track-repo"), self.on_track_repo)
        self.load_repos()

    def load_repos(self):
        logging.info("Loading repos......")
        for repo in self.repos_db.keys():
            self.repos[repo] = self.Repo(self.objects_db, repo, self.face)
        logging.info("All repos loaded.")

    def on_register_failed(self, prefix):
        logging.error("Prefix registration failed: %s", prefix)

    def on_push(self, _prefix, interest: Interest, face, _filter_id, _filter):
        logging.info("OnPush: %s", interest.name.toUri())
        if len(interest.name) < 3:
            return
        repo = interest.name[-3].toEscapedString()
        branch = interest.name[-2].toEscapedString()
        if repo not in self.repos:
            logging.info("Repo %s doesn't exist", repo)
            response = PUSH_RESPONSE_FAILURE
            data = Data(interest.name)
            data.content = struct.pack("i", response)
            face.putData(data)
        else:
            commit = interest.applicationParameters.toBytes().decode("utf-8")
            timeout = interest.interestLifetimeMilliseconds / 1000.0 / 2.0

            logging.info("Arguments %s %s %s %d", repo, branch, commit, timeout)

            event_loop = asyncio.get_event_loop()
            event_loop.create_task(self.repos[repo].push(branch, commit, timeout, face, interest.name))

    def stop(self):
        self.running = False

    def on_create_branch(self, _prefix, interest: Interest, face, _filter_id, _filter):
        logging.info("OnCreateBranch: %s", interest.name.toUri())
        if len(interest.name) < 3:
            return
        repo = interest.name[-2].toEscapedString()
        branch = interest.name[-1].toEscapedString()
        if repo not in self.repos:
            response = PUSH_RESPONSE_FAILURE
        else:
            result = self.repos[repo].create_branch(branch, self.cmd_prefix.toUri())
            response = PUSH_RESPONSE_SUCCESS if result else PUSH_RESPONSE_FAILURE
        data = Data(interest.name)
        data.content = struct.pack("i", response)
        face.putData(data)

    def on_track_repo(self, _prefix, interest: Interest, face, _filter_id, _filter):
        logging.info("OnTrackRepo: %s", interest.name.toUri())
        if len(interest.name) < 2:
            return
        repo = interest.name[-1].toEscapedString()
        if repo in self.repos:
            response = PUSH_RESPONSE_FAILURE
        else:
            self.repos[repo] = self.Repo(self.objects_db, repo, self.face)
            self.repos_db.put(repo, b"")
            response = PUSH_RESPONSE_SUCCESS
        data = Data(interest.name)
        data.content = struct.pack("i", response)
        face.putData(data)
