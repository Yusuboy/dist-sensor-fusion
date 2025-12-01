from dataclasses import dataclass
import hashlib
import time

@dataclass
class SensorValue:
    value: float
    timestamp: float

class GlobalState:
    def __init__(self, node_id: str):
        # Each entry: node_id -> SensorValue
        self.node_id = node_id
        self.state = {node_id: SensorValue(value=None, timestamp=0.0)}

    def update_local(self, value: float):
        """Update this node's own sensor reading."""
        ts = time.time()
        self.state[self.node_id] = SensorValue(value=value, timestamp=ts)

    def merge(self, incoming: dict):
        """
        Merge incoming state into local state.
        Policy: last-writer-wins per node_id using timestamp.
        """
        for nid, entry in incoming.items():
            if nid not in self.state or entry["timestamp"] > self.state[nid].timestamp:
                self.state[nid] = SensorValue(value=entry["value"], timestamp=entry["timestamp"])

    def to_dict(self) -> dict:
        """Convert to serializable dict for messages."""
        return {nid: {"value": sv.value, "timestamp": sv.timestamp} for nid, sv in self.state.items()}

    def digest(self) -> str:
        """Stable hash of current state for checkpoint proposals."""
        # Sort by node_id for determinism
        items = sorted((nid, sv.value, sv.timestamp) for nid, sv in self.state.items())
        raw = str(items).encode()
        return hashlib.sha256(raw).hexdigest()
