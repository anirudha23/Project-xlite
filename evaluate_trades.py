# evaluate_trades.py

import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
SYMBOL = "BTC/USD"
TRADE_HISTORY_FILE = "trade_history.json"
OPEN_TRADE_FILE = "open_trade.json"

def get_live_price():
    url = f"https://api.twelvedata.com/price?symbol={SYMBOL}&apikey={TWELVE_API_KEY}"
    try:
        response = requests.get(url).json()
        return float(response["price"])
    except Exception as e:
        print(f"❌ Failed to fetch price: {e}")
        return None

def evaluate_trade():
    if not os.path.exists(OPEN_TRADE_FILE):
        return

    with open(OPEN_TRADE_FILE, "r") as f:
        open_trade = json.load(f)

    if not open_trade:
        return

    price = get_live_price()
    if price is None:
        return

    hit = None
    direction = open_trade["direction"]
    entry = open_trade["entry"]
    sl = open_trade["sl"]
    tp = open_trade["tp"]

    if direction == "buy":
        if price <= sl:
            hit = "SL"
        elif price >= tp:
            hit = "TP"
    elif direction == "sell":
        if price >= sl:
            hit = "SL"
        elif price <= tp:
            hit = "TP"

    if hit:
        print(f"📉 Trade closed: {hit} hit at {price}")
        result = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "entry": entry,
            "exit": price,
            "type": direction,
            "result": hit
        }

        # Append to trade history
        if os.path.exists(TRADE_HISTORY_FILE):
            with open(TRADE_HISTORY_FILE, "r") as f:
                history = json.load(f)
        else:
            history = []

        history.append(result)

        with open(TRADE_HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)

        # Clear the open trade
        with open(OPEN_TRADE_FILE, "w") as f:
            json.dump({}, f, indent=2)

        return result

if __name__ == "__main__":
    evaluate_trade()
