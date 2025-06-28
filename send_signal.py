import discord
import json
import os
import logging
import time
from typing import Optional
from datetime import datetime
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('signal_bot.log'),
        logging.StreamHandler()
    ]
)

# Configuration from config.py
SYMBOL = Config.SYMBOL
RISK_REWARD = Config.RISK_REWARD

# Discord settings from environment
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

class SignalBot(discord.Client):
    async def on_ready(self):
        logging.info(f"Logged in as {self.user}")
        
        try:
            signal = self.read_signal()
            if not signal:
                logging.warning("No valid signal found")
                await self.close()
                return
                
            embed = self.create_embed(signal)
            channel = self.get_channel(CHANNEL_ID)
            
            if not channel:
                logging.error(f"Channel {CHANNEL_ID} not found")
                await self.close()
                return
                
            await channel.send(embed=embed)
            logging.info("Signal successfully sent")
            
        except Exception as e:
            logging.error(f"Error sending signal: {str(e)}")
        finally:
            await self.close()

    def read_signal(self) -> Optional[dict]:
        """Read and validate the signal file"""
        try:
            with open("last_signal.json") as f:
                signal = json.load(f)
                
            required_fields = {'direction', 'entry', 'sl', 'tp', 'time', 'confidence'}
            if not all(field in signal for field in required_fields):
                raise ValueError("Missing required signal fields")
                
            return signal
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logging.error(f"Signal validation failed: {str(e)}")
            return None

    def create_embed(self, signal: dict) -> discord.Embed:
        """Create Discord embed from signal"""
        color = discord.Color.green() if signal["direction"] == "BUY" else discord.Color.red()
        
        embed = discord.Embed(
            title=f"{SYMBOL} {signal['direction']} Signal",
            description=f"Confidence: {signal['confidence']*100:.1f}%",
            color=color,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Entry", value=signal["entry"], inline=True)
        embed.add_field(name="Stop Loss", value=signal["sl"], inline=True)
        embed.add_field(name="Take Profit", value=signal["tp"], inline=True)
        embed.add_field(name="Risk/Reward", value=f"1:{RISK_REWARD:.1f}", inline=True)
        embed.set_footer(text=f"Signal time: {signal['time']}")
        
        return embed

def run_bot():
    if not TOKEN or not CHANNEL_ID:
        logging.error("Missing Discord credentials")
        return
        
    for attempt in range(MAX_RETRIES):
        try:
            client = SignalBot(intents=discord.Intents.default())
            client.run(TOKEN)
            break
        except discord.LoginFailure:
            logging.error("Invalid Discord token")
            break
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logging.warning(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(RETRY_DELAY)
            else:
                logging.error(f"Failed after {MAX_RETRIES} attempts: {str(e)}")

if __name__ == "__main__":
    run_bot()