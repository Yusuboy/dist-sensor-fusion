import asyncio
from src.core.node import Node
from src.ui.cluster_dashboard import run_cluster_dashboard

async def launch_node(node_id, port, peers):
    node = Node(node_id=node_id, host="127.0.0.1", port=port, peers=peers)
    asyncio.create_task(node.start())
    return node

async def main():
    # Define cluster
    peers_A = ["127.0.0.1:9001", "127.0.0.1:9002"]
    peers_B = ["127.0.0.1:9000", "127.0.0.1:9002"]
    peers_C = ["127.0.0.1:9000", "127.0.0.1:9001"]

    # Launch nodes
    nodeA = await launch_node("A", 9000, peers_A)
    nodeB = await launch_node("B", 9001, peers_B)
    nodeC = await launch_node("C", 9002, peers_C)

    # Launch unified dashboard for all nodes
    asyncio.create_task(run_cluster_dashboard([nodeA, nodeB, nodeC]))

    # Keep event loop alive
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
