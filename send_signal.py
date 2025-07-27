# send_signal.py

import asyncio
from bot_client import client, send_discord_message

def format_signal(signal: dict) -> str:
    trade_type = signal.get("type", "Entry")
    return (
        f"🚨 **{trade_type.upper()} SIGNAL** 🚨\n\n"
        f"**PAIR:** {signal['symbol']}\n"
        f"**Timeframe:** {signal['timeframe']}\n"
        f"**Direction:** {signal['direction'].upper()}\n"
        f"**Entry:** {signal['entry']}\n"
        f"**SL:** {signal['sl']}\n"
        f"**TP:** {signal['tp']}\n"
        f"**Time:** {signal['time']}\n"
        f"Reason: {signal['reason']}\n"
    )

def send_to_discord(signal: dict):
    message = format_signal(signal)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(send_discord_message(message))
    else:
        asyncio.ensure_future(send_discord_message(message))
