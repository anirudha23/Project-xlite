import json
from datetime import datetime

OLD_FILE = "trade_history.json"
NEW_FILE = "trade_history_new.json"

RR_RATIO = 2  # 1:2 risk reward

with open(OLD_FILE) as f:
    old_trades = json.load(f)

new_trades = []

for i, t in enumerate(old_trades, start=1):
    risk = abs(t["entry"] - t["sl"])
    reward = risk * RR_RATIO

    is_tp = t["outcome"] == "hit_tp"

    exit_price = t["tp"] if is_tp else t["sl"]
    pnl = reward if is_tp else -risk

    new_trades.append({
        "trade_id": f"BTCUSD-{t['timestamp'].replace(':','').replace('-','')}-{i:03}",
        "symbol": "BTC/USD",
        "timeframe": "15m",

        "direction": t["direction"],

        "entry_price": t["entry"],
        "stop_loss": t["sl"],
        "take_profit": t["tp"],
        "exit_price": exit_price,

        "risk": round(risk, 2),
        "reward": round(reward, 2),
        "pnl": round(pnl, 2),

        "result": "TP" if is_tp else "SL",

        "entry_time": t["timestamp"],
        "exit_time": t["timestamp"],

        "strategy": "bollinger_breakout"
    })

with open(NEW_FILE, "w") as f:
    json.dump(new_trades, f, indent=2)

print("✅ Migration complete → trade_history_new.json created")
