import asyncio
import random
import time
from typing import Optional
from src.core.state import GlobalState
from src.net.server import Server
from src.net.client import send_message
from src.proto.messages import SensorUpdate, request_vote, vote_response, heartbeat

ROLE_FOLLOWER = "follower"
ROLE_CANDIDATE = "candidate"
ROLE_LEADER = "leader"

def random_timeout(base: float = 2.0, jitter: float = 1.0) -> float:
    return base + random.random() * jitter

class Node:
    def __init__(self, node_id: str, host: str, port: int, peers: list[str]):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.peers = peers
        self.state = GlobalState(node_id)

        # Election state
        self.role = ROLE_FOLLOWER
        self.term = 0
        self.voted_for: Optional[str] = None
        self.last_heartbeat = time.time()
        self.election_timeout = random_timeout(2.0, 1.5)  # ~2–3.5s
        self.votes_received = set()

        # Concurrency primitives
        self._server: Optional[Server] = None
        self._stop = asyncio.Event()

    async def start(self):
        self._server = Server(self.host, self.port, self.handle_message)
        asyncio.create_task(self._server.start())

        asyncio.create_task(self.sensor_loop())
        asyncio.create_task(self.election_watchdog())

        print(f"Node {self.node_id} started on {self.host}:{self.port} (role={self.role}, term={self.term})")
        await self._stop.wait()


    async def sensor_loop(self):
        while True:
            # Simulate sensor reading
            value = random.uniform(20.0, 30.0)
            self.state.update_local(value)

            msg = SensorUpdate(
                node_id=self.node_id,
                value=value,
                timestamp=time.time()
            )

            # Broadcast to peers
            for peer in self.peers:
                host, port = peer.split(":")
                asyncio.create_task(send_message(host, int(port), msg.__dict__))

            print(f"[{self.node_id}] Sensor update: {value:.2f}")
            await asyncio.sleep(5)  # every 5 seconds

    async def handle_message(self, msg: dict):
        # Sensor update
        if "node_id" in msg and "value" in msg and "timestamp" in msg and "term" not in msg:
            self.state.merge({msg["node_id"]: msg})
            print(f"[{self.node_id}] Merged update from {msg['node_id']}: {msg['value']}")
            return

        # Heartbeat
        if "leader_id" in msg and "term" in msg and "value" not in msg:
            leader_id = msg["leader_id"]
            term = msg["term"]
            if term >= self.term:
                if self.role != ROLE_FOLLOWER:
                    print(f"[{self.node_id}] -> FOLLOWER due to heartbeat from {leader_id} term={term} (prev role={self.role})")
                self.role = ROLE_FOLLOWER
                self.term = term
                self.voted_for = None
                self.last_heartbeat = time.time()
                self.election_timeout = random_timeout(2.0, 1.5)
            else:
                # Ignore stale heartbeat
                print(f"[{self.node_id}] Ignoring stale heartbeat from {leader_id} term={term} < local term={self.term}")
            return

        # RequestVote
        if "candidate_id" in msg and "term" in msg and "granted" not in msg:
            candidate_id = msg["candidate_id"]
            term = msg["term"]

            grant = False
            if term > self.term:
                # Newer term: become follower and consider vote
                self.role = ROLE_FOLLOWER
                self.term = term
                self.voted_for = None

            # Grant if: candidate’s term >= ours and we haven’t voted this term
            if term >= self.term and (self.voted_for is None or self.voted_for == candidate_id):
                grant = True
                self.voted_for = candidate_id
                self.last_heartbeat = time.time()
                self.election_timeout = random_timeout(2.0, 1.5)

            # Send vote response
            response = vote_response(voter_id=self.node_id, term=self.term, granted=grant)
            for peer in self.peers:
                host, port = peer.split(":")
                if host == self.host and int(port) == self.port:
                    continue
                # send back directly to candidate if you prefer, but we broadcast for simplicity
                asyncio.create_task(send_message(host, int(port), response))

            print(f"[{self.node_id}] Vote {'granted' if grant else 'denied'} for {candidate_id} (term={term}, local term={self.term}, voted_for={self.voted_for})")
            return

        # VoteResponse
        if "voter_id" in msg and "granted" in msg and "term" in msg:
            # In Part 5B we’ll use this to count votes if we’re a candidate.
            # For now, just log.
            print(f"[{self.node_id}] Received vote response from {msg['voter_id']}: granted={msg['granted']} term={msg['term']}")
            return

        # Unknown message type
        print(f"[{self.node_id}] Unrecognized message: {msg}")


    async def leader_heartbeat_loop(self):
        while not self._stop.is_set() and self.role == ROLE_LEADER:
            hb = heartbeat(leader_id=self.node_id, term=self.term)
            for peer in self.peers:
                host, port = peer.split(":")
                asyncio.create_task(send_message(host, int(port), hb))
            print(f"[{self.node_id}] Heartbeat (term={self.term})")
            await asyncio.sleep(1.0)


    async def election_watchdog(self):
        while not self._stop.is_set():
            elapsed = time.time() - self.last_heartbeat
            if elapsed > self.election_timeout and self.role != ROLE_LEADER:
                # We’ll transition to candidate and start election in Part 4.
                # For now, just log and refresh timeout so you can see the timing behavior.
                print(f"[{self.node_id}] Election timeout elapsed ({elapsed:.2f}s). Role={self.role}, term={self.term}")
                self.election_timeout = random_timeout(2.0, 1.5)
                # Next step: self.start_election()
            await asyncio.sleep(0.2)

