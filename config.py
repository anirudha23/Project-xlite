import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# === API Keys ===
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# === Trading Settings ===
SYMBOL = "BTC/USD"
TIMEFRAME = "15min"

# === Strategy Risk Settings ===
SL_PERCENT = 0.02  # 2% Stop Loss
TP_PERCENT = 0.04  # 4% Take Profit
