from dataclasses import dataclass, asdict
import json
import time

def now_ts() -> float:
    return time.time()

# --- Sensor and state messages ---
@dataclass
class SensorUpdate:
    node_id: str
    value: float
    timestamp: float

def sensor_update(node_id: str, value: float) -> dict:
    return {
        "node_id": node_id,
        "value": value,
        "timestamp": time.time(),
    }

@dataclass
class StateUpdate:
    state_map: dict
    checkpoint_id: int | None = None

# --- Leader election messages ---
@dataclass
class ElectionRequest:
    candidate_id: str
    term: int
    last_state_ts: float

@dataclass
class ElectionVote:
    voter_id: str
    term: int
    vote_granted: bool

# --- Checkpoint consensus messages ---
@dataclass
class CheckpointPropose:
    checkpoint_id: int
    term: int
    state_digest: str
    timestamp: float

@dataclass
class CheckpointAck:
    follower_id: str
    checkpoint_id: int
    term: int

# --- Serialization helpers ---
def to_json(msg) -> str:
    return json.dumps(asdict(msg))

def from_json(msg_type, data: str):
    return msg_type(**json.loads(data))



@dataclass
class Heartbeat:
    leader_id: str
    term: int
    timestamp: float

def heartbeat(leader_id: str, term: int) -> dict:
    return {
        "leader_id": leader_id,
        "term": term,
        "timestamp": time.time(),
    }

@dataclass
class RequestVote:
    candidate_id: str
    term: int
    candidate_host: str
    candidate_port: int
    timestamp: float

def request_vote(candidate_id: str, term: int, candidate_host: str, candidate_port: int) -> dict:
    return {
        "candidate_id": candidate_id,
        "term": term,
        "candidate_host": candidate_host,
        "candidate_port": candidate_port,
        "timestamp": time.time(),
    }
@dataclass
class VoteResponse:
    voter_id: str
    term: int
    granted: bool
    timestamp: float

def vote_response(voter_id: str, term: int, granted: bool) -> dict:
    return {
        "voter_id": voter_id,
        "term": term,
        "granted": granted,
        "timestamp": time.time(),
    }

def append_entries_msg(term, leader_id, prev_log_index, prev_log_term, entries, leader_commit):
    return {
        "type": "APPEND_ENTRIES",
        "term": term,
        "leader_id": leader_id,
        "prev_log_index": prev_log_index,
        "prev_log_term": prev_log_term,
        "entries": entries,  # list of {"index": int, "term": int, "command": Any}
        "leader_commit": leader_commit,
    }

def append_entries_resp(success, term, follower_id, match_index):
    return {
        "type": "APPEND_ENTRIES_RESP",
        "term": term,
        "follower_id": follower_id,
        "success": success,
        "match_index": match_index,  # last index the follower has replicated
    }
