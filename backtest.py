import pandas as pd

df = pd.read_json("trade_history.json")

print("Trades:", len(df))
print("Win rate:", (df["result"] == "TP").mean() * 100)
print("Total PnL:", round(df["pnl"].sum(), 2))
