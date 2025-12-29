import pandas as pd

df = pd.read_json("trade_history.json")

print("Total trades:", len(df))
print("Win rate:", (df["result"] == "TP").mean() * 100, "%")
print("Total PnL:", df["pnl"].sum())
