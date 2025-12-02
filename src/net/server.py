import asyncio
from src.net.codec import decode_message

class Server:
    def __init__(self, host: str, port: int, handler):
        self.host = host
        self.port = port
        self.handler = handler  # callback to process messages

    async def start(self):
        server = await asyncio.start_server(self.handle_conn, self.host, self.port)
        print(f"Server listening on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

    async def handle_conn(self, reader, writer):
        try:
            msg = await decode_message(reader)
            await self.handler(msg)
        except Exception as e:
            print(f"Error handling connection: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
