import json
import os
import pandas as pd
from datetime import datetime
import requests
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from joblib import dump, load
import logging
from typing import Optional, Dict, List
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
SYMBOL = os.getenv('SYMBOL', 'BTC/USD')
TIMEFRAME = os.getenv('TIMEFRAME', '15min')
RISK_REWARD = float(os.getenv('RISK_REWARD', 1.5))
TWELVE_DATA_API_KEY = os.getenv('TWELVE_DATA_API_KEY')

# === Logging setup ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('strategy_engine.log'), logging.StreamHandler()]
)

MODEL_FILE = "/tmp/trading_model.joblib" if 'RENDER' in os.environ else "trading_model.joblib"
API_TIMEOUT = 30  # seconds

class StrategyEngine:
    def __init__(self):
        self.model = self.load_or_train_model()
        logging.info(f"Initialized StrategyEngine for {SYMBOL} @ {TIMEFRAME}")
        logging.info(f"Risk/Reward: {RISK_REWARD}")

    def fetch_candles(self) -> List[Dict]:
        if not TWELVE_DATA_API_KEY:
            logging.error("Twelve Data API key is missing.")
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
                logging.error(f"Unexpected API response: {data.get('message', 'No values returned')}")
                return []

            logging.info(f"📦 First Candle (raw): {data['values'][0]}")

            candles = [{
                "time": c['datetime'],
                "open": float(c['open']),
                "high": float(c['high']),
                "low": float(c['low']),
                "close": float(c['close']),
                "volume": float(c['volume']) if 'volume' in c and c['volume'] not in [None, '', 'null'] else 0.0
            } for c in data['values']]

            logging.info(f"✅ Fetched {len(candles)} candles.")
            return candles
        except Exception as e:
            logging.error(f"Error fetching candles: {str(e)}")
            return []

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time')

            df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
            df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
            df['ema100'] = df['close'].ewm(span=100, adjust=False).mean()

            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

            exp12 = df['close'].ewm(span=12, adjust=False).mean()
            exp26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = exp12 - exp26
            df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()

            df['sma20'] = df['close'].rolling(window=20).mean()
            df['upper_band'] = df['sma20'] + (2 * df['close'].rolling(window=20).std())
            df['lower_band'] = df['sma20'] - (2 * df['close'].rolling(window=20).std())

            df['volume_sma20'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma20']

            return df.dropna()
        except Exception as e:
            logging.error(f"Error in indicator calculation: {str(e)}")
            return df

    def train_model(self) -> Optional[RandomForestClassifier]:
        candles = self.fetch_candles()
        if len(candles) < 70:
            logging.warning("Not enough candles for training.")
            return None

        try:
            df = pd.DataFrame(candles)
            df = self.calculate_technical_indicators(df)
            if df.empty or len(df) < 70:
                logging.warning("Not enough clean data.")
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
            logging.info(f"🎯 Model trained. Accuracy: {model.score(X_test, y_test):.2f}")
            return model
        except Exception as e:
            logging.error(f"Training failed: {str(e)}")
            return None

    def load_or_train_model(self) -> Optional[RandomForestClassifier]:
        if os.path.exists(MODEL_FILE):
            try:
                model = load(MODEL_FILE)
                logging.info("✅ Model loaded from file.")
                return model
            except Exception as e:
                logging.warning(f"Model load failed: {str(e)}. Re-training...")
                return self.train_model()
        else:
            logging.info("🧠 No model found. Training new model...")
            return self.train_model()

    def detect_trade_signal(self) -> Optional[Dict]:
        candles = self.fetch_candles()
        if len(candles) < 70:
            logging.warning("⛔ Not enough candles for signal (need at least 70).")
            return None

        try:
            df = pd.DataFrame(candles)
            df = self.calculate_technical_indicators(df)
            if len(df) < 70:
                logging.warning("⛔ Not enough rows after indicators.")
                return None

            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]

            trend_up = last_row['close'] > last_row['ema20']
            trend_down = last_row['close'] < last_row['ema20']

            features = ['ema20', 'ema50', 'ema100', 'rsi', 'macd', 'signal',
                        'upper_band', 'lower_band', 'volume_ratio']
            X = df[features].iloc[-1:]
            prediction = self.model.predict_proba(X)[0][1] if self.model else 0.5

            if trend_up:
                logging.info(f"[DEBUG] Prediction: {prediction:.2f}, Trend: UP, Close > Prev High: {last_row['close'] > prev_row['high']}")
            elif trend_down:
                logging.info(f"[DEBUG] Prediction: {prediction:.2f}, Trend: DOWN, Close < Prev Low: {last_row['close'] < prev_row['low']}")
            else:
                logging.info(f"[DEBUG] Prediction: {prediction:.2f}, Trend: FLAT")

            if prediction >= 0.65 and trend_up and last_row['close'] > prev_row['high']:
                entry = last_row['close']
                sl = min(last_row['low'], prev_row['low'])
                tp = entry + (entry - sl) * RISK_REWARD

                signal = {
                    "direction": "BUY",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "time": last_row['time'].isoformat(),
                    "confidence": round(prediction, 2),
                    "symbol": SYMBOL,
                    "timeframe": TIMEFRAME
                }
                logging.info("✅ BUY Signal Detected")
                return signal

            elif prediction <= 0.35 and trend_down and last_row['close'] < prev_row['low']:
                entry = last_row['close']
                sl = max(last_row['high'], prev_row['high'])
                tp = entry - (sl - entry) * RISK_REWARD

                signal = {
                    "direction": "SELL",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "time": last_row['time'].isoformat(),
                    "confidence": round(1 - prediction, 2),
                    "symbol": SYMBOL,
                    "timeframe": TIMEFRAME
                }
                logging.info("✅ SELL Signal Detected")
                return signal

            logging.info("❌ No trade signal found.")
            return None
        except Exception as e:
            logging.error(f"Error detecting signal: {str(e)}")
            return None

def main():
    engine = StrategyEngine()
    signal = engine.detect_trade_signal()

    if signal:
        logging.info(f"📤 Signal: {json.dumps(signal, indent=2)}")
        try:
            with open("last_signal.json", "w") as f:
                json.dump(signal, f)
        except Exception as e:
            logging.error(f"Error saving signal: {str(e)}")
    else:
        logging.info("🔍 No valid signal this cycle.")

if __name__ == "__main__":
    main()
