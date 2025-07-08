import schedule, time
from dotenv import load_dotenv
from telegram import send_telegram, handle_commands
from mexc import check_and_trade_all_symbols
import threading

load_dotenv()

def run_bot():
    check_and_trade_all_symbols()

# Schedule to run every minute
schedule.every(1).minutes.do(run_bot)

# Background command listener
threading.Thread(target=handle_commands, daemon=True).start()

send_telegram("🚀 Bot started on Google Cloud.")
while True:
    schedule.run_pending()
    time.sleep(1)
