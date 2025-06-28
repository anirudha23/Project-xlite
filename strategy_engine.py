# ✅ FIXED & OPTIMIZED `strategy_engine.py`

import json
import os
import pandas as pd
from datetime import datetime, timezone
import requests
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from joblib import dump, load
import logging
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SYMBOL = os.getenv('SYMBOL', 'BTC/USD')
TIMEFRAME = os.getenv('TIMEFRAME', '15min')
RISK_REWARD = float(os.getenv('RISK_REWARD', 1.5))
VOLUME_MULTIPLIER = float(os.getenv('VOLUME_MULTIPLIER', 2.0))
TWELVE_DATA_API_KEY = os.getenv('TWELVE_DATA_API_KEY')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('strategy_engine.log'),
        logging.StreamHandler()
    ]
)

# Constants
EMA_PERIOD = 20
MODEL_FILE = "/tmp/trading_model.joblib" if 'RENDER' in os.environ else "trading_model.joblib"
HISTORICAL_DATA_FILE = "historical_data.csv"
API_TIMEOUT = 30

class StrategyEngine:
    def __init__(self):
        self.model = self.load_or_train_model()
        logging.info(f"Initialized StrategyEngine for {SYMBOL} with timeframe {TIMEFRAME}")

    def fetch_candles(self) -> List[Dict]:
        if not TWELVE_DATA_API_KEY:
            logging.error("Twelve Data API key not configured")
            return []

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
                logging.error(f"Unexpected API response: {data.get('message', 'No data')}")
                return []

            candles = [{
                "time": c['datetime'],
                "open": float(c['open']),
                "high": float(c['high']),
                "low": float(c['low']),
                "close": float(c['close']),
                "volume": float(c.get('volume', 1))  # fallback to 1 if missing
            } for c in data['values']]
            return candles

        except Exception as e:
            logging.error(f"Error fetching candles: {str(e)}")
            return []

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time')
            df['ema20'] = df['close'].ewm(span=20).mean()
            df['ema50'] = df['close'].ewm(span=50).mean()
            df['ema100'] = df['close'].ewm(span=100).mean()

            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

            exp12 = df['close'].ewm(span=12).mean()
            exp26 = df['close'].ewm(span=26).mean()
            df['macd'] = exp12 - exp26
            df['signal'] = df['macd'].ewm(span=9).mean()

            df['sma20'] = df['close'].rolling(window=20).mean()
            df['upper_band'] = df['sma20'] + (2 * df['close'].rolling(20).std())
            df['lower_band'] = df['sma20'] - (2 * df['close'].rolling(20).std())

            df['volume_sma20'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma20']

            return df.dropna()
        except Exception as e:
            logging.error(f"Error in indicator calc: {e}")
            return pd.DataFrame()

    def train_model(self) -> Optional[RandomForestClassifier]:
        candles = self.fetch_candles()
        if len(candles) < 100:
            logging.warning("Not enough data to train model")
            return None

        df = pd.DataFrame(candles)
        df = self.calculate_technical_indicators(df)
        if df.empty:
            logging.warning("No clean data after indicators")
            return None

        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        features = ['ema20', 'ema50', 'ema100', 'rsi', 'macd', 'signal', 
                    'upper_band', 'lower_band', 'volume_ratio']
        X = df[features]
        y = df['target']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        dump(model, MODEL_FILE)

        logging.info(f"Model trained with accuracy: {model.score(X_test, y_test):.2f}")
        return model

    def load_or_train_model(self) -> Optional[RandomForestClassifier]:
        if os.path.exists(MODEL_FILE):
            try:
                model = load(MODEL_FILE)
                if isinstance(model, RandomForestClassifier):
                    logging.info("✅ Model loaded from file")
                    return model
            except Exception as e:
                logging.warning(f"Model load failed: {str(e)}")
        return self.train_model()

    def detect_trade_signal(self) -> Optional[Dict]:
        candles = self.fetch_candles()
        if len(candles) < 100:
            logging.warning("Not enough candles for signal detection")
            return None

        df = pd.DataFrame(candles)
        df = self.calculate_technical_indicators(df)
        if df.empty or len(df) < 2:
            logging.warning("Dataframe too small after indicator calc")
            return None

        try:
            last_row = df.iloc[-1]
            last_candle = candles[-1]
            prev_candle = candles[-2]

            avg_volume = sum(c.get("volume", 0) for c in candles[-20:]) / 20
            volume_ok = last_candle.get("volume", 0) > avg_volume * VOLUME_MULTIPLIER

            trend_up = last_candle["close"] > last_row['ema20']
            trend_down = last_candle["close"] < last_row['ema20']

            features = ['ema20', 'ema50', 'ema100', 'rsi', 'macd', 'signal', 
                        'upper_band', 'lower_band', 'volume_ratio']
            X = df[features].iloc[-1:].values
            prediction = self.model.predict_proba(X)[0][1] if self.model else 0.5

            if prediction > 0.65 and trend_up and last_candle["close"] > prev_candle["high"] and volume_ok:
                sl = min(last_candle["low"], prev_candle["low"])
                entry = last_candle["close"]
                tp = entry + (entry - sl) * RISK_REWARD
                return {
                    "direction": "BUY", "entry": round(entry, 2), "sl": round(sl, 2),
                    "tp": round(tp, 2), "time": last_candle["time"],
                    "confidence": round(prediction, 2), "symbol": SYMBOL, "timeframe": TIMEFRAME
                }

            elif prediction < 0.35 and trend_down and last_candle["close"] < prev_candle["low"] and volume_ok:
                sl = max(last_candle["high"], prev_candle["high"])
                entry = last_candle["close"]
                tp = entry - (sl - entry) * RISK_REWARD
                return {
                    "direction": "SELL", "entry": round(entry, 2), "sl": round(sl, 2),
                    "tp": round(tp, 2), "time": last_candle["time"],
                    "confidence": round(1 - prediction, 2), "symbol": SYMBOL, "timeframe": TIMEFRAME
                }

        except Exception as e:
            logging.error(f"Signal detection failed: {str(e)}")
        return None

def main():
    engine = StrategyEngine()
    signal = engine.detect_trade_signal()
    if signal:
        logging.info(f"📈 Signal detected: {signal}")
        try:
            with open("last_signal.json", "w") as f:
                json.dump(signal, f)
        except Exception as e:
            logging.error(f"Error saving signal: {str(e)}")
    else:
        logging.info("No valid setup found.")

if __name__ == "__main__":
    main()
