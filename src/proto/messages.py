"""
Message Protocol for Distributed Sensor Fusion + Raft-style Leader Election
---------------------------------------------------------------------------
Every message in the system follows a unified structure:

{
    "type": "<MESSAGE_TYPE>",
    "term": <int>,                  # for all consensus messages
    "timestamp": <float>,           # sending time
    ... message-specific fields ...
}

MESSAGE TYPES
-------------
1. SENSOR_UPDATE
    - node_id: str
    - value: float
    - timestamp: float

2. HEARTBEAT
    - leader_id: str
    - term: int

3. REQUEST_VOTE
    - candidate_id: str
    - candidate_host: str
    - candidate_port: int
    - term: int

4. VOTE_RESPONSE
    - voter_id: str
    - granted: bool
    - term: int

5. APPEND_ENTRIES
    - leader_id: str
    - term: int
    - prev_log_index: int
    - prev_log_term: int
    - entries: list of { index, term, command }
    - leader_commit: int

6. APPEND_ENTRIES_RESP
    - follower_id: str
    - success: bool
    - match_index: int
    - term: int
"""

import time


def now():
    return time.time()


# ---------------------------------------------------------------------------
# SENSOR UPDATE MESSAGE
# ---------------------------------------------------------------------------
def sensor_update(node_id: str, value: float) -> dict:
    return {
        "type": "SENSOR_UPDATE",
        "node_id": node_id,
        "value": value,
        "timestamp": now(),
    }


# ---------------------------------------------------------------------------
# HEARTBEAT (Leader → Followers)
# ---------------------------------------------------------------------------
def heartbeat(leader_id: str, term: int) -> dict:
    return {
        "type": "HEARTBEAT",
        "leader_id": leader_id,
        "term": term,
        "timestamp": now(),
    }


# ---------------------------------------------------------------------------
# REQUEST VOTE (Candidate → All)
# ---------------------------------------------------------------------------
def request_vote(candidate_id: str, term: int, candidate_host: str, candidate_port: int) -> dict:
    return {
        "type": "REQUEST_VOTE",
        "candidate_id": candidate_id,
        "candidate_host": candidate_host,
        "candidate_port": candidate_port,
        "term": term,
        "timestamp": now(),
    }


# ---------------------------------------------------------------------------
# VOTE RESPONSE (Follower → Candidate)
# ---------------------------------------------------------------------------
def vote_response(voter_id: str, term: int, granted: bool) -> dict:
    return {
        "type": "VOTE_RESPONSE",
        "voter_id": voter_id,
        "term": term,
        "granted": granted,
        "timestamp": now(),
    }


# ---------------------------------------------------------------------------
# LOG REPLICATION MESSAGES (Raft AppendEntries)
# ---------------------------------------------------------------------------
def append_entries_msg(term, leader_id, prev_log_index, prev_log_term, entries, leader_commit):
    return {
        "type": "APPEND_ENTRIES",
        "term": term,
        "leader_id": leader_id,
        "prev_log_index": prev_log_index,
        "prev_log_term": prev_log_term,
        "entries": entries,
        "leader_commit": leader_commit,
        "timestamp": now(),
    }


def append_entries_resp(success, term, follower_id, match_index):
    return {
        "type": "APPEND_ENTRIES_RESP",
        "success": success,
        "term": term,
        "follower_id": follower_id,
        "match_index": match_index,
        "timestamp": now(),
    }

def hello(node_id: str, host: str, port: int):
    return {
        "type": "HELLO",
        "node_id": node_id,
        "host": host,
        "port": port,
        "timestamp": time.time(),
    }

def hello_ack(node_id: str):
    return {
        "type": "HELLO_ACK",
        "node_id": node_id,
        "timestamp": time.time(),
    }