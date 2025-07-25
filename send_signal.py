import discord
import json
import os
import logging
import time
from datetime import datetime

# Config & env variables
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

logging.basicConfig(level=logging.INFO)

class SignalBot(discord.Client):
    async def on_ready(self):
        logging.info(f"Logged in as {self.user}")
        try:
            with open("last_signal.json") as f:
                signal = json.load(f)

            required_fields = {"direction", "entry", "sl", "tp", "time", "confidence"}
            if not required_fields.issubset(signal.keys()):
                logging.error("Signal JSON missing required fields")
                await self.close()
                return

            embed_color = discord.Color.green() if signal["direction"] == "BUY" else discord.Color.red()

            embed = discord.Embed(
                title=f"BTC/USD {signal['direction']} Signal",
                description=f"Confidence: {signal['confidence']*100:.1f}%",
                color=embed_color,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Entry", value=str(signal["entry"]), inline=True)
            embed.add_field(name="Stop Loss", value=str(signal["sl"]), inline=True)
            embed.add_field(name="Take Profit", value=str(signal["tp"]), inline=True)
            embed.set_footer(text=f"Signal time: {signal['time']}")

            channel = self.get_channel(CHANNEL_ID)
            if channel is None:
                logging.error(f"Discord channel {CHANNEL_ID} not found")
                await self.close()
                return

            await channel.send(embed=embed)
            logging.info("Signal sent successfully")

        except Exception as e:
            logging.error(f"Error in sending signal: {e}")
        finally:
            await self.close()

def run_bot():
    if not TOKEN or not CHANNEL_ID:
        logging.error("Discord credentials missing")
        return

    for attempt in range(MAX_RETRIES):
        try:
            client = SignalBot(intents=discord.Intents.default())
            client.run(TOKEN)
            break
        except Exception as e:
            logging.error(f"Attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                logging.error("Max retries reached. Exiting.")

if __name__ == "__main__":
    run_bot()
