import requests
import pandas as pd
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from send_signal import send_to_discord

load_dotenv()

TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
SYMBOL = "BTC/USD"
TIMEFRAME = "1h"

API_URL = (
    f"https://api.twelvedata.com/time_series?"
    f"symbol={SYMBOL}&interval={TIMEFRAME}&apikey={TWELVE_API_KEY}&outputsize=200"
)

OPEN_TRADE_FILE = "open_trade.json"
TRADE_HISTORY_FILE = "trade_history.json"
LAST_SIGNAL_FILE = "last_signal.json"

logging.basicConfig(level=logging.INFO)

# ---------------- DATA ---------------- #

def fetch_data():
    r = requests.get(API_URL).json()
    df = pd.DataFrame(r["values"])
    df.columns = df.columns.str.lower()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df[["open","high","low","close"]] = df[["open","high","low","close"]].astype(float)
    return df.sort_values("datetime").reset_index(drop=True)

# ---------------- STRATEGY ---------------- #

def apply_indicators(df):
    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["support"] = df["low"].rolling(10).min()
    df["resistance"] = df["high"].rolling(10).max()
    return df

def generate_entry(df):
    last, prev = df.iloc[-1], df.iloc[-2]

    if prev["close"] > prev["resistance"] and last["ema9"] > last["ema20"]:
        return create_trade("buy", last)

    if prev["close"] < prev["support"] and last["ema9"] < last["ema20"]:
        return create_trade("sell", last)

    return None

def create_trade(direction, candle):
    entry = candle["close"]
    sl = candle["support"] if direction == "buy" else candle["resistance"]
    tp = entry + 2 * (entry - sl) if direction == "buy" else entry - 2 * (sl - entry)

    return {
        "entry_time": str(candle["datetime"]),
        "direction": direction,
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2)
    }

def check_exit(df, trade):
    price = df.iloc[-1]["close"]

    if trade["direction"] == "buy":
        if price <= trade["sl"]:
            return exit_trade(trade, price, "SL")
        if price >= trade["tp"]:
            return exit_trade(trade, price, "TP")

    if trade["direction"] == "sell":
        if price >= trade["sl"]:
            return exit_trade(trade, price, "SL")
        if price <= trade["tp"]:
            return exit_trade(trade, price, "TP")

    return None

def exit_trade(trade, price, result):
    pnl = price - trade["entry"] if trade["direction"] == "buy" else trade["entry"] - price
    trade.update({
        "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "exit": round(price, 2),
        "pnl": round(pnl, 2),
        "result": result
    })
    return trade

# ---------------- STORAGE ---------------- #

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def load_json(file):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return None

# ---------------- MAIN ---------------- #

async def run():
    df = apply_indicators(fetch_data())
    open_trade = load_json(OPEN_TRADE_FILE)

    if open_trade:
        exit_trade_data = check_exit(df, open_trade)
        if exit_trade_data:
            history = load_json(TRADE_HISTORY_FILE) or []
            history.append(exit_trade_data)
            save_json(TRADE_HISTORY_FILE, history)
            save_json(OPEN_TRADE_FILE, {})
            await send_to_discord({
                "type": "Exit",
                "symbol": SYMBOL,
                "timeframe": TIMEFRAME,
                "direction": exit_trade_data["direction"],
                "entry": exit_trade_data["entry"],
                "sl": exit_trade_data["sl"],
                "tp": exit_trade_data["tp"],
                "time": exit_trade_data["exit_time"],
                "reason": f"{exit_trade_data['result']} | PnL {exit_trade_data['pnl']}"
            })
    else:
        entry = generate_entry(df)
        if entry:
            save_json(OPEN_TRADE_FILE, entry)
            await send_to_discord({
                "type": "Entry",
                "symbol": SYMBOL,
                "timeframe": TIMEFRAME,
                "direction": entry["direction"],
                "entry": entry["entry"],
                "sl": entry["sl"],
                "tp": entry["tp"],
                "time": entry["entry_time"],
                "reason": "EMA trend + Support/Resistance breakout"
            })

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
