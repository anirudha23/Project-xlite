# start_bot.py

import asyncio
from bot_client import client  # Your Discord bot
from scheduler import run_scheduler  # Your signal loop

async def main():
    print("✅ Project X bot starting...")

    # Start scheduler in background
    asyncio.create_task(run_scheduler())  # runs every 15 minutes

    # Start Discord bot (blocks the main thread)
    await client.start()

if __name__ == "__main__":
    asyncio.run(main())
