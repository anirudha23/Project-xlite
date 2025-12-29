import os
import asyncio
from threading import Thread
from flask import Flask
from dotenv import load_dotenv

from scheduler import run_scheduler
from bot_client import client

load_dotenv()

# ---------------- Flask Keep Alive ---------------- #

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Project X running on Render"

def start_flask():
    app.run(host="0.0.0.0", port=8080)

# ---------------- Async Main ---------------- #

async def async_main():
    print("⏳ Starting scheduler...")
    asyncio.create_task(run_scheduler())

    print("🤖 Starting Discord bot...")
    await client.start(os.getenv("DISCORD_TOKEN"))

# ---------------- Entry Point ---------------- #

if __name__ == "__main__":
    print("🌐 Starting Flask keep-alive server...")
    Thread(target=start_flask, daemon=True).start()

    print("⚙️ Starting async event loop...")
    asyncio.run(async_main())
