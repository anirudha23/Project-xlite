import json
import logging
import requests
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# === Load .env ===
load_dotenv()
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
SYMBOL = "BTC/USD"
TIMEFRAME = "15min"
API_TIMEOUT = 30
MIN_CANDLES = 50

# === Logging ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class Bollinger15MinLiveStrategy:
    def __init__(self):
        self.period = 20
        self.position = 0
        self.entry_price = 0
        self.last_signal_file = "last_signal.json"
        logging.info(f"✅ Strategy initialized for {SYMBOL} on {TIMEFRAME}")

    def fetch_candles(self):
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": SYMBOL.split('/')[0],  # Use BTC instead of BTC/USD
            "interval": TIMEFRAME,
            "outputsize": MIN_CANDLES,
            "apikey": TWELVE_API_KEY
        }
        try:
            response = requests.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if 'values' not in data:
                logging.error(f"❌ API Error: {data.get('message', 'No values in response')}")
                return []

            candles = [
                {
                    "time": c['datetime'],
                    "open": float(c['open']),
                    "high": float(c['high']),
                    "low": float(c['low']),
                    "close": float(c['close'])
                } for c in data['values']
            ]
            return candles
        except Exception as e:
            logging.error(f"❌ Exception fetching candles: {e}")
            return []

    def calculate_indicators(self, df):
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time')
        df['ma20'] = df['close'].rolling(window=self.period).mean()
        df['stddev'] = df['close'].rolling(window=self.period).std()
        df['upper'] = df['ma20'] + 2 * df['stddev']
        df['lower'] = df['ma20'] - 2 * df['stddev']
        return df.dropna()

    def generate_signal(self, df):
        if len(df) < self.period + 2:
            logging.warning("⚠️ Not enough candles to generate signal.")
            return None

        current = df.iloc[-1]
        prev = df.iloc[-2]
        price = current['close']
        signal = None
        direction = None

        if self.position == 0:
            if current['close'] < current['lower'] and prev['close'] >= prev['lower']:
                direction = "BUY"
            elif current['close'] > current['upper'] and prev['close'] <= prev['upper']:
                direction = "SELL"

        if direction:
            signal = {
                "symbol": SYMBOL,
                "direction": direction,
                "entry": round(price, 2),
                "sl": round(price * 0.98 if direction == "BUY" else price * 1.02, 2),
                "tp": round(price * 1.02 if direction == "BUY" else price * 0.98, 2),
                "confidence": 80,
                "timeframe": TIMEFRAME,
                "time": current['time'].isoformat()
            }
            logging.info(f"✅ Signal generated: {signal}")
        else:
            logging.info("ℹ️ No signal conditions met.")
        return signal

    def save_signal(self, signal):
        try:
            with open(self.last_signal_file, "w") as f:
                json.dump(signal, f, indent=4)
            logging.info("📁 Signal saved to last_signal.json")
        except Exception as e:
            logging.error(f"❌ Failed to save signal: {e}")

    def run_once(self):
        candles = self.fetch_candles()
        if not candles:
            logging.warning("🚫 No candles fetched.")
            return

        df = pd.DataFrame(candles)
        df = self.calculate_indicators(df)
        signal = self.generate_signal(df)

        if signal:
            self.save_signal(signal)

if __name__ == "__main__":
    strategy = Bollinger15MinLiveStrategy()
    strategy.run_once()
