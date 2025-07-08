import os, time, hmac, hashlib, json, requests
from dotenv import load_dotenv
from strategy import evaluate_signal
from telegram import send_telegram
from google_sheets import log_trade

load_dotenv()
API_KEY = os.getenv("MEXC_API_KEY")
SECRET = os.getenv("MEXC_API_SECRET")
BASE_URL = "https://contract.mexc.com"

with open("config.json") as f:
    CONFIG = json.load(f)

def sign_request(params, secret):
    sorted_params = sorted(params.items())
    query = "&".join(f"{k}={v}" for k, v in sorted_params)
    to_sign = query + f"&secret_key={secret}"
    signature = hmac.new(secret.encode(), to_sign.encode(), hashlib.sha256).hexdigest().upper()
    return signature

def get_headers(params):
    signature = sign_request(params, SECRET)
    headers = {
        "Content-Type": "application/json",
        "ApiKey": API_KEY,
        "Request-Time": str(int(time.time() * 1000)),
        "Signature": signature
    }
    return headers

def get_candles(symbol, interval='1m', limit=50):
    res = requests.get(f"{BASE_URL}/api/v1/contract/kline/{symbol}", params={"interval": interval, "limit": limit})
    data = res.json().get("data", [])
    prices = [float(k["close"]) for k in data]
    volumes = [float(k["vol"]) for k in data]
    return prices, volumes

def get_balance():
    params = {"api_key": API_KEY, "req_time": str(int(time.time() * 1000))}
    headers = get_headers(params)
    res = requests.get(f"{BASE_URL}/api/v1/private/account/assets", headers=headers)
    balances = res.json().get("data", [])
    for b in balances:
        if b["currency"] == "USDT":
            return float(b["availableBalance"])
    return 0

def get_position(symbol):
    params = {"api_key": API_KEY, "req_time": str(int(time.time() * 1000))}
    headers = get_headers(params)
    res = requests.get(f"{BASE_URL}/api/v1/private/position/open_positions", headers=headers)
    data = res.json().get("data", [])
    for p in data:
        if p["symbol"] == symbol:
            return float(p["positionAmt"]), float(p["avgEntryPrice"])
    return 0, 0

def place_order(symbol, side, qty):
    params = {
        "api_key": API_KEY,
        "req_time": str(int(time.time() * 1000)),
        "symbol": symbol,
        "price": 0,
        "vol": qty,
        "leverage": CONFIG["leverage"],
        "side": 1 if side == "BUY" else 2,
        "type": 1,  # Market Order
        "open_type": 1,
        "position_id": 0
    }
    headers = get_headers(params)
    return requests.post(f"{BASE_URL}/api/v1/private/order/submit", headers=headers, json=params).json()

def close_position(symbol, amt):
    side = "SELL" if amt > 0 else "BUY"
    place_order(symbol, side, abs(amt))
    send_telegram(f"🔴 Closed {symbol}: {side} {abs(amt)}")
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

            if change_pct >= CONFIG["take_profit_pct"]:
                close_position(symbol, amt)
                send_telegram(f"✅ TP hit on {symbol} ({change_pct:.2f}%)")
            elif change_pct <= -CONFIG["stop_loss_pct"]:
                close_position(symbol, amt)
                send_telegram(f"🛑 SL hit on {symbol} ({change_pct:.2f}%)")
            return

        if score >= CONFIG["min_confidence_score"] and direction != "HOLD":
            usdt = get_balance()
            risk_amount = usdt * CONFIG["risk_per_trade"]
            qty = round((risk_amount * CONFIG["leverage"]) / price_now, 3)
            side = "BUY" if direction == "LONG" else "SELL"
            place_order(symbol, side, qty)
            send_telegram(f"🚀 {direction} {symbol} | Score: {score:.2f} | Qty: {qty}")
            log_trade(symbol, side, qty, "OPEN", debug)
    except Exception as e:
        send_telegram(f"❗ MEXC Error {symbol}: {str(e)}")

def check_and_trade_all_symbols():
    for symbol in CONFIG["symbols"]:
        check_and_trade(symbol)
