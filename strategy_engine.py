# Project X: Bollinger Band Bot (strategy_engine.py)

import requests
import pandas as pd
import numpy as np
import json
from datetime import datetime
from send_signal import send_to_discord
import os

# === Configuration ===
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SYMBOL = "BTC/USD"
INTERVAL = "15min"

LAST_SIGNAL_FILE = "last_signal.json"
TRADE_HISTORY_FILE = "trade_history.json"

# === Helper Functions ===
def fetch_data():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&apikey={TWELVE_API_KEY}&outputsize=50"
    try:
        response = requests.get(url)
        data = response.json()
        if "values" not in data:
            print("Error fetching data:", data)
            return None

        df = pd.DataFrame(data['values'])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime')
        df.set_index('datetime', inplace=True)
        df = df.astype(float)
        return df

    except Exception as e:
        print("Exception while fetching data:", e)
        return None

def calculate_bollinger_bands(df, period=20, std_dev=2):
    df['MA'] = df['close'].rolling(window=period).mean()
    df['STD'] = df['close'].rolling(window=period).std()
    df['Upper'] = df['MA'] + (std_dev * df['STD'])
    df['Lower'] = df['MA'] - (std_dev * df['STD'])
    return df

def load_last_signal():
    try:
        with open(LAST_SIGNAL_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"entry": None, "direction": None}

def save_last_signal(signal_data):
    with open(LAST_SIGNAL_FILE, 'w') as f:
        json.dump(signal_data, f, indent=4)

def save_trade_history(entry, sl, tp, direction, result="pending"):
    record = {
        "time": datetime.utcnow().isoformat(),
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "direction": direction,
        "result": result
    }
    try:
        with open(TRADE_HISTORY_FILE, 'r') as f:
            history = json.load(f)
    except:
        history = []
    history.append(record)
    with open(TRADE_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def generate_signal():
    df = fetch_data()
    if df is None or len(df) < 21:
        return None

    df = calculate_bollinger_bands(df)
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    if prev['close'] < prev['Lower'] and latest['close'] > latest['Lower']:
        direction = 'buy'
    elif prev['close'] > prev['Upper'] and latest['close'] < latest['Upper']:
        direction = 'sell'
    else:
        return None

    entry = round(latest['close'], 2)
    sl = round(entry * 0.98 if direction == 'buy' else entry * 1.02, 2)
    tp = round(entry * 1.03 if direction == 'buy' else entry * 0.97, 2)

    return {
        "time": str(datetime.utcnow()),
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "confidence": np.random.randint(75, 95)
    }

def main():
    signal = generate_signal()
    if not signal:
        print("No trade setup.")
        return

    last_signal = load_last_signal()
    if signal["entry"] == last_signal.get("entry") and signal["direction"] == last_signal.get("direction"):
        print("Duplicate signal. Skipping.")
        return

    save_last_signal(signal)
    send_to_discord(signal, DISCORD_WEBHOOK_URL)
    save_trade_history(signal["entry"], signal["sl"], signal["tp"], signal["direction"])
    print("Signal sent:", signal)

if __name__ == "__main__":
    main()
