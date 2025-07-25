import json
import time
import subprocess
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

def load_last_sent_time():
    try:
        with open("last_sent_time.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

def save_last_sent_time(timestamp):
    with open("last_sent_time.txt", "w") as f:
        f.write(timestamp)

def run_scheduler():
    logging.info("📅 Scheduler started!")
    while True:
        # Step 1: Run the strategy to generate signal
        subprocess.run(["python3", "strategy_engine.py"])

        # Step 2: Check if signal is new
        try:
            with open("last_signal.json") as f:
                signal = json.load(f)
        except Exception as e:
            logging.warning(f"⚠️ Could not read last_signal.json: {e}")
            time.sleep(300)
            continue

        new_time = signal.get("time", "")
        last_sent_time = load_last_sent_time()

        if new_time != last_sent_time:
            logging.info("📤 New signal detected! Sending to Discord...")
            subprocess.run(["python3", "send_signal.py"])
            save_last_sent_time(new_time)
        else:
            logging.info("🟡 No new signal to send.")

        time.sleep(300)  # Wait 5 minutes

if __name__ == "__main__":
    run_scheduler()
