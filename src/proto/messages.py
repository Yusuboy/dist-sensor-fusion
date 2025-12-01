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

@dataclass
class StateUpdate:
    state_map: dict
    checkpoint_id: int | None = None

@dataclass
class Heartbeat:
    leader_id: str
    term: int
    timestamp: float

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
