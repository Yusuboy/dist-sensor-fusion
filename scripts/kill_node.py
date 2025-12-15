import os
import signal
import sys

node = sys.argv[1]

try:
    with open(f"/tmp/node_{node}.pid") as f:
        pid = int(f.read().strip())
    os.kill(pid, signal.SIGTERM)
    print(f"Killed node {node} (PID={pid})")
except FileNotFoundError:
    print(f"No PID file found for node {node}")
except ProcessLookupError:
    print(f"No running process with PID for node {node}")
