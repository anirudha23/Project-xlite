import os
import requests
from dotenv import load_dotenv
load_dotenv()

WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")

def send_to_discord(signal):
    msg = f"**{signal['type']} Signal**\nEntry: {signal['entry']}\nSL: {signal['sl']}\nTP: {signal['tp']}\nConfidence: {signal['confidence'] * 100}%"
    data = {"content": msg}
    requests.post(WEBHOOK, json=data)
