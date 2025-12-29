from bot_client import send_discord_message

async def send_to_discord(signal: dict):
    msg = (
        f"🚨 **{signal['type']} SIGNAL** 🚨\n\n"
        f"**PAIR:** {signal['symbol']}\n"
        f"**TIMEFRAME:** {signal['timeframe']}\n"
        f"**DIRECTION:** {signal['direction'].upper()}\n"
        f"**ENTRY:** {signal['entry']}\n"
        f"**SL:** {signal['sl']}\n"
        f"**TP:** {signal['tp']}\n"
        f"**TIME:** {signal['time']}\n"
        f"**REASON:** {signal['reason']}"
    )
    await send_discord_message(msg)
