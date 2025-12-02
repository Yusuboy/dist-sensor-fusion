import json
import struct

def encode_message(msg: dict) -> bytes:
    """Encode dict to length-prefixed JSON bytes."""
    data = json.dumps(msg).encode("utf-8")
    length = struct.pack("!I", len(data))  # 4-byte length prefix
    return length + data

async def decode_message(reader) -> dict:
    """Decode one length-prefixed JSON message from stream."""
    length_bytes = await reader.readexactly(4)
    length = struct.unpack("!I", length_bytes)[0]
    data = await reader.readexactly(length)
    return json.loads(data.decode("utf-8"))
