from typing import Union
from pyndn import Face, Name, Data, Interest
from .storage import DBStorage
import shutil
import asyncio
import struct
import logging
import os
import subprocess
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

        def register_prefix(prefix: Union[str, Name]):
            self.face.registerPrefix(prefix, None, self.on_register_failed)
            self.face.setInterestFilter(Name(prefix).append("push"), self.on_push)
            self.face.setInterestFilter(Name(prefix).append("create-branch"), self.on_create_branch)
            self.face.setInterestFilter(Name(prefix).append("track-repo"), self.on_track_repo)
            self.face.setInterestFilter(Name(prefix).append("mount"), self.on_mount)
            self.face.setInterestFilter(Name(prefix).append("unmount"), self.on_unmount)
            self.face.setInterestFilter(Name(prefix).append("commit"), self.on_commit)

        register_prefix(self.cmd_prefix)
        register_prefix(LOCAL_CMD_PREFIX)

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
        data.metaInfo.freshnessPeriod = 1000
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
        data.metaInfo.freshnessPeriod = 1000
        face.putData(data)

    def on_mount(self, _prefix, interest: Interest, face, _filter_id, _filter):
        logging.info("OnMount: %s", interest.name.toUri())
        repo = interest.name[-2].toEscapedString()
        branch = interest.name[-1].toEscapedString()
        mount_path = os.path.join(os.path.expanduser(MOUNT_PATH), repo)
        os.makedirs(mount_path, exist_ok=True)
        repo_uri = "ndn::" + Name(GIT_PREFIX).append(repo).toUri()

        os.spawnlp(os.P_NOWAIT, 'git', 'git', 'clone', '--single-branch',
                   '--branch', branch, repo_uri, os.path.join(mount_path, branch))

        # Respond with Data
        data = Data(interest.name)
        data.content = struct.pack("i", PUSH_RESPONSE_SUCCESS)
        data.metaInfo.freshnessPeriod = 1000
        face.putData(data)

    def on_unmount(self, _prefix, interest: Interest, face, _filter_id, _filter):
        logging.info("OnUnmount: %s", interest.name.toUri())
        repo = interest.name[-2].toEscapedString()
        branch = interest.name[-1].toEscapedString()
        dest_path = os.path.join(os.path.expanduser(MOUNT_PATH), repo, branch)

        shutil.rmtree(dest_path, ignore_errors=True)

        # Respond with Data
        data = Data(interest.name)
        data.content = struct.pack("i", PUSH_RESPONSE_SUCCESS)
        data.metaInfo.freshnessPeriod = 1000
        face.putData(data)

    def on_commit(self, _prefix, interest: Interest, face, _filter_id, _filter):
        param = interest.applicationParameters.toBytes()
        if not isinstance(param, bytes):
            print("Malformed request")
            return
        param = param.split(b'\x00')
        if len(param) != 4:
            print("Malformed request")
            return
        repo, branch, dest_branch, commit_msg = map(bytes.decode, param)

        env = os.environ
        env['GIT_COMMITTER_NAME'] = 'GitSync'
        env['GIT_WORK_TREE'] = os.path.join(os.path.expanduser(MOUNT_PATH), repo, branch)
        env['GIT_DIR'] = os.path.join(env['GIT_WORK_TREE'], '.git')
        repo_uri = "ndn::" + Name(GIT_PREFIX).append(repo).toUri()

        # Commit (blocking)
        subprocess.call(['git', 'commit', '-a', '-m', commit_msg], env=env)
        # Push
        os.spawnlpe(os.P_NOWAIT, 'git', 'git', 'push', repo_uri, 'HEAD:refs/heads/' + dest_branch, env)

        # Respond with Data
        data = Data(interest.name)
        data.content = struct.pack("i", PUSH_RESPONSE_SUCCESS)
        data.metaInfo.freshnessPeriod = 1000
        face.putData(data)
