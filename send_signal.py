from bot_client import send_discord_message

async def send_to_discord(signal):
    msg = (
        f"🚨 {signal['type']} SIGNAL\n"
        f"Pair: {signal['symbol']}\n"
        f"TF: {signal['timeframe']}\n"
        f"Dir: {signal['direction']}\n"
        f"Entry: {signal['entry']}\n"
        f"SL: {signal['sl']}\n"
        f"TP: {signal['tp']}\n"
        f"Time: {signal['time']}\n"
        f"Reason: {signal['reason']}"
    )
    await send_discord_message(msg)
