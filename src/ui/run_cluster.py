import asyncio
import subprocess
import signal
import os
from src.ui.cluster_dashboard import run_cluster_dashboard

NODE_CONFIG = {
    "A": ("9000", ["127.0.0.1:9001", "127.0.0.1:9002"]),
    "B": ("9001", ["127.0.0.1:9000", "127.0.0.1:9002"]),
    "C": ("9002", ["127.0.0.1:9000", "127.0.0.1:9001"]),
}

async def main():
    node_procs = {}

    # Launch nodes as OS subprocesses
    for nid, (port, peers) in NODE_CONFIG.items():
        cmd = [
            "python3",
            "-m",
            "scripts.run_node",
            nid,
            port,
            ",".join(peers)
        ]
        proc = subprocess.Popen(cmd)
        node_procs[nid] = proc
        print(f"Started node {nid} with PID {proc.pid}")

    print("\n=== All nodes started ===\n")
    print("Kill example in another terminal:")
    print("   kill -9 <PID_OF_NODE_A>")
    print()

    # Now launch dashboard
    await run_cluster_dashboard([])  # dashboard will poll state files eventually

if __name__ == "__main__":
    asyncio.run(main())
