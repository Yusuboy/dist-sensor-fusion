import asyncio
import random
import time
from core.state import GlobalState
from net.server import Server
from net.client import send_message
from proto.messages import SensorUpdate

class Node:
    def __init__(self, node_id: str, host: str, port: int, peers: list[str]):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.peers = peers
        self.state = GlobalState(node_id)

    async def start(self):
        # Start server to receive messages
        server = Server(self.host, self.port, self.handle_message)
        asyncio.create_task(server.start())

        # Periodically generate sensor readings
        asyncio.create_task(self.sensor_loop())

        print(f"Node {self.node_id} started on {self.host}:{self.port}")
        await asyncio.Event().wait()  # keep running

    async def sensor_loop(self):
        while True:
            # Simulate sensor reading
            value = random.uniform(20.0, 30.0)
            self.state.update_local(value)

            msg = SensorUpdate(
                node_id=self.node_id,
                value=value,
                timestamp=time.time()
            )

            # Broadcast to peers
            for peer in self.peers:
                host, port = peer.split(":")
                asyncio.create_task(send_message(host, int(port), msg.__dict__))

            print(f"[{self.node_id}] Sensor update: {value:.2f}")
            await asyncio.sleep(5)  # every 5 seconds

    async def handle_message(self, msg: dict):
        # For now, only handle SENSOR_UPDATE
        if "node_id" in msg and "value" in msg:
            self.state.merge({msg["node_id"]: msg})
            print(f"[{self.node_id}] Merged update from {msg['node_id']}: {msg['value']}")
