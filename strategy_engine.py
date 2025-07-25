import json
import logging
import requests
import os
import pandas as pd
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
SYMBOL = "BTC/USD"
TIMEFRAME = "15min"
ALIGNMENT_BUFFER = 5  # seconds buffer after candle close

# === Logging setup ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_TIMEOUT = 30  # seconds
MIN_CANDLES = 50  # for indicator calculation

class Bollinger15MinLiveStrategy:
    def __init__(self):  # FIXED constructor name
        self.period = 20
        self.position = 0  # 0=no position, 1=long, -1=short
        self.entry_price = 0
        self.last_candle_time = None
        logging.info(f"🚀 Initialized Bollinger 15min Strategy for {SYMBOL} on {TIMEFRAME}")

    def is_new_candle_time(self):
        now = datetime.utcnow()
        expected_minute = (now.minute // 15) * 15
        target_time = now.replace(minute=expected_minute, second=0, microsecond=0)
        return (now - target_time) < timedelta(seconds=ALIGNMENT_BUFFER)

    def fetch_candles(self):
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": SYMBOL.replace("/", ""),
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
            candles = [{
                "time": c['datetime'],
                "open": float(c['open']),
                "high": float(c['high']),
                "low": float(c['low']),
                "close": float(c['close'])
            } for c in data['values']]
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
        if len(df) < self.period + 1:
            logging.warning("⛔ Not enough candles to generate signal")
            return None

        current = df.iloc[-1]
        prev = df.iloc[-2]

        price = current['close']
        ma20 = current['ma20']
        signal = None

        # Entry signals
        if self.position == 0:
            if current['close'] < current['lower'] and prev['close'] >= prev['lower']:
                signal = {
                    "action": "BUY",
                    "entry": round(price, 2),
                    "time": current['time'].isoformat()
                }
            elif current['close'] > current['upper'] and prev['close'] <= prev['upper']:
                signal = {
                    "action": "SELL",
                    "entry": round(price, 2),
                    "time": current['time'].isoformat()
                }

        # Exit signals
        elif self.position == 1 and price > ma20:
            signal = {
                "action": "EXIT_LONG",
                "exit_price": round(price, 2),
                "time": current['time'].isoformat()
            }
        elif self.position == -1 and price < ma20:
            signal = {
                "action": "EXIT_SHORT",
                "exit_price": round(price, 2),
                "time": current['time'].isoformat()
            }

        return signal

    def process_signal(self, signal):
        if signal is None:
            logging.info("No trade signal generated this cycle.")
            return

        action = signal["action"]

        if action == "BUY":
            self.position = 1
            self.entry_price = signal["entry"]
            logging.info(f"📈 Enter LONG @ {self.entry_price}")

        elif action == "SELL":
            self.position = -1
            self.entry_price = signal["entry"]
            logging.info(f"📉 Enter SHORT @ {self.entry_price}")

        elif action == "EXIT_LONG" and self.position == 1:
            profit = signal["exit_price"] - self.entry_price
            logging.info(f"🚪 Exit LONG @ {signal['exit_price']} | Profit: {profit:.2f}")
            self.position = 0
            self.entry_price = 0

        elif action == "EXIT_SHORT" and self.position == -1:
            profit = self.entry_price - signal["exit_price"]
            logging.info(f"🚪 Exit SHORT @ {signal['exit_price']} | Profit: {profit:.2f}")
            self.position = 0
            self.entry_price = 0

        # Save signal to JSON
        try:
            with open("last_signal.json", "w") as f:
                json.dump(signal, f, indent=4)
            logging.info("📩 Signal saved to last_signal.json")
        except Exception as e:
            logging.error(f"❌ Failed to save signal: {e}")

    def run(self):
        logging.info("📡 Starting Bollinger Bands Live Strategy")
        while True:
            now = datetime.utcnow()
            if self.is_new_candle_time():
                candles = self.fetch_candles()
                if candles:
                    df = pd.DataFrame(candles)
                    df = self.calculate_indicators(df)
                    signal = self.generate_signal(df)
                    self.process_signal(signal)
            # Sleep to next minute check
            time.sleep(60 - now.second)

# === Entry point ===
if __name__ == "__main__":  # FIXED
    bot = Bollinger15MinLiveStrategy()
    bot.run()
