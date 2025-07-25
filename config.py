import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Trading Parameters
    SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')
    TIMEFRAME = os.getenv('TIMEFRAME', '15m')
    RISK_REWARD = float(os.getenv('RISK_REWARD', 1.5))
    
    # Model Settings
    MODEL_REFRESH_HOURS = 24
    MAX_TRADES = 5