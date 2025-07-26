import time
from strategy_engine import generate_signal, load_last_signal, save_last_signal, save_trade_history
from send_signal import send_to_discord
import os

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def run_scheduler():
    while True:
        print("Checking for new signal...")
        new_signal = generate_signal()
        if not new_signal:
            print("No signal generated.")
        else:
            last_signal = load_last_signal()
            if (
                new_signal["entry"] != last_signal.get("entry")
                or new_signal["direction"] != last_signal.get("direction")
            ):
                send_to_discord(new_signal, DISCORD_WEBHOOK_URL)
                save_last_signal(new_signal)
                save_trade_history(new_signal["entry"], new_signal["sl"], new_signal["tp"], new_signal["direction"])
                print("✅ New signal sent:", new_signal)
            else:
                print("Duplicate signal. Not sending.")

        time.sleep(300)  # Wait 5 minutes before next run

if __name__ == "__main__":
    run_scheduler()
