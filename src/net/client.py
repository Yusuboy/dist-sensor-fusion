import asyncio
from src.net.codec import encode_message

async def send_message(host: str, port: int, msg: dict):
    try:
        reader, writer = await asyncio.open_connection(host, port)
        writer.write(encode_message(msg))
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        print(f"Failed to send to {host}:{port} -> {e}")
