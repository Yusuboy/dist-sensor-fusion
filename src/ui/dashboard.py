import asyncio
import os
from datetime import datetime

async def run_dashboard(node):
    """
    Live visualization of node state.
    This module depends only on the public attributes of Node.
    """
    while True:
        # Clear terminal
        os.system("clear" if os.name == "posix" else "cls")

        role = node.role.upper()
        term = node.term
        local_id = node.node_id

        print("─" * 50)
        print(f" Node {local_id}  |  Role: {role}  |  Term: {term}")
        print("─" * 50)

        print(" Global sensor state:")
        # node.state.data is a dict: {node_id: {value: x, timestamp: y}}
        for nid, entry in sorted(node.state.data.items()):
            value = entry.get("value")
            if value is not None:
                print(f"  {nid}: {value:.2f}")

        print("─" * 50)
        print(f" Updated: {datetime.now().strftime('%H:%M:%S')}")
        await asyncio.sleep(1)
