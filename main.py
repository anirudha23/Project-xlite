from keep_alive import keep_alive
import threading
import subprocess
import json
import time
import signal
import sys
import os
from datetime import datetime

# Handle Render's ephemeral storage
if 'RENDER' in os.environ:
    MODEL_FILE = '/tmp/trading_model.joblib'  # Render's ephemeral storage
    print("⚙️ Running on Render - using ephemeral storage")
else:
    MODEL_FILE = 'trading_model.joblib'
    print("⚙️ Running locally - using local storage")

# 🛡️ Ensure last_signal.json always exists to avoid FileNotFoundError
if not os.path.exists("last_signal.json"):
    with open("last_signal.json", "w") as f:
        json.dump({}, f)
    print("🆕 Created empty last_signal.json")

previous_signal = None
running = True

def signal_handler(sig, frame):
    global running
    print(f"\n🛑 Shutting down at {datetime.now().isoformat()}")
    print("🧹 Cleaning up before shutdown...")
    running = False
    sys.exit(0)

def read_last_signal():
    try:
        with open("last_signal.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ Signal read error: {str(e)}")
        return None

def run_scheduler():
    global previous_signal
    print(f"📅 Starting Intraday Precision Trader at {datetime.now().isoformat()}")

    while running:
        try:
            print(f"⏱️ Running strategy_engine.py at {datetime.now().isoformat()}")
            subprocess.run(["python3", "strategy_engine.py"], check=True, timeout=300)

            current_signal = read_last_signal()

            if current_signal:
                # Avoid duplicates: compare timestamps (or full content optionally)
                if previous_signal is None or current_signal["time"] != previous_signal.get("time"):
                    print(f"📡 New signal detected at {current_signal['time']}")
                    try:
                        subprocess.run(["python3", "send_signal.py"], check=True, timeout=60)
                        previous_signal = current_signal
                    except subprocess.TimeoutExpired:
                        print("❌ send_signal.py timed out")
                    except Exception as e:
                        print(f"❌ send_signal.py failed: {str(e)}")
                else:
                    print("⚠️ Duplicate signal — not sending again.")
            else:
                print("🔁 No new signal. Waiting...")

            print(f"🔄 Cycle completed at {datetime.now().isoformat()}")

        except subprocess.TimeoutExpired:
            print("❌ strategy_engine.py timed out")
        except Exception as e:
            print(f"❌ strategy_engine.py failed: {str(e)}")

        time.sleep(60)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start Flask server
    keep_alive()

    # Run scheduler thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        running = False
