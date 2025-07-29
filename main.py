# main.py

import os
import asyncio
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from scheduler import run_scheduler
from bot_client import client

# === Load environment variables ===
load_dotenv()

# === Flask keep-alive server ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Project X 1 is running with bot token!"

def start_flask():
    print("🌐 Starting Flask keep-alive server on port 8080...")
    app.run(host='0.0.0.0', port=8080)

def start_scheduler():
    print("⏳ Starting async scheduler...")
    asyncio.run(run_scheduler())

# === Main entry point ===
if __name__ == '__main__':
    # Start Flask and Scheduler in separate threads
    flask_thread = Thread(target=start_flask)
    scheduler_thread = Thread(target=start_scheduler)

    flask_thread.start()
    scheduler_thread.start()

    # Start Discord bot (async internally)
    print("🤖 Starting Discord bot...")
    client.run(os.getenv("DISCORD_TOKEN"))
