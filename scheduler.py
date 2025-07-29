# scheduler.py (Improved 15-min interval scheduler)

import asyncio
import json
import os
import traceback
from datetime import datetime, timedelta
from send_signal import send_to_discord
from strategy_engine import run as generate_and_send_signal

SIGNAL_FILE = "last_signal.json"
TRACK_FILE = "last_sent_signal.json"

def load_json(file_path):
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading JSON from {file_path}: {e}")
    return {}

def save_json(file_path, data):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving JSON to {file_path}: {e}")

async def check_for_new_signal():
    current = load_json(SIGNAL_FILE)
    last = load_json(TRACK_FILE)

    if current and current != last:
        print("✅ New signal detected. Sending to Discord...")
        try:
            await send_to_discord(current)
            save_json(TRACK_FILE, current)
        except Exception as e:
            print(f"❌ Failed to send signal to Discord: {e}")
            traceback.print_exc()
    else:
        print("🔄 No new signal found.")

async def run_scheduler():
    print("📅 Scheduler started. Running every 15 minutes at aligned times (00:00, 00:15, 00:30, 00:45)...")

    while True:
        now = datetime.now()
        minutes = (now.minute // 15 + 1) * 15
        if minutes == 60:
            next_run = now.replace(hour=(now.hour + 1) % 24, minute=0, second=0, microsecond=0)
        else:
            next_run = now.replace(minute=minutes, second=0, microsecond=0)

        wait_time = (next_run - now).total_seconds()
        print(f"⏳ Next run scheduled at: {next_run.strftime('%H:%M:%S')} (in {int(wait_time)}s)")
        await asyncio.sleep(wait_time)

        try:
            print(f"\n⏰ Running strategy at {datetime.now().strftime('%H:%M:%S')}")
            await generate_and_send_signal()
            await check_for_new_signal()
        except Exception as e:
            print(f"🔥 Scheduler error: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_scheduler())
