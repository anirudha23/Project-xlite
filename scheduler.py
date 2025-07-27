# scheduler.py (FIXED ASYNC VERSION)

import asyncio
import json
import os
import traceback
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
    print("📅 Async scheduler started. Checking every 5 minutes...")
    while True:
        try:
            await asyncio.to_thread(generate_and_send_signal)
            await check_for_new_signal()
        except Exception as e:
            print(f"🔥 Scheduler error: {e}")
            traceback.print_exc()
        await asyncio.sleep(300)  # Wait 5 minutes before next cycle
