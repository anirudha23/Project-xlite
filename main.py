# main.py

import os
from flask import Flask
from threading import Thread
from scheduler import run_scheduler
from bot_client import client
from dotenv import load_dotenv

# === Load .env ===
load_dotenv()

# === Flask keep-alive app ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Project X 1 is running with bot token!"

def start_flask():
    app.run(host='0.0.0.0', port=8080)

# === Start scheduler in background ===
def start_scheduler():
    run_scheduler()

# === Start both scheduler and Flask ===
if __name__ == '__main__':
    Thread(target=start_flask).start()
    Thread(target=start_scheduler).start()
    # Run Discord bot
    client.run(os.getenv("DISCORD_TOKEN"))
