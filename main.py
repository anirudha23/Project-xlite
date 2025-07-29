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

# === Combined async runner for scheduler and bot ===
async def main_async():
    print("⏳ Starting async scheduler...")
    asyncio.create_task(run_scheduler())  # ✅ Proper async task
    print("📅 Scheduler started. Running at every 15-minute mark...")
    print("🤖 Starting Discord bot...")
    await client.start(os.getenv("DISCORD_TOKEN"))

# === Entry point ===
if __name__ == '__main__':
    print("🌐 Starting Flask keep-alive server on port 8080...")
    Thread(target=start_flask, daemon=True).start()
    asyncio.run(main_async())
