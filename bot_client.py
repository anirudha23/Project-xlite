# bot_client.py

import os
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def send_discord_message(content: str):
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(content)
    else:
        print("❌ Channel not found")

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
