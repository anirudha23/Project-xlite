import time
import json
from strategy_engine import generate_signal, load_last_signal, save_last_signal
from send_signal import send_to_discord

def run_scheduler():
    while True:
        print("Checking for new signal...")
        new_signal = generate_signal()
        if not new_signal:
            print("No signal generated.")
            time.sleep(300)
            continue

        last_signal = load_last_signal()
        if new_signal != last_signal:
            send_to_discord(new_signal)
            save_last_signal(new_signal)
            print("New signal sent:", new_signal)
        else:
            print("Same signal, not sending.")

        time.sleep(300)  # Run every 5 minutes

if __name__ == "__main__":
    run_scheduler()
