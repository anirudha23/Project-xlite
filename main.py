# main.py

from flask import Flask
import threading
import time
import logging
import os
from strategy_engine import run as run_strategy
from evaluate_trades import evaluate_trade

app = Flask(__name__)

# Logging
logging.basicConfig(level=logging.INFO)

# 15-minute signal runner
def signal_loop():
    while True:
        try:
            logging.info("📡 Running 15-min Signal Engine")
            run_strategy()
        except Exception as e:
            logging.error(f"❌ Error in signal loop: {e}")
        time.sleep(900)  # 15 minutes

# Optional: auto evaluate every 5 mins
def evaluation_loop():
    while True:
        try:
            logging.info("🔍 Checking trade outcomes")
            evaluate_trade()
        except Exception as e:
            logging.error(f"❌ Error in evaluation loop: {e}")
        time.sleep(300)  # 5 minutes

@app.route('/')
def home():
    return "✅ Project X 1 AI Bot is Running!"

if __name__ == '__main__':
    threading.Thread(target=signal_loop, daemon=True).start()
    threading.Thread(target=evaluation_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
