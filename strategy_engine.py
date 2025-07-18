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
RISK_REWARD = float(os.getenv('RISK_REWARD', 2))
TWELVE_DATA_API_KEY = os.getenv('TWELVE_DATA_API_KEY')

# === Logging setup ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('triple_confluence.log'), logging.StreamHandler()]
)

MODEL_FILE = "/tmp/trading_model.joblib" if 'RENDER' in os.environ else "triple_confluence_model.joblib"
API_TIMEOUT = 30  # seconds

class TripleConfluenceStrategy:
    def __init__(self):
        # Strategy parameters
        self.bb_length = 20
        self.bb_stddev = 2.0
        self.fvg_lookback = 3
        self.swing_lookback = 5
        self.min_candles = 100
        self.model = self.load_or_train_model()
        logging.info(f"Initialized TripleConfluenceStrategy for {SYMBOL} @ {TIMEFRAME}")
        logging.info(f"Risk/Reward: {RISK_REWARD}")

    def fetch_candles(self) -> List[Dict]:
        """Fetch candle data from Twelve Data API"""
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

            candles = [{
                "time": c['datetime'],
                "open": float(c['open']),
                "high": float(c['high']),
                "low": float(c['low']),
                "close": float(c['close']),
                "volume": float(c.get('volume', 1))
            } for c in data['values']]

            logging.info(f"✅ Fetched {len(candles)} candles.")
            return candles
        except Exception as e:
            logging.error(f"Error fetching candles: {str(e)}")
            return []

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all required technical indicators"""
        try:
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time')
            
            # Bollinger Bands
            basis = df['close'].rolling(window=self.bb_length).mean()
            dev = df['close'].rolling(window=self.bb_length).std()
            df['bb_upper'] = basis + self.bb_stddev * dev
            df['bb_lower'] = basis - self.bb_stddev * dev
            df['bb_width'] = df['bb_upper'] - df['bb_lower']
            df['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(20).mean()
            
            # EMA for trend
            df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
            df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
            
            # Swing points
            df['swing_high'] = (df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(-1))
            df['swing_low'] = (df['low'] < df['low'].shift(1)) & (df['low'] < df['low'].shift(-1))
            
            # Fair Value Gap detection
            df['fvg_bullish'] = (df['low'].shift(2) > df['high'].shift(1)) & (df['low'].shift(2) > df['high'])
            df['fvg_bearish'] = (df['high'].shift(2) < df['low'].shift(1)) & (df['high'].shift(2) < df['low'])
            
            # Additional indicators for ML model
            df['rsi'] = self._calculate_rsi(df['close'])
            df['macd'], df['signal'] = self._calculate_macd(df['close'])
            df['volume_sma20'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma20']
            
            return df.dropna()
        except Exception as e:
            logging.error(f"Error in indicator calculation: {str(e)}")
            return df

    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, series: pd.Series) -> tuple:
        exp12 = series.ewm(span=12, adjust=False).mean()
        exp26 = series.ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9, adjust=False).mean()
        return macd, signal

    def train_model(self) -> Optional[RandomForestClassifier]:
        """Train the machine learning model"""
        candles = self.fetch_candles()
        if len(candles) < self.min_candles:
            logging.warning("Not enough candles for training.")
            return None

        try:
            df = pd.DataFrame(candles)
            df = self.calculate_technical_indicators(df)
            if df.empty or len(df) < self.min_candles:
                logging.warning("Not enough clean data.")
                return None

            # Create target - price increase in next 3 candles
            df['target'] = (df['close'].shift(-3) > df['close']).astype(int)
            
            # Features for ML model
            features = ['bb_width', 'bb_squeeze', 'ema_50', 'ema_200', 
                        'rsi', 'macd', 'signal', 'volume_ratio']
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
        """Load existing model or train a new one"""
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

    def detect_bos(self, df: pd.DataFrame, i: int, direction: str) -> bool:
        """Detect Break of Structure"""
        if direction == 'bullish':
            return (df['close'].iloc[i] > df['high'].iloc[i-self.swing_lookback:i].max() and
                    df['close'].iloc[i-1] > df['high'].iloc[i-self.swing_lookback:i-1].max())
        elif direction == 'bearish':
            return (df['close'].iloc[i] < df['low'].iloc[i-self.swing_lookback:i].min() and
                    df['close'].iloc[i-1] < df['low'].iloc[i-self.swing_lookback:i-1].min())
        return False

    def detect_rejection_candle(self, df: pd.DataFrame, i: int, direction: str) -> bool:
        """Detect rejection candle patterns"""
        body = abs(df['close'].iloc[i] - df['open'].iloc[i])
        candle_range = df['high'].iloc[i] - df['low'].iloc[i]
        
        if candle_range == 0:
            return False
            
        if direction == 'bullish':
            prev_candle_bearish = df['close'].iloc[i-1] < df['open'].iloc[i-1]
            engulfing = (df['close'].iloc[i] > df['open'].iloc[i-1] and 
                        df['open'].iloc[i] < df['close'].iloc[i-1])
            return prev_candle_bearish and engulfing and (body/candle_range > 0.5)
        
        elif direction == 'bearish':
            prev_candle_bullish = df['close'].iloc[i-1] > df['open'].iloc[i-1]
            engulfing = (df['close'].iloc[i] < df['open'].iloc[i-1] and 
                        df['open'].iloc[i] > df['close'].iloc[i-1])
            return prev_candle_bullish and engulfing and (body/candle_range > 0.5)
        
        return False

    def detect_liquidity_sweep(self, df: pd.DataFrame, i: int) -> tuple:
        """Detect liquidity sweep pattern"""
        swing_high = df['swing_high'].iloc[i-self.swing_lookback]
        swing_low = df['swing_low'].iloc[i-self.swing_lookback]
        
        sweep_high = (swing_high and 
                     df['high'].iloc[i] > df['high'].iloc[i-self.swing_lookback] and
                     df['close'].iloc[i] < df['high'].iloc[i-self.swing_lookback])
        
        sweep_low = (swing_low and
                    df['low'].iloc[i] < df['low'].iloc[i-self.swing_lookback] and
                    df['close'].iloc[i] > df['low'].iloc[i-self.swing_lookback])
        
        return sweep_high, sweep_low

    def detect_trend(self, df: pd.DataFrame, i: int) -> str:
        """Determine market trend"""
        return 'bullish' if df['ema_50'].iloc[i] > df['ema_200'].iloc[i] else 'bearish'

    def detect_trade_signal(self) -> Optional[Dict]:
        """Main method to generate trading signals"""
        candles = self.fetch_candles()
        if len(candles) < self.min_candles:
            logging.warning(f"⛔ Not enough data (need at least {self.min_candles} candles)")
            return None
            
        df = pd.DataFrame(candles)
        df = self.calculate_technical_indicators(df)
        
        if len(df) < self.min_candles:
            logging.warning("⛔ Not enough data after indicator calculation")
            return None
            
        # Get ML model prediction
        features = ['bb_width', 'bb_squeeze', 'ema_50', 'ema_200', 
                   'rsi', 'macd', 'signal', 'volume_ratio']
        X = df[features].iloc[-1:].values
        prediction = self.model.predict_proba(X)[0][1] if self.model else 0.5
        
        # Check last candle for signals
        i = len(df) - 1
        current = df.iloc[i]
        trend = self.detect_trend(df, i)
        sweep_high, sweep_low = self.detect_liquidity_sweep(df, i)
        squeeze = df['bb_squeeze'].iloc[i]
        breakout = (current['close'] > current['bb_upper'] or 
                    current['close'] < current['bb_lower'])
        
        # Check for long setup
        if (trend == 'bullish' and
            any(df['fvg_bullish'].iloc[i-self.fvg_lookback:i]) and
            sweep_low and
            squeeze and
            breakout and
            prediction >= 0.65):
            
            if (self.detect_bos(df, i, 'bullish') and 
                self.detect_rejection_candle(df, i, 'bullish')):
                
                entry = current['close']
                sl = min(current['low'], df['low'].iloc[i-1])
                tp = entry + RISK_REWARD * (entry - sl)
                
                signal = {
                    "direction": "BUY",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "time": current['time'].isoformat(),
                    "confidence": round(prediction, 2),
                    "symbol": SYMBOL,
                    "timeframe": TIMEFRAME,
                    "strategy": "TripleConfluence",
                    "reason": "BOS + FVG + Liquidity Sweep + BB Squeeze"
                }
                logging.info("✅ BUY Signal Detected")
                return signal
        
        # Check for short setup
        elif (trend == 'bearish' and
              any(df['fvg_bearish'].iloc[i-self.fvg_lookback:i]) and
              sweep_high and
              squeeze and
              breakout and
              prediction <= 0.35):
            
            if (self.detect_bos(df, i, 'bearish') and 
                self.detect_rejection_candle(df, i, 'bearish')):
                
                entry = current['close']
                sl = max(current['high'], df['high'].iloc[i-1])
                tp = entry - RISK_REWARD * (sl - entry)
                
                signal = {
                    "direction": "SELL",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "time": current['time'].isoformat(),
                    "confidence": round(1 - prediction, 2),
                    "symbol": SYMBOL,
                    "timeframe": TIMEFRAME,
                    "strategy": "TripleConfluence",
                    "reason": "BOS + FVG + Liquidity Sweep + BB Squeeze"
                }
                logging.info("✅ SELL Signal Detected")
                return signal
        
        logging.info("❌ No trade signal found.")
        return None

def main():
    strategy = TripleConfluenceStrategy()
    signal = strategy.detect_trade_signal()

    if signal:
        logging.info(f"📤 Signal: {json.dumps(signal, indent=2)}")
        try:
            with open("last_signal.json", "w") as f:
                json.dump(signal, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving signal: {str(e)}")
    else:
        logging.info("🔍 No valid signal this cycle.")

if __name__ == "__main__":
    main()