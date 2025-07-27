import json
import os
from datetime import datetime
import time
from dotenv import load_dotenv
from strategy_engine import get_trade_signal
from send_signal import send_to_discord

# === Load Environment Variables ===
load_dotenv()
TRADE_HISTORY_FILE = "trade_history.json"
LAST_SIGNAL_FILE = "last_signal.json"

# === Load Previous Signal ===
def load_last_signal():
    if not os.path.exists(LAST_SIGNAL_FILE):
        return None
    with open(LAST_SIGNAL_FILE, "r") as f:
        return json.load(f)

# === Save New Signal ===
def save_last_signal(signal):
    with open(LAST_SIGNAL_FILE, "w") as f:
        json.dump(signal, f, indent=2)

# === Save Trade History ===
def save_trade_history(signal):
    if os.path.exists(TRADE_HISTORY_FILE):
        with open(TRADE_HISTORY_FILE, "r") as f:
            history = json.load(f)
    else:
        history = []

    history.append(signal)

    with open(TRADE_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

# === Scheduled Task ===
def run_scheduled_task():
    print(f"[{datetime.now()}] Running strategy engine...")

    signal = get_trade_signal()
    if signal is None:
        print("No valid signal generated.")
        return

    # Check against last signal to avoid duplicates
    last_signal = load_last_signal()
    if last_signal and signal["entry"] == last_signal.get("entry"):
        print("Duplicate signal. Skipping...")
        return

    # Save and send signal
    save_last_signal(signal)
    save_trade_history(signal)
    send_to_discord(signal)
    print("✅ New signal sent and saved.")

