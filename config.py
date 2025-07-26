import os
from dotenv import load_dotenv

load_dotenv()

TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SYMBOL = "BTC/USD"
TIMEFRAME = "15min"
