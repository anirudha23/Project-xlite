# statergy_engine.py

import os
import time
import json
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# === Load API ===
load_dotenv()
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
SYMBOL = "BTC/USD"
INTERVAL = "15min"
MEMORY_FILE = "ai_memory.json"

def fetch_candles():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize=100&apikey={TWELVE_API_KEY}"
    response = requests.get(url)
    data = response.json()
    if "values" not in data:
        print("❌ Error fetching candles:", data)
        return None
    df = pd.DataFrame(data["values"])
    df = df.iloc[::-1]
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["high"] = pd.to_numeric(df["high"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"], errors="coerce")
    df.dropna(inplace=True)
    return df

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {"buy_wins": 1, "buy_losses": 1, "sell_wins": 1, "sell_losses": 1}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)

def apply_strategy(df, memory):
    df["ma20"] = df["close"].rolling(window=20).mean()
    df["stddev"] = df["close"].rolling(window=20).std()
    df["upper"] = df["ma20"] + 2 * df["stddev"]
    df["lower"] = df["ma20"] - 2 * df["stddev"]
    df["buy_signal"] = df["close"] < df["lower"]
    df["sell_signal"] = df["close"] > df["upper"]

    # AI adaptive filter
    buy_winrate = memory["buy_wins"] / (memory["buy_wins"] + memory["buy_losses"])
    sell_winrate = memory["sell_wins"] / (memory["sell_wins"] + memory["sell_losses"])
    df["ai_buy"] = df["buy_signal"] & (buy_winrate > 0.5)
    df["ai_sell"] = df["sell_signal"] & (sell_winrate > 0.5)
    return df

def generate_signal(df):
    latest = df.iloc[-1]
    price = latest["close"]
    print(f"📈 BTC Live: ${price:.2f} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    signal_data = {
        "symbol": "BTC/USDT",
        "direction": "none",
        "entry": round(price, 2),
        "sl": None,
        "tp": None,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if latest["ai_buy"]:
        signal_data["direction"] = "BUY"
        signal_data["sl"] = round(price * 0.99, 2)
        signal_data["tp"] = round(price * 1.02, 2)
    elif latest["ai_sell"]:
        signal_data["direction"] = "SELL"
        signal_data["sl"] = round(price * 1.01, 2)
        signal_data["tp"] = round(price * 0.98, 2)

    return signal_data

def save_signal(signal):
    with open("last_signal.json", "w") as f:
        json.dump(signal, f, indent=4)
    print(f"✅ SIGNAL: {signal['direction']} | Entry: {signal['entry']} | SL: {signal['sl']} | TP: {signal['tp']}")

def run_ai_engine():
    df = fetch_candles()
    if df is None:
        return
    memory = load_memory()
    df = apply_strategy(df, memory)
    signal = generate_signal(df)
    if signal["direction"] != "none":
        save_signal(signal)
    else:
        print("⏳ No valid trade setup found.")

if __name__ == "__main__":
    run_ai_engine()
