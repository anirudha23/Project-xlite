import asyncio
from datetime import datetime, timedelta
from strategy_engine import run

async def run_scheduler():
    print("⏳ Scheduler started (1H strategy)")

    while True:
        now = datetime.now()

        # Run just after a full 1H candle closes
        next_run = (now + timedelta(hours=1)).replace(
            minute=0,
            second=5,
            microsecond=0
        )

        wait_time = (next_run - now).total_seconds()
        print(f"⏱ Next strategy run at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        await asyncio.sleep(wait_time)

        await run()
