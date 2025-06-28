import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def backtest(data_file='historical_data.csv'):
    try:
        df = pd.read_csv(data_file)
        if len(df) < 10:
            print("⚠️ Not enough trades to backtest")
            return
            
        df['profit'] = df.apply(lambda x: x['tp'] - x['entry'] if x['direction'] == 'BUY' 
                               else x['entry'] - x['tp'], axis=1)
        
        print(f"🔍 Backtest Results ({len(df)} trades)")
        print(f"✅ Win Rate: {(df['success'].mean()):.2%}")
        print(f"📈 Avg Profit: {df['profit'].mean():.2f} points")
        
        # Plot equity curve
        df['cumulative'] = df['profit'].cumsum()
        df.plot(x='time', y='cumulative')
        plt.savefig('backtest_results.png')
        print("📊 Saved backtest_results.png")
        
    except FileNotFoundError:
        print("⚠️ No trade history found - run the bot first")

if __name__ == "__main__":
    backtest()