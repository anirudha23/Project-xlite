import pandas as pd

def evaluate_bollinger_trade(df: pd.DataFrame) -> dict:
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['STD20'] = df['close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + 2 * df['STD20']
    df['Lower'] = df['MA20'] - 2 * df['STD20']

    last = df.iloc[-1]
    previous = df.iloc[-2]

    signal = None
    if previous['close'] < previous['Lower'] and last['close'] > last['Lower']:
        signal = "buy"
    elif previous['close'] > previous['Upper'] and last['close'] < last['Upper']:
        signal = "sell"
    else:
        signal = "sideways"

    sl = round(last['close'] * (0.98 if signal == "buy" else 1.02), 2)
    tp = round(last['close'] * (1.02 if signal == "buy" else 0.98), 2)

    return {
        "signal": signal,
        "entry": round(last['close'], 2),
        "sl": sl,
        "tp": tp
    }
