import os
import gspread
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

gc = gspread.service_account(filename="google_credentials.json")
sheet = gc.open_by_key(SHEET_ID).sheet1

def log_trade(symbol, side, qty, action, indicators):
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    row = [
        now,
        symbol,
        side,
        qty,
        action,
        indicators.get('ema9', ''),
        indicators.get('ema21', ''),
        indicators.get('rsi', ''),
        indicators.get('macd', ''),
        indicators.get('volume', ''),
        indicators.get('trend', '')
    ]
    try:
        sheet.append_row(row)
    except Exception as e:
        print(f"Google Sheet error: {e}")