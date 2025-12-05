import asyncio
import sys
from src.core.node import Node

async def main():
    node_id = sys.argv[1]
    port = int(sys.argv[2])
    peers = sys.argv[3].split(",") if len(sys.argv) > 3 else []

    node = Node(node_id=node_id, host="127.0.0.1", port=port, peers=peers)

    # Force A to act as leader for demo
    if node_id == "A":
        node.role = "leader"
        node.term = 1
        asyncio.create_task(node.leader_heartbeat_loop())

    await node.start()

if __name__ == "__main__":
    asyncio.run(main())
