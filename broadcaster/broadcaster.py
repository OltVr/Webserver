import os
import asyncio
import json
import aiohttp
from nats.aio.client import Client as NATS

# Environment/config
nats_url = os.getenv("NATS_URL", "nats://my-nats:4222")
discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
queue_group = os.getenv("NATS_QUEUE", "broadcaster")

if not discord_webhook_url:
    raise Exception("DISCORD_WEBHOOK_URL environment variable is required!")

async def send_to_discord(message):
    payload = {
        "content": message
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(discord_webhook_url, json=payload) as resp:
                if resp.status != 204:
                    print(f"Failed to send to Discord. Status: {resp.status}")
                else:
                    print("✅ Successfully sent message to Discord!")
        except Exception as e:
            print(f"Error sending to Discord: {e}")

async def message_handler(msg):
    data = msg.data.decode()
    print(f"📩 Received a message from NATS: {data}")
    await send_to_discord(data)

def safe_create_task(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.create_task(coro)

async def main():
    nc = NATS()

    while True:
        try:
            await nc.connect(servers=[nats_url])
            print(f"✅ Connected to NATS server at {nats_url}")
            break
        except Exception as e:
            print(f"❌ Waiting for NATS... {e}")
            await asyncio.sleep(2)

    async def subscribe():
        await nc.subscribe("todo.updates", queue=queue_group, cb=message_handler)
        print(f"✅ Subscribed to 'todo.updates' with queue group '{queue_group}'")

    await subscribe()

    # Keep the service alive
    print("📡 Broadcaster is now listening for todo updates...")
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    print("🚀 Starting Broadcaster Service...")
    safe_create_task(main())
    asyncio.get_event_loop().run_forever()