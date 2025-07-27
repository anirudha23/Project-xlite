# bot_client.py

import os
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Queue to hold messages that come before the bot is ready
message_queue = []

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    # Send all queued messages once bot is ready
    for content in message_queue:
        channel = client.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(content)
        else:
            print("❌ Channel not found")

async def send_discord_message(content: str):
    # If bot is ready, send immediately
    if client.is_ready():
        channel = client.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(content)
        else:
            print("❌ Channel not found")
    else:
        # Queue message if bot not ready
        message_queue.append(content)
