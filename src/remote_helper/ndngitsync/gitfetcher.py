from typing import Optional, Union
import os
import zlib
import hashlib
import asyncio
from pyndn import Face, Interest, Data, NetworkNack, Name


FETCHER_MAX_ATTEMPT_NUMBER = 3
FETCHER_RETRY_INTERVAL = 1000.0
FETCHER_FINAL_BLOCK_ID = 2 ** 31 - 1
FETCHER_MAX_INTEREST_IN_FLIGHT = 20
HASH_LENGTH = 20


async def fetch_data_packet(face: Face, interest: Interest) -> Union[Data, NetworkNack, None]:
    done = asyncio.Event()
    result = None

    def on_data(_interest, data: Data):
        nonlocal done, result
        result = data
        done.set()

    def on_timeout(_interest):
        nonlocal done
        done.set()

    def on_network_nack(_interest, network_nack: NetworkNack):
        nonlocal done, result
        result = network_nack
        done.set()

    face.expressInterest(interest, on_data, on_timeout, on_network_nack)
    await done.wait()
    return result


async def fetch_object(face: Face, prefix: Name, semaphore: asyncio.Semaphore) -> Optional[bytes]:
    async def retry_or_fail() -> Optional[Data]:
        nonlocal interest
        result = None
        # retry for up to FETCHER_MAX_ATTEMPT_NUMBER times
        for _ in range(FETCHER_MAX_ATTEMPT_NUMBER):
            # express interest
            async with semaphore:
                response = await fetch_data_packet(face, interest)
            if isinstance(response, Data):
                # if succeeded, jump out
                result = response
                break
            else:
                # if failed, wait for next time
                await asyncio.sleep(FETCHER_RETRY_INTERVAL / 1000.0)
        return result

    data = bytes("", "utf-8")
    final_id = FETCHER_FINAL_BLOCK_ID
    cur_id = 0
    while cur_id <= final_id:
        if cur_id == 0:
            interest = Interest(Name(prefix))
        else:
            interest = Interest(Name(prefix).appendSegment(cur_id))
        data_packet = await retry_or_fail()
        if data_packet is None:
            return None
        data += data_packet.content.toBytes()
        final_id_component = data_packet.metaInfo.getFinalBlockId()
        if final_id_component.isSegment():
            final_id = final_id_component.toSegment()
        else:
            break
        cur_id += 1
    return data


def path_from_hash(hash_name):
    return os.path.join("objects", hash_name[:2], hash_name[2:])


class GitFetcher:
    def __init__(self, face: Face, prefix: Union[Name, str], path_prefix: str):
        self.face = face
        self.semaphore = asyncio.Semaphore(FETCHER_MAX_INTEREST_IN_FLIGHT)
        self.requested = set()
        self.finished_cnt = 0
        self.finish_event = asyncio.Event()
        self.prefix = prefix
        self.path = path_prefix
        self.success = True
        self.event_loop = asyncio.get_event_loop()

    def fetch(self, hash_name: str, expect_type: str = ""):
        # Ignore in-flight or fetched file
        hash_value = bytes.fromhex(hash_name)
        if hash_value in self.requested:
            return
        self.requested.add(hash_value)
        self.event_loop.create_task(self._do_fetch(hash_name, hash_value, expect_type))

    async def _do_fetch(self, hash_name: str, hash_value: bytes, expect_type: str = ""):
        def fail():
            self.success = False
            self.finish_event.set()

        # Get the data
        file_path = os.path.join(self.path, path_from_hash(hash_name))
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                raw_data = f.read()
            from_disk = True
        else:
            raw_data = await fetch_object(self.face, Name(self.prefix).append(hash_name), self.semaphore)
            from_disk = False
        if not isinstance(raw_data, bytes):
            fail()
            return
        # Verify data
        data = zlib.decompress(raw_data)
        header_size = data.find(b'\x00')
        header = data[:header_size]
        content = data[header_size + 1:]
        content_type, content_len = header.decode("utf-8").split(' ')
        content_len = int(content_len)
        if content_len != len(content):
            fail()
            return
        if expect_type != "" and content_type != expect_type:
            fail()
            return
        sha1 = hashlib.sha1()
        sha1.update(data)
        if sha1.digest() != hash_value:
            fail()
            return
        # Write back if OK
        if not from_disk:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(raw_data)
        # Traverse data
        if content_type == "commit":
            if not from_disk:
                self.traverse_commit(content)
        elif content_type == "tree":
            self.traverse_tree(content)
        else:
            if content_type != "blob":
                print("Error: Unknown file type", content_type)
        # Finish event
        self.finished_cnt += 1
        if self.finished():
            self.finish_event.set()

    def traverse_commit(self, content: bytes):
        # event_loop = asyncio.get_event_loop()
        lines = content.decode("utf-8").split("\n")
        for ln in lines:
            if not ln.startswith("tree") and not ln.startswith("parent"):
                break
            expect_type, hash_name = ln.split(" ")
            if expect_type == "parent":
                expect_type = "commit"
            self.fetch(hash_name, expect_type)

    def traverse_tree(self, content: bytes):
        # event_loop = asyncio.get_event_loop()
        size = len(content)
        pos = 0
        while pos < size:
            name_start = content.find(b'\x00', pos)
            hash_name = content[name_start + 1:name_start + HASH_LENGTH + 1]
            if content[pos] == ord('1'):
                expect_type = "blob"
            else:
                expect_type = "tree"
            self.fetch(hash_name.hex(), expect_type)
            pos = name_start + HASH_LENGTH + 1

    def finished(self) -> bool:
        return len(self.requested) == self.finished_cnt or not self.success

    async def wait_until_finish(self):
        await self.finish_event.wait()
        return self.success
