import asyncio
from datetime import datetime
from strategy_engine import run

async def run_scheduler():
    print("⏳ Scheduler started")
    while True:
        now = datetime.now()
        wait = (15 - now.minute % 15) * 60
        await asyncio.sleep(wait)
        await run()
