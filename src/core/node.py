import asyncio
import random
import time
from typing import Optional
from src.core.state import GlobalState
from src.net.server import Server
from src.net.client import send_message
from src.proto.messages import SensorUpdate, sensor_update, request_vote, vote_response, heartbeat

ROLE_FOLLOWER = "follower"
ROLE_CANDIDATE = "candidate"
ROLE_LEADER = "leader"

def random_timeout(base: float = 2.5, jitter: float = 2.0) -> float:
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
        self.election_timeout = random_timeout(2.5, 2.0)
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
        while not self._stop.is_set():
            # Simulate sensor reading
            value = random.uniform(20.0, 30.0)
            self.state.update_local(value)

            # Broadcast to peers (skip self)
            payload = sensor_update(self.node_id, value)
            for peer in self.peers:
                host, port = peer.split(":")
                if host == self.host and int(port) == self.port:
                    continue
                asyncio.create_task(send_message(host, int(port), payload))

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

            # Ignore our own heartbeat
            if leader_id == self.node_id:
                return

            if term >= self.term:
                if self.role != ROLE_FOLLOWER:
                    print(f"[{self.node_id}] -> FOLLOWER due to heartbeat from {leader_id} term={term} (prev role={self.role})")
                self.role = ROLE_FOLLOWER
                self.term = term
                self.voted_for = None
                self.last_heartbeat = time.time()
                self.election_timeout = random_timeout(2.5, 2.0)
            else:
                print(f"[{self.node_id}] Ignoring stale heartbeat from {leader_id} term={term} < local term={self.term}")
            return

        # RequestVote
        if "candidate_id" in msg and "term" in msg and "granted" not in msg:
            candidate_id = msg["candidate_id"]
            term = msg["term"]
            candidate_host = msg.get("candidate_host")
            candidate_port = int(msg.get("candidate_port", 0))

            # Step down if term is higher
            if term > self.term:
                if self.role != ROLE_FOLLOWER:
                    print(f"[{self.node_id}] -> FOLLOWER due to RequestVote from {candidate_id} term={term} (prev role={self.role})")
                self.role = ROLE_FOLLOWER
                self.term = term
                self.voted_for = None

            grant = False
            if term == self.term and (self.voted_for is None or self.voted_for == candidate_id):
                grant = True
                self.voted_for = candidate_id
                self.last_heartbeat = time.time()
                self.election_timeout = random_timeout(2.5, 2.0)

            # Reply directly to candidate if address provided; otherwise broadcast (fallback)
            response = vote_response(voter_id=self.node_id, term=self.term, granted=grant)
            if candidate_host and candidate_port:
                asyncio.create_task(send_message(candidate_host, candidate_port, response))
            else:
                for peer in self.peers:
                    host, port = peer.split(":")
                    if host == self.host and int(port) == self.port:
                        continue
                    asyncio.create_task(send_message(host, int(port), response))

            print(f"[{self.node_id}] Vote {'granted' if grant else 'denied'} for {candidate_id} (incoming term={term}, local term={self.term}, voted_for={self.voted_for})")
            return

        # VoteResponse
        if "voter_id" in msg and "granted" in msg and "term" in msg:
            voter_id = msg["voter_id"]
            granted = msg["granted"]
            term = msg["term"]

            # Higher-term response -> step down
            if term > self.term:
                if self.role != ROLE_FOLLOWER:
                    print(f"[{self.node_id}] Step down: higher term in vote response (term={term} > local={self.term})")
                self.role = ROLE_FOLLOWER
                self.term = term
                self.voted_for = None
                self.last_heartbeat = time.time()
                self.election_timeout = random_timeout(2.5, 2.0)
                return

            if self.role == ROLE_CANDIDATE and term == self.term and granted:
                self.votes_received.add(voter_id)
                total_nodes = len(self.peers) + 1  # self + peers
                majority = len(self.votes_received) > total_nodes // 2
                print(f"[{self.node_id}] Vote from {voter_id}: granted={granted}. Tally={len(self.votes_received)}/{total_nodes} (term={self.term})")

                if majority and self.role == ROLE_CANDIDATE:
                    self.role = ROLE_LEADER
                    self.last_heartbeat = time.time()  # prevent immediate timeout
                    print(f"[{self.node_id}] Became LEADER for term {self.term}")
                    asyncio.create_task(self.leader_heartbeat_loop())
            return

        # Unknown message type
        print(f"[{self.node_id}] Unrecognized message: {msg}")

    async def leader_heartbeat_loop(self):
        while not self._stop.is_set() and self.role == ROLE_LEADER:
            hb = heartbeat(leader_id=self.node_id, term=self.term)
            for peer in self.peers:
                host, port = peer.split(":")
                # Skip self
                if host == self.host and int(port) == self.port:
                    continue
                asyncio.create_task(send_message(host, int(port), hb))

            print(f"[{self.node_id}] Heartbeat (term={self.term})")
            self.last_heartbeat = time.time()  # refresh so watchdog doesn’t fire
            await asyncio.sleep(1.0)


    async def election_watchdog(self):
        while not self._stop.is_set():
            elapsed = time.time() - self.last_heartbeat

            # Only followers can trigger elections
            if self.role == ROLE_FOLLOWER and elapsed > self.election_timeout:
                print(f"[{self.node_id}] Election timeout ({elapsed:.2f}s). Starting election.")
                await self.start_election()

            # Candidates wait for votes; leaders send heartbeats separately
            await asyncio.sleep(0.2)
    async def start_election(self):
        # Transition to candidate
        self.role = ROLE_CANDIDATE
        self.term += 1
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}  # vote for self
        self.election_timeout = random_timeout(2.5, 2.0)

        print(f"[{self.node_id}] Starting election for term {self.term}")

        # Broadcast RequestVote to peers (skip self)
        rv = request_vote(
            candidate_id=self.node_id,
            term=self.term,
            candidate_host=self.host,
            candidate_port=self.port,
        )
        for peer in self.peers:
            host, port = peer.split(":")
            if host == self.host and int(port) == self.port:
                continue
            asyncio.create_task(send_message(host, int(port), rv))
