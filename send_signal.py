# send_signal.py

import requests
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_to_discord(signal: dict):
    if not DISCORD_WEBHOOK_URL:
        print("Discord webhook URL not found.")
        return

    trade_type = signal.get("type", "Entry")
    content = f"🚨 **{trade_type.upper()} SIGNAL** 🚨\n\n" \
              f"**PAIR:** {signal['symbol']}\n" \
              f"**Timeframe:** {signal['timeframe']}\n" \
              f"**Direction:** {signal['direction'].upper()}\n" \
              f"**Entry:** {signal['entry']}\n" \
              f"**SL:** {signal['sl']}\n" \
              f"**TP:** {signal['tp']}\n" \
              f"**Time:** {signal['time']}\n" \
              f"Reason: {signal['reason']}\n"

    payload = {
        "content": content
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code == 204:
            print("✅ Signal sent to Discord.")
        else:
            print(f"❌ Failed to send signal. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Discord send error: {e}")
