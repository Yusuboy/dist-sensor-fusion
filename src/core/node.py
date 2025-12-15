import asyncio
import random
import time
from typing import Optional

from src.core.state import GlobalState
from src.net.server import Server
from src.net.client import send_message
from src.proto.messages import (
    sensor_update,
    heartbeat,
    request_vote,
    vote_response,
    append_entries_msg,
    append_entries_resp,
    hello,
    hello_ack,
)

ROLE_FOLLOWER = "follower"
ROLE_CANDIDATE = "candidate"
ROLE_LEADER = "leader"

HANDSHAKE_RETRY_INTERVAL = 1.0      # seconds between HELLO retries
HANDSHAKE_MAX_RETRIES = 10          # max attempts before giving up and continuing


def random_timeout(base: float = 2.5, jitter: float = 2.0) -> float:
    return base + random.random() * jitter


class Node:
    def __init__(self, node_id: str, host: str, port: int, peers: list[str]):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.peers = peers

        # Cluster startup barrier state
        self.hello_from_peers: set[str] = set()  # peer_ids that sent HELLO to us
        self.ack_from_peers: set[str] = set()    # peer_ids that sent HELLO_ACK to us
        self.ready = asyncio.Event()             # set when cluster handshake is done

        # Sensor fusion state
        self.state = GlobalState(node_id)

        # Raft state
        self.role = ROLE_FOLLOWER
        self.term = 0
        
        self.voted_for: Optional[str] = None
        self.votes_received: set[str] = set()

        # Heartbeat & elections
        self.last_heartbeat = time.time()
        self.election_timeout = random_timeout()

        # AppendEntries log placeholders
        self.log: list[dict] = []  # list of {"index": int, "term": int, "command": Any}
        self.commit_index = 0
        self.last_applied = 0

        # Concurrency
        self._server: Optional[Server] = None
        self._stop = asyncio.Event()

        self.events = []  # dashboard log queue
        self.is_alive = True  # dashboard health flag

        self.control_port = self.port + 1000  # example: node A: 9000 → control at 10000

    # ----------------------------------------------------------------------
    # STARTUP & HANDSHAKE
    # ----------------------------------------------------------------------
    async def start(self):
        self._server = Server(self.host, self.port, self.handle_message)
        asyncio.create_task(self._server.start())
        asyncio.create_task(self.control_server())

        self.record_event("Waiting for cluster handshakes…")

        print(f"Node {self.node_id} waiting for cluster handshakes…")

        # Allow server to bind
        await asyncio.sleep(0.3)

        # Start handshake retry loop (non-blocking)
        asyncio.create_task(self.handshake_loop())

        # Wait for cluster barrier
        await self.ready.wait()

        print(f"[{self.node_id}] Cluster READY → starting main loops")

        asyncio.create_task(self.sensor_loop())
        asyncio.create_task(self.election_watchdog())

        print(f"Node {self.node_id} started at {self.host}:{self.port} [role={self.role}]")
        await self._stop.wait()

    def stop(self):
        if not self.is_alive:
            return
        self.is_alive = False
        self.record_event("Node shutting down")
        self._stop.set()


    async def control_server(self):
        """Listen for external commands like KILL."""
        control_port = self.port + 1000  # e.g. node on 9000 → control on 10000

        server = await asyncio.start_server(self.handle_control, self.host, control_port)
        print(f"[{self.node_id}] Control server on {self.host}:{control_port}")

        async with server:
            await server.serve_forever()

    async def handle_control(self, reader, writer):
        try:
            msg = (await reader.read(100)).decode().strip()
        except:
            writer.close()
            return

        if msg == "KILL":
            print(f"[{self.node_id}] Received external KILL → shutting down")
            self.stop()

        writer.close()
        await writer.wait_closed()


    async def handle_control(self, reader, writer):
        msg = (await reader.read(100)).decode().strip()

        if msg == "KILL":
            print(f"[{self.node_id}] received external kill command")
            self.stop()

        writer.close()
        await writer.wait_closed()




    def record_event(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {self.node_id}: {message}"
        self.events.append(entry)

        # Keep only recent events (avoid infinite memory)
        if len(self.events) > 200:
            self.events.pop(0)


    async def handshake_loop(self):
        retries = 0

        while not self.ready.is_set() and retries < HANDSHAKE_MAX_RETRIES:
            print(f"[{self.node_id}] Handshake attempt {retries + 1}/{HANDSHAKE_MAX_RETRIES}")
            await self.send_hello_to_peers()
            await asyncio.sleep(HANDSHAKE_RETRY_INTERVAL)
            retries += 1

        if not self.ready.is_set():
            print(f"[{self.node_id}] WARNING: cluster did NOT fully handshake. Continuing anyway.")
            self.ready.set()

    async def send_hello_to_peers(self):
        msg = hello(self.node_id, self.host, self.port)
        self.record_event("Sending HELLO to peers…")
        print(f"[{self.node_id}] Sending HELLO to peers…")

        for peer in self.peers:
            host, port = peer.split(":")
            asyncio.create_task(send_message(host, int(port), msg))

    def check_cluster_ready(self):
        expected = len(self.peers)

        # Condition: we have seen HELLO from all peers and HELLO_ACK from all peers
        if len(self.hello_from_peers) >= expected and len(self.ack_from_peers) >= expected:
            if not self.ready.is_set():
                self.record_event("All handshakes complete → cluster ready")

                print(f"[{self.node_id}] All handshakes complete → cluster ready")
                self.ready.set()

    # ----------------------------------------------------------------------
    # SENSOR LOOP
    # ----------------------------------------------------------------------
    async def sensor_loop(self):
        while not self._stop.is_set():
            value = random.uniform(20.0, 30.0)
            self.state.update_local(value)

            msg = sensor_update(self.node_id, value)

            # Broadcast to peers
            for peer in self.peers:
                host, port = peer.split(":")
                asyncio.create_task(send_message(host, int(port), msg))

            print(f"[{self.node_id}] Sensor update: {value:.2f}")
            await asyncio.sleep(5)

    # ----------------------------------------------------------------------
    # CENTRAL MESSAGE ROUTER
    # ----------------------------------------------------------------------
    async def handle_message(self, msg: dict):
        msg_type = msg.get("type")

        if msg_type == "HELLO":
            return await self.handle_hello(msg)

        if msg_type == "HELLO_ACK":
            return await self.handle_hello_ack(msg)

        if msg_type == "SENSOR_UPDATE":
            return await self.handle_sensor_update(msg)

        if msg_type == "HEARTBEAT":
            return await self.handle_heartbeat(msg)

        if msg_type == "REQUEST_VOTE":
            return await self.handle_request_vote(msg)

        if msg_type == "VOTE_RESPONSE":
            return await self.handle_vote_response(msg)

        if msg_type == "APPEND_ENTRIES":
            return await self.handle_append_entries(msg)

        if msg_type == "APPEND_ENTRIES_RESP":
            return await self.handle_append_entries_resp(msg)

        print(f"[{self.node_id}] Unknown message type: {msg}")

    # ----------------------------------------------------------------------
    # HANDSHAKE MESSAGE HANDLERS
    # ----------------------------------------------------------------------
    async def handle_hello(self, msg: dict):
        peer_id = msg["node_id"]
        peer_host = msg["host"]
        peer_port = msg["port"]

        self.record_event(f"HELLO from {peer_id} → ACK sent")
        print(f"[{self.node_id}] HELLO from {peer_id} → ACK sent")

        # Record HELLO from this peer
        self.hello_from_peers.add(peer_id)

        # Always send ACK back
        ack = hello_ack(self.node_id)
        asyncio.create_task(send_message(peer_host, int(peer_port), ack))

        self.check_cluster_ready()

    async def handle_hello_ack(self, msg: dict):
        peer_id = msg["node_id"]
        self.record_event(f"HELLO_ACK received from {peer_id}")

        print(f"[{self.node_id}] HELLO_ACK received from {peer_id}")

        # Record ACK from this peer
        self.ack_from_peers.add(peer_id)

        self.check_cluster_ready()

    # ----------------------------------------------------------------------
    # SENSOR & RAFT MESSAGE HANDLERS
    # ----------------------------------------------------------------------
    async def handle_sensor_update(self, msg: dict):
        self.state.merge({msg["node_id"]: msg})
        print(f"[{self.node_id}] merged sensor from {msg['node_id']}: {msg['value']}")

    async def handle_heartbeat(self, msg: dict):
        leader_id = msg["leader_id"]
        term = msg["term"]

        if leader_id == self.node_id:
            return

        if term >= self.term:
            if self.role != ROLE_FOLLOWER:
                print(f"[{self.node_id}] stepping down → FOLLOWER due to heartbeat from {leader_id}")

            self.role = ROLE_FOLLOWER
            self.term = term
            self.voted_for = None

            self.last_heartbeat = time.time()
            self.election_timeout = random_timeout()
        else:
            print(f"[{self.node_id}] ignoring stale heartbeat (term {term} < local {self.term})")

    async def handle_request_vote(self, msg: dict):
        candidate_id = msg["candidate_id"]
        term = msg["term"]

        if term > self.term:
            self.role = ROLE_FOLLOWER
            self.term = term
            self.voted_for = None

        grant = False

        if term == self.term and (self.voted_for is None or self.voted_for == candidate_id):
            grant = True
            self.voted_for = candidate_id
            self.last_heartbeat = time.time()
            self.election_timeout = random_timeout()

        response = vote_response(self.node_id, self.term, grant)
        asyncio.create_task(send_message(msg["candidate_host"], msg["candidate_port"], response))

        print(f"[{self.node_id}] Vote {'GRANTED' if grant else 'DENIED'} for {candidate_id}")

    async def handle_vote_response(self, msg: dict):
        if self.role != ROLE_CANDIDATE:
            return

        term = msg["term"]
        voter = msg["voter_id"]
        granted = msg["granted"]

        # Higher term → step down
        if term > self.term:
            self.record_event(f"Step down: higher-term vote from {voter}")
            self.role = ROLE_FOLLOWER
            self.term = term
            self.voted_for = None
            return

        # Log every vote
        self.record_event(f"Vote received from {voter} (granted={granted})")

        # Process granted votes
        if granted:
            self.votes_received.add(voter)
            total_nodes = len(self.peers) + 1

            # Become leader if majority reached
            if len(self.votes_received) > total_nodes // 2:
                self.role = ROLE_LEADER
                self.record_event(f"*** ELECTED LEADER for term {self.term} ***")
                asyncio.create_task(self.leader_heartbeat_loop())




    # ----------------------------------------------------------------------
    # APPEND ENTRIES (SIMPLIFIED)
    # ----------------------------------------------------------------------
    async def handle_append_entries(self, msg: dict):
        term = msg["term"]

        if term < self.term:
            # reject outdated leader
            resp = append_entries_resp(False, self.term, self.node_id, match_index=0)
            await self._reply_to_leader(msg, resp)
            return

        # accept leader
        self.role = ROLE_FOLLOWER
        self.term = term
        self.last_heartbeat = time.time()

        # simplified: accept entries and overwrite local log tail
        entries = msg["entries"]
        for entry in entries:
            index = entry["index"]
            while len(self.log) <= index:
                self.log.append(None)
            self.log[index] = entry

        # update commit index
        self.commit_index = msg["leader_commit"]

        resp = append_entries_resp(True, self.term, self.node_id, match_index=len(self.log) - 1)
        await self._reply_to_leader(msg, resp)

    async def handle_append_entries_resp(self, msg: dict):
        if self.role == ROLE_LEADER:
            success = msg["success"]
            follower = msg["follower_id"]
            print(f"[{self.node_id}] AppendEntriesResp from {follower}: success={success}")

    async def _reply_to_leader(self, msg: dict, resp: dict):
        # For now we don’t know leader's address → left as an academic stub
        pass

    # ----------------------------------------------------------------------
    # ELECTIONS
    # ----------------------------------------------------------------------
    async def election_watchdog(self):
        await asyncio.sleep(random.uniform(0.0, 0.5))
        while not self._stop.is_set():
            elapsed = time.time() - self.last_heartbeat

            if self.role == ROLE_FOLLOWER and elapsed > self.election_timeout:
                print(f"[{self.node_id}] election timeout → starting election")
                await self.start_election()

            await asyncio.sleep(0.2)

    async def start_election(self):
        self.role = ROLE_CANDIDATE
        self.term += 1

        # Self-vote
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}

        # Store who we asked votes from (for dashboard)
        self.vote_request_targets = list(self.peers)

        self.election_timeout = random_timeout()

        # DASHBOARD EVENT
        self.record_event(f"Starting election for term {self.term}")
        self.record_event(f"Requesting votes from: {', '.join(self.vote_request_targets)}")

        # Build vote-request message
        rv = request_vote(
            candidate_id=self.node_id,
            term=self.term,
            candidate_host=self.host,
            candidate_port=self.port,
        )

        # Send requests to all peers
        for peer in self.peers:
            host, port = peer.split(":")
            asyncio.create_task(send_message(host, int(port), rv))


    # ----------------------------------------------------------------------
    # LEADER HEARTBEATS
    # ----------------------------------------------------------------------
    async def leader_heartbeat_loop(self):
        self.record_event(f"Leader heartbeat loop started (term {self.term})")

        while self.role == ROLE_LEADER and not self._stop.is_set():
            msg = heartbeat(self.node_id, self.term)

            # Send heartbeat to all peers
            for peer in self.peers:
                host, port = peer.split(":")
                asyncio.create_task(send_message(host, int(port), msg))

            self.last_heartbeat = time.time()

            # RECORD IN DASHBOARD (instead of print)
            self.record_event(f"Heartbeat sent (term {self.term})")

            await asyncio.sleep(1.0)

