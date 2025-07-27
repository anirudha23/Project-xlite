import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def backtest(data_file='trade_history.json'):
    try:
        df = pd.read_json(data_file)

        if len(df) < 10:
            print("⚠️ Not enough trades to backtest")
            return

        # Calculate profit
        df['profit'] = df.apply(lambda x: x['tp'] - x['entry'] if x['direction'].lower() == 'buy' 
                                else x['entry'] - x['tp'], axis=1)

        print(f"\n🔍 Backtest Results ({len(df)} trades)")
        print(f"✅ Win Rate: {(df['success'].mean()):.2%}")
        print(f"📈 Avg Profit: {df['profit'].mean():.2f} points")

        # Equity curve
        df['cumulative'] = df['profit'].cumsum()
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        df['cumulative'].plot(title="Equity Curve", figsize=(10, 5))
        plt.xlabel("Time")
        plt.ylabel("Cumulative Profit")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig("backtest_results.png")
        print("📊 Saved backtest_results.png")

    except FileNotFoundError:
        print("⚠️ No trade history found - run the bot first or ensure trade_history.json exists")

if __name__ == "__main__":
    backtest()
