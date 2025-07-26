from flask import Flask
app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8080)


# === scheduler.py ===
from ai_engine import generate_signal
from send_signal import send_to_discord
import json

def run_scheduler():
    signal = generate_signal()
    if signal:
        with open('last_signal.json', 'r') as f:
            last = json.load(f)
        if signal != last:
            send_to_discord(signal)
            with open('last_signal.json', 'w') as f:
                json.dump(signal, f, indent=2)
            with open('trade_history.json', 'a') as f:
                f.write(json.dumps(signal) + "\n")
