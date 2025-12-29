import os
import asyncio
from threading import Thread
from flask import Flask
from dotenv import load_dotenv

from scheduler import run_scheduler
from bot_client import client

load_dotenv()

app = Flask(__name__)

@app.route("/")
def home():
    return "Project X running"

def start_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

async def async_main():
    asyncio.create_task(run_scheduler())
    await client.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    Thread(target=start_flask, daemon=True).start()
    asyncio.run(async_main())
