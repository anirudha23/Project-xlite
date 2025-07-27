# scheduler.py

import time
import schedule
import json
import os
from send_signal import send_to_discord

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

def check_for_new_signal():
    current = load_json(SIGNAL_FILE)
    last = load_json(TRACK_FILE)

    if current != last and current != {}:
        print("✅ New signal detected. Sending to Discord...")
        send_to_discord(current)
        save_json(TRACK_FILE, current)
    else:
        print("🔄 No new signal found.")

def run_scheduler():
    schedule.every(5).minutes.do(check_for_new_signal)
    print("📅 Scheduler is running every 5 minutes...")

    while True:
        schedule.run_pending()
        time.sleep(1)
