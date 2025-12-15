import asyncio
import sys

async def main():
    node = sys.argv[1].upper()
    control_ports = {"A": 10000, "B": 10001, "C": 10002}

    if node not in control_ports:
        print("Invalid node ID. Use A, B, or C.")
        return

    port = control_ports[node]
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
    except Exception as e:
        print(f"Node {node} not reachable: {e}")
        return

    writer.write(b"KILL")
    await writer.drain()
    writer.close()
    print(f"Sent KILL to node {node}")

asyncio.run(main())
