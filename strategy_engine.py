import requests
import pandas as pd
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from send_signal import send_to_discord

load_dotenv()

TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
SYMBOL = "BTC/USD"
TIMEFRAME = "15m"

API_URL = (
    f"https://api.twelvedata.com/time_series?"
    f"symbol={SYMBOL}&interval=15min&apikey={TWELVE_API_KEY}&outputsize=200"
)

OPEN_TRADE_FILE = "open_trade.json"
TRADE_HISTORY_FILE = "trade_history.json"
LAST_SIGNAL_FILE = "last_signal.json"

def fetch_data():
    r = requests.get(API_URL).json()
    df = pd.DataFrame(r["values"])
    df.columns = df.columns.str.lower()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df[["open","high","low","close"]] = df[["open","high","low","close"]].astype(float)
    return df.sort_values("datetime")

def indicators(df):
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["upper"] = df["close"].rolling(20).mean() + 2 * df["close"].rolling(20).std()
    df["lower"] = df["close"].rolling(20).mean() - 2 * df["close"].rolling(20).std()
    return df

def load_json(file):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return None

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

async def run():
    df = indicators(fetch_data())
    last = df.iloc[-1]

    open_trade = load_json(OPEN_TRADE_FILE)

    # EXIT LOGIC
    if open_trade:
        price = last["close"]
        hit_tp = price >= open_trade["tp"] if open_trade["direction"] == "buy" else price <= open_trade["tp"]
        hit_sl = price <= open_trade["sl"] if open_trade["direction"] == "buy" else price >= open_trade["sl"]

        if hit_tp or hit_sl:
            result = "TP" if hit_tp else "SL"
            record = {
                "trade_id": f"BTCUSD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "symbol": SYMBOL,
                "timeframe": TIMEFRAME,
                "direction": open_trade["direction"],
                "entry_price": open_trade["entry"],
                "stop_loss": open_trade["sl"],
                "take_profit": open_trade["tp"],
                "exit_price": price,
                "risk": abs(open_trade["entry"] - open_trade["sl"]),
                "reward": abs(open_trade["tp"] - open_trade["entry"]),
                "pnl": abs(open_trade["tp"] - open_trade["entry"]) if hit_tp else -abs(open_trade["entry"] - open_trade["sl"]),
                "result": result,
                "entry_time": open_trade["entry_time"],
                "exit_time": datetime.now().isoformat(),
                "strategy": "bollinger_breakout"
            }

            history = load_json(TRADE_HISTORY_FILE) or []
            history.append(record)
            save_json(TRADE_HISTORY_FILE, history)
            save_json(OPEN_TRADE_FILE, {})

            await send_to_discord({
                "type": "Exit",
                "symbol": SYMBOL,
                "timeframe": TIMEFRAME,
                "direction": open_trade["direction"],
                "entry": open_trade["entry"],
                "sl": open_trade["sl"],
                "tp": open_trade["tp"],
                "time": record["exit_time"],
                "reason": f"{result} hit | PnL {record['pnl']}"
            })
        return

    # ENTRY LOGIC
    if last["close"] > last["upper"]:
        direction = "sell"
    elif last["close"] < last["lower"]:
        direction = "buy"
    else:
        return

    entry = last["close"]
    sl = entry * (1.02 if direction == "sell" else 0.98)
    tp = entry * (0.96 if direction == "sell" else 1.04)

    trade = {
        "direction": direction,
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "entry_time": datetime.now().isoformat()
    }

    save_json(OPEN_TRADE_FILE, trade)

    signal = {
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "direction": direction,
        "entry": trade["entry"],
        "sl": trade["sl"],
        "tp": trade["tp"],
        "time": trade["entry_time"],
        "reason": "Bollinger band breakout",
        "type": "Entry"
    }

    save_json(LAST_SIGNAL_FILE, signal)
    await send_to_discord(signal)
