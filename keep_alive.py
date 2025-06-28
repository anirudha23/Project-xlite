from flask import Flask
from threading import Thread
import logging
import os

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Port configuration
PORT = int(os.environ.get("PORT", 8080))  # Render requires this

@app.route('/')
def home():
    return "✅ Intraday Precision Trader is running"

@app.route('/health')
def health():
    return {"status": "healthy"}, 200

def run():
    app.run(host='0.0.0.0', port=PORT)
    logging.info(f"Server running on port {PORT}")

def keep_alive():
    server = Thread(target=run, daemon=True)
    server.start()
    logging.info("Flask server started")