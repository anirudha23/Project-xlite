import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from joblib import dump
import os
from dotenv import load_dotenv

def evaluate_and_retrain():
    try:
        # Load environment variables
        load_dotenv()
        SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')  # Default to BTCUSDT
        
        print(f"🔍 Evaluating trades for {SYMBOL}")
        
        df = pd.read_csv("historical_data.csv")
        if len(df) < 50:
            print("⚠️ Not enough trade data for evaluation")
            return
        
        # Calculate success rate
        success_rate = df['success'].mean()
        print(f"📊 Historical success rate: {success_rate:.2%}")
        
        # Analyze best performing conditions
        best_buy = df[df['direction'] == 'BUY']['success'].mean()
        best_sell = df[df['direction'] == 'SELL']['success'].mean()
        print(f"📈 Buy success: {best_buy:.2%}, Sell success: {best_sell:.2%}")
        
        # Retrain model with new data
        from strategy_engine import train_model
        train_model()
        
    except FileNotFoundError:
        print("⚠️ No historical data found for evaluation")

if __name__ == "__main__":
    evaluate_and_retrain()