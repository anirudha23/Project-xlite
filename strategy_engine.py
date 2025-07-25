import json
import logging
import requests
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import random

# === Load environment variables ===
load_dotenv()
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
SYMBOL = "BTC/USD"
TIMEFRAME = "15min"

# === Logging setup ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_TIMEOUT = 30  # seconds

class SMC_BOS_FVG_Strategy:
    def __init__(self):
        self.fvg_lookback = 3
        self.swing_lookback = 5
        self.min_candles = 100
        logging.info(f"✅ Strategy Initialized: SMC_BOS_FVG | Symbol: {SYMBOL} | TF: {TIMEFRAME}")

    def fetch_candles(self):
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": SYMBOL,
            "interval": TIMEFRAME,
            "outputsize": 500,
            "apikey": TWELVE_API_KEY
        }
        try:
            response = requests.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if 'values' not in data:
                logging.error(f"❌ API Error: {data.get('message', 'No data returned')}")
                return []

            candles = [{
                "time": c['datetime'],
                "open": float(c['open']),
                "high": float(c['high']),
                "low": float(c['low']),
                "close": float(c['close'])
            } for c in data['values']]

            logging.info(f"✅ Fetched {len(candles)} candles.")
            return candles

        except Exception as e:
            logging.exception("❌ Exception while fetching candles")
            return []

    def calculate_indicators(self, df: pd.DataFrame):
        try:
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time')

            df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
            df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

            df['swing_high'] = (df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(-1))
            df['swing_low'] = (df['low'] < df['low'].shift(1)) & (df['low'] < df['low'].shift(-1))

            df['fvg_bullish'] = (df['low'].shift(2) > df['high'].shift(1)) & (df['low'].shift(2) > df['high'])
            df['fvg_bearish'] = (df['high'].shift(2) < df['low'].shift(1)) & (df['high'].shift(2) < df['low'])

            return df.dropna()
        except Exception as e:
            logging.exception("❌ Error calculating indicators")
            return pd.DataFrame()

    def detect_trend(self, df, i):
        try:
            return 'bullish' if df['ema_50'].iloc[i] > df['ema_200'].iloc[i] else 'bearish'
        except:
            logging.warning("⚠️ Trend detection fallback to sideways")
            return 'sideways'

    def detect_bos(self, df, i, direction):
        try:
            if direction == 'bullish':
                return df['close'].iloc[i] > df['high'].iloc[i - self.swing_lookback:i].max()
            elif direction == 'bearish':
                return df['close'].iloc[i] < df['low'].iloc[i - self.swing_lookback:i].min()
            return False
        except:
            logging.warning("⚠️ BOS detection failed")
            return False

    def detect_rejection_candle(self, df, i, direction):
        try:
            if i < 1:
                return False
            body = abs(df['close'].iloc[i] - df['open'].iloc[i])
            candle_range = df['high'].iloc[i] - df['low'].iloc[i]
            if candle_range == 0:
                return False
            if direction == 'bullish':
                prev_bear = df['close'].iloc[i-1] < df['open'].iloc[i-1]
                engulf = df['close'].iloc[i] > df['open'].iloc[i-1] and df['open'].iloc[i] < df['close'].iloc[i-1]
                return prev_bear and engulf and (body / candle_range > 0.5)
            elif direction == 'bearish':
                prev_bull = df['close'].iloc[i-1] > df['open'].iloc[i-1]
                engulf = df['close'].iloc[i] < df['open'].iloc[i-1] and df['open'].iloc[i] > df['close'].iloc[i-1]
                return prev_bull and engulf and (body / candle_range > 0.5)
            return False
        except:
            logging.warning("⚠️ Rejection candle detection failed")
            return False

    def detect_trade_signal(self):
        candles = self.fetch_candles()
        if len(candles) < self.min_candles:
            logging.warning("⛔ Not enough candles to evaluate.")
            return None

        df = pd.DataFrame(candles)
        df = self.calculate_indicators(df)
        if df.empty or len(df) < self.min_candles:
            logging.warning("⛔ Not enough data after indicators.")
            return None

        i = len(df) - 1
        current = df.iloc[i]
        trend = self.detect_trend(df, i)
        rr = round(random.uniform(1.5, 2.0), 2)

        if trend == 'bullish' and any(df['fvg_bullish'].iloc[i - self.fvg_lookback:i]) and self.detect_bos(df, i, 'bullish') and self.detect_rejection_candle(df, i, 'bullish'):
            entry = current['close']
            sl = min(current['low'], df['low'].iloc[i-1])
            tp = entry + rr * (entry - sl)
            signal = {
                "symbol": SYMBOL,
                "time": current['time'].isoformat(),
                "direction": "BUY",
                "entry": round(entry, 2),
                "sl": round(sl, 2),
                "tp": round(tp, 2),
                "rr_ratio": rr,
                "strategy": "SMC_BOS_FVG"
            }
            logging.info("✅ BUY Signal Detected")
            return signal

        elif trend == 'bearish' and any(df['fvg_bearish'].iloc[i - self.fvg_lookback:i]) and self.detect_bos(df, i, 'bearish') and self.detect_rejection_candle(df, i, 'bearish'):
            entry = current['close']
            sl = max(current['high'], df['high'].iloc[i-1])
            tp = entry - rr * (sl - entry)
            signal = {
                "symbol": SYMBOL,
                "time": current['time'].isoformat(),
                "direction": "SELL",
                "entry": round(entry, 2),
                "sl": round(sl, 2),
                "tp": round(tp, 2),
                "rr_ratio": rr,
                "strategy": "SMC_BOS_FVG"
            }
            logging.info("✅ SELL Signal Detected")
            return signal

        logging.info("❌ No valid signal found")
        return None

def main():
    logging.info("🚀 Starting strategy engine...")

    # Show live price
    try:
        price_url = f"https://api.twelvedata.com/price?symbol=BTC/USD&apikey={TWELVE_API_KEY}"
        price_resp = requests.get(price_url)
        price_resp.raise_for_status()
        price_data = price_resp.json()
        live_price = price_data.get("price")
        if live_price:
            logging.info(f"📈 Live BTC Price: {live_price}")
    except Exception as e:
        logging.warning("⚠️ Could not fetch live BTC price")

    strategy = SMC_BOS_FVG_Strategy()
    signal = strategy.detect_trade_signal()

    if signal:
        try:
            with open("last_signal.json", "w") as f:
                json.dump(signal, f, indent=4)
            logging.info("📩 Signal saved to last_signal.json")

            history_path = "trade_history.json"
            history = []
            if os.path.exists(history_path):
                with open(history_path, "r") as f:
                    try:
                        history = json.load(f)
                    except:
                        logging.warning("⚠️ trade_history.json corrupted or empty")

            history.append(signal)
            with open(history_path, "w") as f:
                json.dump(history, f, indent=4)
            logging.info("📝 Signal stored in trade_history.json")

        except Exception as e:
            logging.error("❌ Failed to save signal")
    else:
        logging.warning("⚠️ No signal generated, strategy AI might be untrained or data not sufficient")

if __name__ == "__main__":
    main()
