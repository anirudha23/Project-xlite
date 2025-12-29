import os
import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
STARTUP_FLAG_FILE = "startup_sent.flag"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

    if os.path.exists(STARTUP_FLAG_FILE):
        print("ℹ️ Startup message already sent")
        return

    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(
            "🟢 **Project X is LIVE**\n"
            "⏱ 4H S/R + 1H EMA rejection strategy running\n"
            "📡 Waiting for next 1H candle..."
        )
        with open(STARTUP_FLAG_FILE, "w") as f:
            f.write("sent")

async def send_discord_message(msg):
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(msg)
