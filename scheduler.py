import asyncio
from datetime import datetime, timedelta
from strategy_engine import run

async def run_scheduler():
    print("⏳ Scheduler started (1H strategy)")

    while True:
        now = datetime.utcnow()

        next_run = (now + timedelta(hours=1)).replace(
            minute=0, second=5, microsecond=0
        )

        wait_time = (next_run - now).total_seconds()

        print(
            f"🕒 UTC now: {now.strftime('%H:%M:%S')} | "
            f"Next run: {next_run.strftime('%H:%M:%S')} | "
            f"Sleeping {int(wait_time)}s"
        )

        await asyncio.sleep(wait_time)

        print("🚀 Running strategy...")
        await run()
        print("✅ Strategy cycle complete\n")
