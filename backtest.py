import pandas as pd

df = pd.read_json("trade_history.json")

print("Trades:", len(df))
print("Win rate:", (df["result"] == "TP").mean())
print("Total PnL:", df["pnl"].sum())
print("Average PnL:", df["pnl"].mean())
