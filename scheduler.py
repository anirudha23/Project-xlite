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

def get_live_btc_price():
    try:
        with open("last_signal.json") as f:
            data = json.load(f)
            price = data.get("entry")
            return price
    except:
        return None

def run_scheduler():
    logging.info("📅 Scheduler started!")

    while True:
        logging.info("⚙️ Running strategy_engine.py...")
        subprocess.run(["python3", "strategy_engine.py"])

        try:
            with open("last_signal.json") as f:
                signal = json.load(f)
        except Exception as e:
            logging.warning(f"⚠️ Could not read last_signal.json: {e}")
            time.sleep(300)
            continue

        new_time = signal.get("time", "")
        last_sent_time = load_last_sent_time()

        # 🟢 Print live BTC value to Render logs
        live_price = signal.get("entry")
        if live_price:
            logging.info(f"💰 Live BTC Entry Price: {live_price}")

        if new_time != last_sent_time:
            logging.info("📤 New signal detected! Sending to Discord...")
            subprocess.run(["python3", "send_signal.py"])
            save_last_sent_time(new_time)
        else:
            logging.info("🟡 No new signal to send.")

        time.sleep(300)  # Wait 5 minutes

if __name__ == "__main__":
    run_scheduler()
