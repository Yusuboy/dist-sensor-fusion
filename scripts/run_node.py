import asyncio
import sys
from src.core.node import Node

if __name__ == "__main__":
    node_id = sys.argv[1]
    port = int(sys.argv[2])
    peers = sys.argv[3].split(",") if len(sys.argv) > 3 else []

    node = Node(node_id=node_id, host="127.0.0.1", port=port, peers=peers)
    asyncio.run(node.start())
