import asyncio
import sys
from src.core.node import Node
from src.ui.dashboard import run_dashboard   # <- NEW

async def main():
    node_id = sys.argv[1]
    port = int(sys.argv[2])
    peers = sys.argv[3].split(",") if len(sys.argv) > 3 else []

    node = Node(node_id=node_id, host="127.0.0.1", port=port, peers=peers)

    # Start node logic (handshake, sensor loop, election, etc.)
    asyncio.create_task(node.start())

    # Start dashboard in parallel
    asyncio.create_task(run_dashboard(node))

    # Keep main alive forever
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
