import json
import logging
import requests
import os
import pandas as pd
import time
from datetime import datetime, timedelta, timezone  # ✅ timezone added
from dotenv import load_dotenv

# Load env variables
load_dotenv()
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
SYMBOL = "BTC/USD"
TIMEFRAME = "15min"
ALIGNMENT_BUFFER = 5  # seconds buffer after candle close to avoid API delay

# Risk reward config
RISK_REWARD = 1.5
STOP_LOSS_PERCENT = 0.01  # 1% stop loss

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_TIMEOUT = 30  # seconds
MIN_CANDLES = 50  # for indicator calc

class Bollinger15MinLiveStrategy:
    def __init__(self):
        self.period = 20
        self.position = 0  # 0=no pos, 1=long, -1=short
        self.entry_price = 0
        self.last_candle_time = None
        logging.info(f"🚀 Initialized Bollinger 15min Strategy for {SYMBOL} on {TIMEFRAME}")

    def is_new_candle_time(self):
        now = datetime.now(timezone.utc)  # ✅ timezone-aware datetime
        expected_minute = (now.minute // 15) * 15
        target_time = now.replace(minute=expected_minute, second=0, microsecond=0)
        return (now - target_time) < timedelta(seconds=ALIGNMENT_BUFFER)

    def fetch_candles(self):
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": SYMBOL.split('/')[0],
            "interval": TIMEFRAME,
            "outputsize": MIN_CANDLES,
            "apikey": TWELVE_API_KEY
        }
        try:
            response = requests.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            if 'values' not in data:
                logging.error(f"❌ API Error: {data.get('message', 'No candle data')}")
                return []
            candles = [ {
                "time": c['datetime'],
                "open": float(c['open']),
                "high": float(c['high']),
                "low": float(c['low']),
                "close": float(c['close'])
            } for c in data['values'] ]
            logging.info(f"✅ Fetched {len(candles)} candles")
            return candles
        except Exception as e:
            logging.error(f"❌ Exception fetching candles: {e}")
            return []

    def calculate_indicators(self, df: pd.DataFrame):
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time')
        df['ma20'] = df['close'].rolling(window=self.period).mean()
        df['stddev'] = df['close'].rolling(window=self.period).std()
        df['upper'] = df['ma20'] + 2 * df['stddev']
        df['lower'] = df['ma20'] - 2 * df['stddev']
        return df.dropna()

    def generate_signal(self, df: pd.DataFrame):
        if len(df) < MIN_CANDLES:
            logging.warning("⛔ Not enough candles to generate signal")
            return None

        current = df.iloc[-1]
        prev = df.iloc[-2]

        price = current['close']
        ma20 = current['ma20']

        signal = None

        if self.position == 0:
            if current['close'] < current['lower'] and prev['close'] >= prev['lower']:
                signal = {
                    "direction": "BUY",
                    "entry": round(price, 2),
                    "sl": round(price * (1 - STOP_LOSS_PERCENT), 2),
                    "tp": round(price + (price - price * (1 - STOP_LOSS_PERCENT)) * RISK_REWARD, 2),
                    "time": current['time'].isoformat(),
                    "confidence": 0.75
                }
            elif current['close'] > current['upper'] and prev['close'] <= prev['upper']:
                signal = {
                    "direction": "SELL",
                    "entry": round(price, 2),
                    "sl": round(price * (1 + STOP_LOSS_PERCENT), 2),
                    "tp": round(price - (price * (1 + STOP_LOSS_PERCENT) - price) * RISK_REWARD, 2),
                    "time": current['time'].isoformat(),
                    "confidence": 0.75
                }

        elif self.position == 1 and price > ma20:
            logging.info(f"🚪 Exit LONG @ {round(price, 2)}")
            self.position = 0
            self.entry_price = 0
            return None

        elif self.position == -1 and price < ma20:
            logging.info(f"🚪 Exit SHORT @ {round(price, 2)}")
            self.position = 0
            self.entry_price = 0
            return None

        return signal

    def process_signal(self, signal):
        if signal is None:
            logging.info("No trade signal generated this cycle.")
            return

        action = signal.get("direction")

        if action == "BUY":
            self.position = 1
            self.entry_price = signal["entry"]
            logging.info(f"📈 Enter LONG @ {self.entry_price}")

        elif action == "SELL":
            self.position = -1
            self.entry_price = signal["entry"]
            logging.info(f"📉 Enter SHORT @ {self.entry_price}")

        if action in ["BUY", "SELL"]:
            try:
                with open("last_signal.json", "w") as f:
                    json.dump(signal, f, indent=4)
                logging.info("📩 Signal saved to last_signal.json")
            except Exception as e:
                logging.error(f"❌ Failed to save signal: {e}")

    def run(self):
        logging.info("📡 Starting Bollinger Bands Live Strategy")
        while True:
            now = datetime.now(timezone.utc)  # ✅ timezone-aware
            if self.is_new_candle_time():
                candles = self.fetch_candles()
                if candles:
                    df = pd.DataFrame(candles)
                    df = self.calculate_indicators(df)
                    signal = self.generate_signal(df)
                    self.process_signal(signal)
            time.sleep(60 - now.second)

if __name__ == "__main__":
    bot = Bollinger15MinLiveStrategy()
    bot.run()
