import discord
import json
import os
import logging
import time
from datetime import datetime
from dotenv import load_dotenv

# === Load environment variables from .env ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# === Config ===
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# === Logging Setup ===
logging.basicConfig(level=logging.INFO)

class SignalBot(discord.Client):
    async def on_ready(self):
        logging.info(f"✅ Logged in as {self.user}")

        # Load signal JSON
        try:
            with open("last_signal.json", "r") as f:
                signal = json.load(f)
        except FileNotFoundError:
            logging.error("❌ last_signal.json not found.")
            await self.close()
            return
        except json.JSONDecodeError:
            logging.error("❌ last_signal.json is not a valid JSON.")
            await self.close()
            return

        required_fields = {"symbol", "direction", "entry", "sl", "tp", "time"}
        if not required_fields.issubset(signal):
            logging.error("❌ Signal JSON missing required fields.")
            await self.close()
            return

        embed_color = discord.Color.green() if signal["direction"].upper() == "BUY" else discord.Color.red()
        embed = discord.Embed(
            title=f"{signal['symbol']} {signal['direction']} Signal",
            color=embed_color,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Entry", value=f"${signal['entry']}", inline=True)
        embed.add_field(name="Stop Loss", value=f"${signal['sl']}", inline=True)
        embed.add_field(name="Take Profit", value=f"${signal['tp']}", inline=True)
        embed.set_footer(text=f"📅 Signal Time: {signal['time']}")

        # Send to channel
        channel = self.get_channel(CHANNEL_ID)
        if channel is None:
            logging.error(f"❌ Discord channel with ID {CHANNEL_ID} not found.")
        else:
            await channel.send(embed=embed)
            logging.info("📨 Signal sent successfully!")

        await self.close()

def run_bot():
    if not TOKEN or not CHANNEL_ID:
        logging.error("❌ Missing DISCORD_TOKEN or DISCORD_CHANNEL_ID in .env.")
        return

    for attempt in range(MAX_RETRIES):
        try:
            client = SignalBot(intents=discord.Intents.default())
            client.run(TOKEN)
            break
        except Exception as e:
            logging.error(f"❌ Attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                logging.error("❌ Max retries reached. Exiting.")

if __name__ == "__main__":
    run_bot()
