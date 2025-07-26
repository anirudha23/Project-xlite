# Project X: Bollinger Band Bot (ai_engine.py)

import requests
import pandas as pd
import numpy as np
import json
import time
from datetime import datetime
from send_signal import send_to_discord

TWELVE_API_KEY = 'your_twelve_data_api_key'
DISCORD_WEBHOOK_URL = 'your_discord_webhook_url'
SYMBOL = 'BTC/USDT'
INTERVAL = '15min'

LAST_SIGNAL_FILE = 'last_signal.json'
TRADE_HISTORY_FILE = 'trade_history.json'

# === Helper Functions ===
def fetch_data():
    url = f"https://api.twelvedata.com/time_series?symbol=BTC/USD&interval=15min&apikey={TWELVE_API_KEY}&outputsize=50"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data['values'])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime')
    df.set_index('datetime', inplace=True)
    df = df.astype(float)
    return df

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
        return {"timestamp": "", "signal": "none"}

def save_last_signal(signal_data):
    with open(LAST_SIGNAL_FILE, 'w') as f:
        json.dump(signal_data, f, indent=4)

def save_trade_history(entry, sl, tp, direction, result):
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
        "confidence": np.random.randint(75, 95)  # simulated AI confidence
    }

def main():
    df = fetch_data()
    df = calculate_bollinger_bands(df)

    signal = generate_signal(df)
    if not signal:
        print("No trade setup.")
        return

    last_signal = load_last_signal()
    if last_signal.get("entry") == signal["entry"] and last_signal.get("direction") == signal["direction"]:
        print("Duplicate signal. Skipping.")
        return

    # Save signal and send to Discord
    save_last_signal(signal)
    send_to_discord(signal, DISCORD_WEBHOOK_URL)
    print("Signal sent:", signal)

if __name__ == "__main__":
    main()
