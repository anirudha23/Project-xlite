import os
import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(
            "🟢 **Project X is LIVE!**\n"
            "🤖 Discord bot connected successfully\n"
            "⏱ Scheduler initialized\n"
            "📡 Waiting for next signal..."
        )
    else:
        print("❌ Discord channel not found")

async def send_discord_message(message: str):
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(message)
