from typing import Optional, Union
import asyncio
from datetime import datetime
from pyndn import Face, Interest, Data, NetworkNack, Name
from random import uniform


SYNC_INTERVAL_MIN = 1.0
SYNC_INTERVAL_MAX = 2.0


class Sync:
    def __init__(self, prefix: Union[Name, str], face: Face, on_update):
        self.state = {}
        self.running = False
        self.prefix = prefix
        self.face = face
        self.on_update = on_update
        self.lock = asyncio.Lock()
        self.sync_event = asyncio.Event()

    @staticmethod
    def encode(sync_vec: dict) -> str:
        return "~".join(k + ":" + str(v) for k, v in sync_vec.items())

    @staticmethod
    def decode(raw_vec: str) -> dict:
        ret = {}
        for state in raw_vec.split("~"):
            branch, timestamp = state.split(":")
            ret[branch] = int(timestamp)
        return ret

    @staticmethod
    def timestamp():
        return int(datetime.utcnow().timestamp() * 1000000)

    def on_sync_interest(self, _prefix, interest: Interest, face, _filter_id, _filter):
        async def update_state():
            nonlocal new_state
            async with self.lock:
                for branch, timestamp in new_state.items():
                    if branch not in self.state or self.state[branch] < timestamp:
                        self.state[branch] = timestamp
                        self.on_update(branch, timestamp)

        raw_vec = interest.parameters.toBytes().decode("utf-8")
        new_state = self.decode(raw_vec)
        event_loop = asyncio.get_event_loop()
        event_loop.create_task(update_state())

    def on_sync_data(self, *args, **kwargs):
        pass

    async def retx_sync_interest(self):
        while self.running:
            interest = Interest(Name(self.prefix))
            interest.parameters = self.encode(self.state)
            interest.appendParametersDigestToName()

            # await fetch_data_packet(self.face, interest)
            self.face.expressInterest(interest, self.on_sync_data)

            timeout = uniform(SYNC_INTERVAL_MIN, SYNC_INTERVAL_MAX)
            try:
                await asyncio.wait_for(self.sync_event, timeout)
            except asyncio.TimeoutError:
                pass
            self.sync_event.clear()


    def run(self):
        self.running = True
        event_loop = asyncio.get_event_loop()
        event_loop.create_task(self.retx_sync_interest())

    def stop(self):
        self.running = False

    async def publish_data(self, branch: str, timestamp: Optional[int]):
        if timestamp is None:
            timestamp = self.timestamp()
        async with self.lock:
            self.state[branch] = timestamp
        self.sync_event.set()
