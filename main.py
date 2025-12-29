import asyncio
from threading import Thread
from flask import Flask
from scheduler import run_scheduler
from bot_client import client
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Project X 1 Running"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    asyncio.create_task(run_scheduler())
    asyncio.run(client.start(os.getenv("DISCORD_TOKEN")))
