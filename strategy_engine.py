# strategy_engine.py

import requests
import pandas as pd
import numpy as np
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from send_signal import send_to_discord_sync  # CHANGED

# === Load Config ===
load_dotenv()
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
SYMBOL = "BTC/USD"
INTERVAL = "15min"
API_URL = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&apikey={TWELVE_API_KEY}&outputsize=100&format=JSON"

# === File Paths ===
OPEN_TRADE_FILE = "open_trade.json"
TRADE_HISTORY_FILE = "trade_history.json"
LAST_SIGNAL_FILE = "last_signal.json"
LAST_TRADE_FILE = "last_trade.json"

# === Logging ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_btc_data():
    try:
        response = requests.get(API_URL)
        data = response.json()
        candles = data.get("values", [])
        df = pd.DataFrame(candles)
        df.columns = [col.lower() for col in df.columns]
        df["datetime"] = pd.to_datetime(df["datetime"])
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
        df = df.sort_values("datetime").reset_index(drop=True)
        return df
    except Exception as e:
        logging.error(f"[ERROR] Failed to fetch BTC data: {e}")
        return None

def apply_strategy(df):
    period = 20
    df['ma20'] = df['close'].rolling(window=period).mean()
    df['stddev'] = df['close'].rolling(window=period).std()
    df['upper'] = df['ma20'] + 2 * df['stddev']
    df['lower'] = df['ma20'] - 2 * df['stddev']
    df['buy_signal'] = df['close'] < df['lower']
    df['sell_signal'] = df['close'] > df['upper']
    return df

def load_open_trade():
    if os.path.exists(OPEN_TRADE_FILE):
        with open(OPEN_TRADE_FILE, 'r') as f:
            return json.load(f)
    return None

def save_open_trade(trade):
    with open(OPEN_TRADE_FILE, 'w') as f:
        json.dump(trade, f, indent=2)

def clear_open_trade():
    if os.path.exists(OPEN_TRADE_FILE):
        os.remove(OPEN_TRADE_FILE)

def save_trade_history(trade):
    history = []
    if os.path.exists(TRADE_HISTORY_FILE):
        with open(TRADE_HISTORY_FILE, 'r') as f:
            history = json.load(f)
    history.append(trade)
    with open(TRADE_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def save_last_signal(signal):
    with open(LAST_SIGNAL_FILE, 'w') as f:
        json.dump(signal, f, indent=2)

def save_last_trade(entry):
    trade = {
        "timestamp": entry['entry_time'],
        "direction": entry['direction'],
        "entry": round(entry['entry'], 2),
        "sl": round(entry['sl'], 2),
        "tp": round(entry['tp'], 2),
        "status": "open"
    }
    with open(LAST_TRADE_FILE, 'w') as f:
        json.dump(trade, f, indent=2)

def generate_entry(df):
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    std = previous['stddev']

    if latest['buy_signal']:
        entry = latest['close']
        return {
            "direction": "buy",
            "entry": entry,
            "sl": round(entry - (1.5 * std), 2),
            "tp": round(entry + (2.5 * std), 2),
            "entry_time": str(latest['datetime'])
        }
    elif latest['sell_signal']:
        entry = latest['close']
        return {
            "direction": "sell",
            "entry": entry,
            "sl": round(entry + (1.5 * std), 2),
            "tp": round(entry - (2.5 * std), 2),
            "entry_time": str(latest['datetime'])
        }
    return None

def check_exit(df, trade):
    latest = df.iloc[-1]
    price = latest['close']
    ma = latest['ma20']
    pl = 0
    exit_type = None

    if trade['direction'].lower() == 'buy':
        if price <= trade['sl']:
            exit_type = 'SL'
        elif price >= trade['tp']:
            exit_type = 'TP'
        elif price < ma:
            exit_type = 'MA20'
        pl = price - trade['entry']
    elif trade['direction'].lower() == 'sell':
        if price >= trade['sl']:
            exit_type = 'SL'
        elif price <= trade['tp']:
            exit_type = 'TP'
        elif price > ma:
            exit_type = 'MA20'
        pl = trade['entry'] - price

    if exit_type:
        return {
            "exit_price": price,
            "pnl": round(pl, 2),
            "exit_time": str(latest['datetime']),
            "exit_type": exit_type
        }
    return None

def run():
    df = fetch_btc_data()
    if df is None or df.empty:
        logging.warning("[WARNING] Empty DataFrame received")
        return

    df = apply_strategy(df)
    open_trade = load_open_trade()

    if open_trade:
        logging.info("📉 Open trade found. Checking for exit signal...")
        exit_info = check_exit(df, open_trade)
        if exit_info:
            signal = {
                "symbol": SYMBOL,
                "timeframe": INTERVAL,
                "direction": open_trade['direction'],
                "entry": open_trade['entry'],
                "sl": open_trade['sl'],
                "tp": open_trade['tp'],
                "time": exit_info['exit_time'],
                "reason": f"Exit via {exit_info['exit_type']} with P/L: {exit_info['pnl']}"
            }
            send_to_discord_sync(signal)
            save_last_signal(signal)
            open_trade.update(exit_info)
            save_trade_history(open_trade)
            clear_open_trade()
        else:
            logging.info("❌ No exit signal found.")
    else:
        logging.info("📈 No open trade. Checking for entry signal...")
        entry = generate_entry(df)
        if entry:
            logging.info("✅ Entry signal found. Sending entry signal to Discord.")
            signal = {
                "symbol": SYMBOL,
                "timeframe": INTERVAL,
                "direction": entry['direction'],
                "entry": entry['entry'],
                "sl": entry['sl'],
                "tp": entry['tp'],
                "time": entry['entry_time'],
                "reason": "Bollinger band breakout"
            }
            send_to_discord_sync(signal)
            save_last_signal(signal)
            save_open_trade(entry)
            save_last_trade(entry)
        else:
            logging.info("❌ No trade signal found.")

if __name__ == "__main__":
    run()
