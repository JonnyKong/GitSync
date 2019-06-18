from pyndn import Face, Name, Data, Interest
from .storage import DBStorage, IStorage
import asyncio
import struct
import logging
from .config import *
from .repo import Repo


class Server:
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

        self.face.registerPrefix(LOCAL_CMD_PREFIX, None, self.on_register_failed)
        self.face.setInterestFilter(Name(LOCAL_CMD_PREFIX).append("push"), self.on_push)
        self.face.setInterestFilter(Name(LOCAL_CMD_PREFIX).append("create-branch"), self.on_create_branch)
        self.face.setInterestFilter(Name(LOCAL_CMD_PREFIX).append("track-repo"), self.on_track_repo)

        self.load_repos()

    def load_repos(self):
        logging.info("Loading repos......")
        for repo in self.repos_db.keys():
            self.repos[repo] = Repo(self.objects_db, repo, self.face)
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
            self.repos[repo] = Repo(self.objects_db, repo, self.face)
            self.repos_db.put(repo, b"")
            response = PUSH_RESPONSE_SUCCESS
        data = Data(interest.name)
        data.content = struct.pack("i", response)
        face.putData(data)
