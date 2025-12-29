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

HTF_INTERVAL = "4h"
LTF_INTERVAL = "1h"

OPEN_TRADE_FILE = "open_trade.json"
TRADE_HISTORY_FILE = "trade_history.json"
LAST_SIGNAL_FILE = "last_signal.json"

# ---------- UTIL ---------- #

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def fetch_data(interval, limit=200):
    url = (
        f"https://api.twelvedata.com/time_series?"
        f"symbol={SYMBOL}&interval={interval}"
        f"&apikey={TWELVE_API_KEY}&outputsize={limit}"
    )
    values = requests.get(url).json()["values"]
    df = pd.DataFrame(values)
    df.columns = df.columns.str.lower()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df[["open","high","low","close"]] = df[["open","high","low","close"]].astype(float)
    return df.sort_values("datetime").reset_index(drop=True)

# ---------- STRATEGY ---------- #

def get_support_resistance(df, lookback=30):
    return df["low"].rolling(lookback).min().iloc[-1], \
           df["high"].rolling(lookback).max().iloc[-1]

def apply_ema(df):
    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema20"] = df["close"].ewm(span=20).mean()
    return df

async def run():
    print("📊 Strategy run started")

    df_4h = fetch_data(HTF_INTERVAL)
    support, resistance = get_support_resistance(df_4h)
    print(f"🧱 4H Support={support:.2f} Resistance={resistance:.2f}")

    df_1h = apply_ema(fetch_data(LTF_INTERVAL))
    last, prev = df_1h.iloc[-1], df_1h.iloc[-2]

    print(f"📈 EMA9={last['ema9']:.2f} EMA20={last['ema20']:.2f}")

    open_trade = load_json(OPEN_TRADE_FILE)

    # ---------- EXIT ---------- #
    if open_trade:
        print("📂 Open trade found, checking exit")
        price = last["close"]
        hit_tp = price >= open_trade["tp"] if open_trade["direction"] == "buy" else price <= open_trade["tp"]
        hit_sl = price <= open_trade["sl"] if open_trade["direction"] == "buy" else price >= open_trade["sl"]

        if hit_tp or hit_sl:
            result = "TP" if hit_tp else "SL"
            pnl = price - open_trade["entry"] if open_trade["direction"] == "buy" else open_trade["entry"] - price

            record = {
                "trade_id": f"BTC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "symbol": SYMBOL,
                "timeframe": "1h",
                "direction": open_trade["direction"],
                "entry_price": open_trade["entry"],
                "stop_loss": open_trade["sl"],
                "take_profit": open_trade["tp"],
                "exit_price": price,
                "pnl": pnl,
                "result": result,
                "entry_time": open_trade["entry_time"],
                "exit_time": datetime.utcnow().isoformat(),
                "strategy": "HTF_SR_EMA_REJECTION"
            }

            history = load_json(TRADE_HISTORY_FILE) or []
            history.append(record)
            save_json(TRADE_HISTORY_FILE, history)
            save_json(OPEN_TRADE_FILE, {})

            await send_to_discord({
                "type": "Exit",
                "symbol": SYMBOL,
                "timeframe": "1h",
                "direction": open_trade["direction"],
                "entry": open_trade["entry"],
                "sl": open_trade["sl"],
                "tp": open_trade["tp"],
                "time": record["exit_time"],
                "reason": f"{result} hit | PnL {round(pnl,2)}"
            })
        return

    # ---------- ENTRY ---------- #
    trend_up = last["ema9"] > last["ema20"]
    trend_down = last["ema9"] < last["ema20"]

    buy_rejection = (
        (last["low"] <= last["ema9"] or last["low"] <= last["ema20"]) and
        last["close"] > last["ema9"] and
        (last["close"] - last["low"]) > abs(last["open"] - last["close"])
    )

    sell_rejection = (
        (last["high"] >= last["ema9"] or last["high"] >= last["ema20"]) and
        last["close"] < last["ema9"] and
        (last["high"] - last["close"]) > abs(last["open"] - last["close"])
    )

    if trend_up and prev["close"] > resistance and buy_rejection:
        direction = "buy"
    elif trend_down and prev["close"] < support and sell_rejection:
        direction = "sell"
    else:
        print("❌ No valid setup this candle")
        return

    entry = last["close"]
    sl = support if direction == "buy" else resistance
    tp = entry + 2 * abs(entry - sl) if direction == "buy" else entry - 2 * abs(sl - entry)

    trade = {
        "direction": direction,
        "entry": round(entry,2),
        "sl": round(sl,2),
        "tp": round(tp,2),
        "entry_time": datetime.utcnow().isoformat()
    }

    save_json(OPEN_TRADE_FILE, trade)

    signal = {
        "type": "Entry",
        "symbol": SYMBOL,
        "timeframe": "1h",
        "direction": direction,
        "entry": trade["entry"],
        "sl": trade["sl"],
        "tp": trade["tp"],
        "time": trade["entry_time"],
        "reason": "4H S/R break + EMA9/20 rejection (1H)"
    }

    save_json(LAST_SIGNAL_FILE, signal)
    await send_to_discord(signal)
