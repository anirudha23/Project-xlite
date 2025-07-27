# main.py

from flask import Flask
import threading
import time
import logging
import os
from strategy_engine import run_strategy
from scheduler import main as run_scheduler
from send_signal import send_to_discord

app = Flask(__name__)

# === Logging Setup ===
logging.basicConfig(level=logging.INFO)

# === 15-min Signal Engine ===
def signal_loop():
    while True:
        try:
            logging.info("📡 Running 15-min Signal Engine")
            signal = run_strategy()
            if signal:
                send_to_discord(signal)
        except Exception as e:
            logging.error(f"❌ Error in signal engine: {e}")
        time.sleep(900)  # every 15 min

# === 5-min Scheduler Loop ===
def scheduler_loop():
    while True:
        try:
            logging.info("🔁 Running 5-min Scheduler Task")
            run_scheduler()
        except Exception as e:
            logging.error(f"❌ Error in scheduler loop: {e}")
        time.sleep(300)  # every 5 min

# === Flask Route for Render Keep-Alive ===
@app.route('/')
def home():
    return "✅ Project X 1 AI Bot is Running!"

# === Start Threads and Flask ===
if __name__ == '__main__':
    threading.Thread(target=signal_loop, daemon=True).start()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
