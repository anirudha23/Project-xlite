import time
import json
from strategy_engine import generate_signal
from send_signal import send_to_discord

def load_last_signal():
    try:
        with open("last_signal.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_last_signal(signal_data):
    with open("last_signal.json", "w") as f:
        json.dump(signal_data, f, indent=4)

def run_scheduler():
    while True:
        new_signal = generate_signal()
        if not new_signal:
            time.sleep(300)
            continue

        last_signal = load_last_signal()
        if new_signal != last_signal:
            send_to_discord(new_signal)
            save_last_signal(new_signal)

        time.sleep(300)  # Run every 5 mins
