import time
import threading
from flask import Flask
from scheduler import run_scheduler

app = Flask(__name__)

@app.route('/')
def home():
    return "Project X (Bollinger Bot) is running!"

def start_scheduler():
    while True:
        run_scheduler()
        time.sleep(300)  # Run every 5 minutes

if __name__ == '__main__':
    threading.Thread(target=start_scheduler).start()
    app.run(host='0.0.0.0', port=8080)
