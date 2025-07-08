import os, json
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BOT_STATE_FILE = "bot_state.json"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': msg}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

def load_state():
    if not os.path.exists(BOT_STATE_FILE):
        save_state(True)
    with open(BOT_STATE_FILE, 'r') as f:
        return json.load(f)['running']

def save_state(running):
    with open(BOT_STATE_FILE, 'w') as f:
        json.dump({'running': running}, f)

def handle_commands():
    pass  # Stub for webhook or polling (optional)