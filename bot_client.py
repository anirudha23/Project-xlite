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

    # 🔒 Prevent duplicate startup messages
    if os.path.exists(STARTUP_FLAG_FILE):
        print("ℹ️ Startup message already sent, skipping.")
        return

    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(
            "🟢 **Project X is LIVE!**\n"
            "🤖 Discord bot connected successfully\n"
            "⏱ Scheduler initialized\n"
            "📡 Waiting for next signal..."
        )

        # Create lock file
        with open(STARTUP_FLAG_FILE, "w") as f:
            f.write("sent")

        print("✅ Startup message sent.")
    else:
        print("❌ Discord channel not found")

async def send_discord_message(message: str):
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(message)
