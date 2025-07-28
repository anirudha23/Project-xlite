# smart_bot.py

import asyncio
from bot_client import client  # Your Discord bot instance
from scheduler import run_scheduler  # Your signal generation scheduler

async def main():
    print("✅ Project X bot starting...")

    # Start the signal scheduler loop in the background
    asyncio.create_task(run_scheduler())  # Runs every 5 minutes

    # Start the Discord bot (this blocks the main thread)
    try:
        await client.start()
    except Exception as e:
        print(f"❌ Discord bot failed to start: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot stopped by user.")
