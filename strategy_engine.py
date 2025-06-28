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
SYMBOL = os.getenv('SYMBOL', 'BTC/USD')  # Twelve Data format
TIMEFRAME = os.getenv('TIMEFRAME', '15min')  # Twelve Data format
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
MODEL_FILE = "trading_model.joblib"
HISTORICAL_DATA_FILE = "historical_data.csv"
API_TIMEOUT = 30  # seconds

class StrategyEngine:
    def __init__(self):
        self.model = self.load_or_train_model()
        logging.info(f"Initialized StrategyEngine for {SYMBOL} with timeframe {TIMEFRAME}")
        logging.info(f"Risk reward ratio: {RISK_REWARD}, Volume multiplier: {VOLUME_MULTIPLIER}")
        
    def fetch_candles(self) -> List[Dict]:
        """Fetch candle data from Twelve Data API"""
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
                
            candles = []
            for candle in data['values']:
                candles.append({
                    "time": candle['datetime'],
                    "open": float(candle['open']),
                    "high": float(candle['high']),
                    "low": float(candle['low']),
                    "close": float(candle['close']),
                    "volume": float(candle.get('volume', 0))  # Some endpoints might not have volume
                })
            return candles
            
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error fetching candles: {str(e)}")
            return []

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate various technical indicators"""
        try:
            # Convert time to datetime and sort
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time')
            
            # Moving Averages
            df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
            df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
            df['ema100'] = df['close'].ewm(span=100, adjust=False).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp12 = df['close'].ewm(span=12, adjust=False).mean()
            exp26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = exp12 - exp26
            df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            
            # Bollinger Bands
            df['sma20'] = df['close'].rolling(window=20).mean()
            df['upper_band'] = df['sma20'] + (2 * df['close'].rolling(window=20).std())
            df['lower_band'] = df['sma20'] - (2 * df['close'].rolling(window=20).std())
            
            # Volume features
            if 'volume' in df.columns:
                df['volume_sma20'] = df['volume'].rolling(window=20).mean()
                df['volume_ratio'] = df['volume'] / df['volume_sma20']
            else:
                df['volume_ratio'] = 1.0  # Default if no volume data
                
            return df.dropna()
        except Exception as e:
            logging.error(f"Error calculating indicators: {str(e)}")
            return df

    def train_model(self) -> Optional[RandomForestClassifier]:
        """Train and save a new model"""
        candles = self.fetch_candles()
        if len(candles) < 100:
            logging.warning("Not enough data for training")
            return None
            
        try:
            df = pd.DataFrame(candles)
            df = self.calculate_technical_indicators(df)
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
        except Exception as e:
            logging.error(f"Model training failed: {str(e)}")
            return None

    def load_or_train_model(self) -> Optional[RandomForestClassifier]:
        """Load existing model or train a new one"""
        if os.path.exists(MODEL_FILE):
            try:
                model = load(MODEL_FILE)
                if isinstance(model, RandomForestClassifier):
                    logging.info("Loaded existing model")
                    return model
                raise ValueError("Invalid model type")
            except Exception as e:
                logging.warning(f"Model load failed: {str(e)}. Retraining...")
                return self.train_model()
        else:
            logging.info("No model found, training new model")
            return self.train_model()

    def detect_trade_signal(self) -> Optional[Dict]:
        """Detect trading signals using combined rule-based and AI approach"""
        candles = self.fetch_candles()
        if len(candles) < 100:
            logging.warning("Not enough data for signal detection")
            return None
            
        try:
            df = pd.DataFrame(candles)
            df = self.calculate_technical_indicators(df)
            last_row = df.iloc[-1]
            last_candle = candles[-1]
            prev_candle = candles[-2]
            
            # Volume condition
            avg_volume = sum(c.get("volume", 0) for c in candles[-20:]) / 20
            volume_ok = last_candle.get("volume", 0) > avg_volume * VOLUME_MULTIPLIER
            
            # Trend conditions
            ema20 = last_row['ema20']
            trend_up = last_candle["close"] > ema20
            trend_down = last_candle["close"] < ema20
            
            # AI prediction
            features = ['ema20', 'ema50', 'ema100', 'rsi', 'macd', 'signal', 
                       'upper_band', 'lower_band', 'volume_ratio']
            X = df[features].iloc[-1:].values
            prediction = self.model.predict_proba(X)[0][1]
            
            # Generate signals
            if (prediction > 0.65 and trend_up and 
                last_candle["close"] > prev_candle["high"] and 
                volume_ok):
                
                sl = min(last_candle["low"], prev_candle["low"])
                entry = last_candle["close"]
                tp = entry + (entry - sl) * RISK_REWARD
                
                return {
                    "direction": "BUY",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "time": last_candle["time"],
                    "confidence": round(prediction, 2),
                    "symbol": SYMBOL,
                    "timeframe": TIMEFRAME
                }
                
            elif (prediction < 0.35 and trend_down and 
                  last_candle["close"] < prev_candle["low"] and 
                  volume_ok):
                
                sl = max(last_candle["high"], prev_candle["high"])
                entry = last_candle["close"]
                tp = entry - (sl - entry) * RISK_REWARD
                
                return {
                    "direction": "SELL",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "time": last_candle["time"],
                    "confidence": round(1 - prediction, 2),
                    "symbol": SYMBOL,
                    "timeframe": TIMEFRAME
                }
                
            return None
        except Exception as e:
            logging.error(f"Signal detection failed: {str(e)}")
            return None

def main():
    engine = StrategyEngine()
    signal = engine.detect_trade_signal()
    
    if signal:
        logging.info(f"Signal detected (Confidence: {signal['confidence']}): {signal}")
        try:
            with open("last_signal.json", "w") as f:
                json.dump(signal, f)
        except Exception as e:
            logging.error(f"Failed to save signal: {str(e)}")
    else:
        logging.info("No valid setup found")

if __name__ == "__main__":
    main()