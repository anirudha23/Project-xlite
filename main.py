# main.py

import os
import asyncio
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from scheduler import run_scheduler
from bot_client import client

# === Load .env ===
load_dotenv()

# === Flask keep-alive server ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Project X 1 is running with bot token!"

def start_flask():
    app.run(host='0.0.0.0', port=8080)

# === Async scheduler thread ===
def start_scheduler():
    asyncio.run(run_scheduler())

# === Main entry point ===
if __name__ == '__main__':
    Thread(target=start_flask).start()
    Thread(target=start_scheduler).start()

    # Discord bot is already async-aware internally
    client.run(os.getenv("DISCORD_TOKEN"))
