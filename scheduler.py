# scheduler.py (ASYNC VERSION)

import asyncio
import json
import os
from send_signal import send_to_discord
from strategy_engine import run as generate_and_send_signal

SIGNAL_FILE = "last_signal.json"
TRACK_FILE = "last_sent_signal.json"

def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return {}

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

async def check_for_new_signal():
    current = load_json(SIGNAL_FILE)
    last = load_json(TRACK_FILE)

    if current != last and current != {}:
        print("✅ New signal detected. Sending to Discord...")
        await send_to_discord(current)
        save_json(TRACK_FILE, current)
    else:
        print("🔄 No new signal found.")

async def run_scheduler():
    print("📅 Async scheduler started. Checking every 5 minutes...")
    while True:
        await generate_and_send_signal()
        await check_for_new_signal()
        await asyncio.sleep(300)  # 5 minutes
