import asyncio
from datetime import datetime
from strategy_engine import run

async def run_scheduler():
    while True:
        now = datetime.now()
        wait = (60 - now.minute % 60) * 60
        await asyncio.sleep(wait)
        await run()

if __name__ == "__main__":
    asyncio.run(run_scheduler())
