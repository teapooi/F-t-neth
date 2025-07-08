import requests, time, hmac, hashlib, os, json
from dotenv import load_dotenv
from strategy import evaluate_signal
from telegram import send_telegram
from google_sheets import log_trade

load_dotenv()
BASE_URL = 'https://fapi.binance.com'

API_KEY = os.getenv("BINANCE_API_KEY")
SECRET = os.getenv("BINANCE_API_SECRET")

with open('config.json') as f:
    CONFIG = json.load(f)

def signed_request(method, path, params=None):
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    headers = {'X-MBX-APIKEY': API_KEY}
    url = f"{BASE_URL}{path}?{query}&signature={signature}"
    if method == 'GET':
        return requests.get(url, headers=headers).json()
    elif method == 'POST':
        return requests.post(url, headers=headers).json()
    elif method == 'DELETE':
        return requests.delete(url, headers=headers).json()

def get_candles(symbol, interval='1m', limit=50):
    url = f"{BASE_URL}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    prices = [float(k[4]) for k in data]
    volumes = [float(k[5]) for k in data]
    return prices, volumes

def get_balance():
    res = signed_request('GET', '/fapi/v2/balance')
    usdt_bal = next((float(b['balance']) for b in res if b['asset'] == 'USDT'), 0)
    return usdt_bal

def get_position(symbol):
    res = signed_request('GET', '/fapi/v2/positionRisk')
    for p in res:
        if p['symbol'] == symbol:
            amt = float(p['positionAmt'])
            price = float(p['entryPrice'])
            return amt, price
    return 0, 0

def set_leverage(symbol, lev):
    signed_request('POST', '/fapi/v1/leverage', {'symbol': symbol, 'leverage': lev})

def place_order(symbol, side, quantity):
    params = {
        'symbol': symbol,
        'side': side,
        'type': 'MARKET',
        'quantity': quantity
    }
    return signed_request('POST', '/fapi/v1/order', params)

def close_position(symbol, amt):
    side = 'SELL' if amt > 0 else 'BUY'
    place_order(symbol, side, abs(amt))
    send_telegram(f"🔴 Closed position on {symbol}: {side} {abs(amt)}")
    log_trade(symbol, side, abs(amt), "CLOSE", {})

def check_and_trade(symbol):
    try:
        prices, volumes = get_candles(symbol, CONFIG["timeframe"])
        score, direction, debug = evaluate_signal(prices, volumes)
        amt, entry = get_position(symbol)
        price_now = prices[-1]

        if amt != 0:
            entry = float(entry)
            change_pct = ((price_now - entry) / entry) * 100
            if amt < 0: change_pct *= -1

            if change_pct >= CONFIG['take_profit_pct']:
                close_position(symbol, amt)
                send_telegram(f"✅ TP hit on {symbol} ({change_pct:.2f}%)")
            elif change_pct <= -CONFIG['stop_loss_pct']:
                close_position(symbol, amt)
                send_telegram(f"🛑 SL hit on {symbol} ({change_pct:.2f}%)")
            return

        if score >= CONFIG["min_confidence_score"] and direction != "HOLD":
            usdt = get_balance()
            risk_amount = usdt * CONFIG["risk_per_trade"]
            qty = round((risk_amount * CONFIG["leverage"]) / price_now, 3)
            side = "BUY" if direction == "LONG" else "SELL"
            set_leverage(symbol, CONFIG["leverage"])
            place_order(symbol, side, qty)
            send_telegram(f"🚀 {direction} {symbol} | Score: {score:.2f} | Qty: {qty}")
            log_trade(symbol, side, qty, "OPEN", debug)
    except Exception as e:
        send_telegram(f"❗ Error {symbol}: {str(e)}")

def check_and_trade_all_symbols():
    for sym in CONFIG["symbols"]:
        check_and_trade(sym)