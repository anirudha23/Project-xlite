# main.py
from flask import Flask
import threading
import asyncio
import logging
import os
from strategy_engine import run as run_strategy
from evaluate_trades import evaluate_trade
from bot_client import client

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def signal_loop():
    while True:
        try:
            logging.info("📡 Running 15-min Signal Engine")
            run_strategy()
        except Exception as e:
            logging.error(f"❌ Error in signal loop: {e}")
        time.sleep(900)

def evaluation_loop():
    while True:
        try:
            logging.info("🔍 Checking trade outcomes")
            evaluate_trade()
        except Exception as e:
            logging.error(f"❌ Error in evaluation loop: {e}")
        time.sleep(300)

@app.route('/')
def home():
    return "✅ Project X 1 AI Bot is Running with Discord Bot!"

def start_discord_bot():
    asyncio.run(client.start(os.getenv("DISCORD_TOKEN")))

if __name__ == '__main__':
    threading.Thread(target=signal_loop, daemon=True).start()
    threading.Thread(target=evaluation_loop, daemon=True).start()
    threading.Thread(target=start_discord_bot, daemon=True).start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
