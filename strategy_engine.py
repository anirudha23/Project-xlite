import json
import os
import pandas as pd
from datetime import datetime
import requests
import logging
from typing import Optional, Dict, List
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
SYMBOL = os.getenv('SYMBOL', 'BTC/USD')
TIMEFRAME = os.getenv('TIMEFRAME', '15min')
RISK_REWARD = float(os.getenv('RISK_REWARD', 3))
TWELVE_DATA_API_KEY = os.getenv('TWELVE_DATA_API_KEY')

# === Logging setup ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('smc_bos_fvg.log'), logging.StreamHandler()]
)

API_TIMEOUT = 30  # seconds

class SMC_BOS_FVG_Strategy:
    def __init__(self):
        self.fvg_lookback = 3
        self.swing_lookback = 5
        self.min_candles = 100
        logging.info(f"✅ Strategy Initialized: SMC_BOS_FVG | Symbol: {SYMBOL} | TF: {TIMEFRAME}")

    def fetch_candles(self) -> List[Dict]:
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": SYMBOL,
            "interval": TIMEFRAME,
            "outputsize": 500,
            "apikey": TWELVE_DATA_API_KEY
        }

        try:
            response = requests.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if 'values' not in data:
                logging.error(f"API Error: {data.get('message', 'No data returned')}")
                return []

            candles = [  # Reformat into OHLCV list
                {
                    "time": c['datetime'],
                    "open": float(c['open']),
                    "high": float(c['high']),
                    "low": float(c['low']),
                    "close": float(c['close']),
                    "volume": float(c.get('volume', 1))
                }
                for c in data['values']
            ]

            logging.info(f"✅ Fetched {len(candles)} candles.")
            return candles
        except Exception as e:
            logging.error(f"❌ Error fetching candles: {str(e)}")
            return []

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time')

        # Trend EMAs
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # Swing detection
        df['swing_high'] = (df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(-1))
        df['swing_low'] = (df['low'] < df['low'].shift(1)) & (df['low'] < df['low'].shift(-1))

        # Fair Value Gaps
        df['fvg_bullish'] = (df['low'].shift(2) > df['high'].shift(1)) & (df['low'].shift(2) > df['high'])
        df['fvg_bearish'] = (df['high'].shift(2) < df['low'].shift(1)) & (df['high'].shift(2) < df['low'])

        return df.dropna()

    def detect_trend(self, df: pd.DataFrame, i: int) -> str:
        return 'bullish' if df['ema_50'].iloc[i] > df['ema_200'].iloc[i] else 'bearish'

    def detect_bos(self, df: pd.DataFrame, i: int, direction: str) -> bool:
        if direction == 'bullish':
            return df['close'].iloc[i] > df['high'].iloc[i - self.swing_lookback:i].max()
        elif direction == 'bearish':
            return df['close'].iloc[i] < df['low'].iloc[i - self.swing_lookback:i].min()
        return False

    def detect_rejection_candle(self, df: pd.DataFrame, i: int, direction: str) -> bool:
        if i < 1:
            return False

        body = abs(df['close'].iloc[i] - df['open'].iloc[i])
        candle_range = df['high'].iloc[i] - df['low'].iloc[i]
        if candle_range == 0:
            return False

        if direction == 'bullish':
            prev_bearish = df['close'].iloc[i-1] < df['open'].iloc[i-1]
            engulfing = (
                df['close'].iloc[i] > df['open'].iloc[i-1] and
                df['open'].iloc[i] < df['close'].iloc[i-1]
            )
            return prev_bearish and engulfing and (body / candle_range > 0.5)

        elif direction == 'bearish':
            prev_bullish = df['close'].iloc[i-1] > df['open'].iloc[i-1]
            engulfing = (
                df['close'].iloc[i] < df['open'].iloc[i-1] and
                df['open'].iloc[i] > df['close'].iloc[i-1]
            )
            return prev_bullish and engulfing and (body / candle_range > 0.5)

        return False

    def detect_trade_signal(self) -> Optional[Dict]:
        candles = self.fetch_candles()
        if len(candles) < self.min_candles:
            logging.warning("⛔ Not enough candles to evaluate.")
            return None

        df = pd.DataFrame(candles)
        df = self.calculate_indicators(df)
        if len(df) < self.min_candles:
            logging.warning("⛔ Not enough data after indicators.")
            return None

        i = len(df) - 1
        current = df.iloc[i]
        trend = self.detect_trend(df, i)

        if (trend == 'bullish' and
            any(df['fvg_bullish'].iloc[i - self.fvg_lookback:i]) and
            self.detect_bos(df, i, 'bullish') and
            self.detect_rejection_candle(df, i, 'bullish')):

            entry = current['close']
            sl = min(current['low'], df['low'].iloc[i - 1])
            tp = entry + RISK_REWARD * (entry - sl)

            signal = {
                "direction": "BUY",
                "entry": round(entry, 2),
                "sl": round(sl, 2),
                "tp": round(tp, 2),
                "time": current['time'].isoformat(),
                "symbol": SYMBOL,
                "timeframe": TIMEFRAME,
                "strategy": "SMC_BOS_FVG",
                "reason": "SMC BOS + Bullish FVG + Rejection Candle"
            }
            logging.info("✅ BUY Signal Detected")
            return signal

        elif (trend == 'bearish' and
              any(df['fvg_bearish'].iloc[i - self.fvg_lookback:i]) and
              self.detect_bos(df, i, 'bearish') and
              self.detect_rejection_candle(df, i, 'bearish')):

            entry = current['close']
            sl = max(current['high'], df['high'].iloc[i - 1])
            tp = entry - RISK_REWARD * (sl - entry)

            signal = {
                "direction": "SELL",
                "entry": round(entry, 2),
                "sl": round(sl, 2),
                "tp": round(tp, 2),
                "time": current['time'].isoformat(),
                "symbol": SYMBOL,
                "timeframe": TIMEFRAME,
                "strategy": "SMC_BOS_FVG",
                "reason": "SMC BOS + Bearish FVG + Rejection Candle"
            }
            logging.info("✅ SELL Signal Detected")
            return signal

        logging.info("❌ No trade signal found.")
        return None

def main():
    strategy = SMC_BOS_FVG_Strategy()
    signal = strategy.detect_trade_signal()

    if signal:
        logging.info(f"📤 Final Signal:\n{json.dumps(signal, indent=2)}")
        try:
            with open("last_signal.json", "w") as f:
                json.dump(signal, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving signal: {str(e)}")
    else:
        logging.info("🔍 No valid signal this cycle.")

if __name__ == "__main__":
    main()
