from statistics import mean

def calculate_ema(prices, period):
    return mean(prices[-period:])

def calculate_rsi(prices, period=14):
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = prices[-i] - prices[-i - 1]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))
    avg_gain = mean(gains) if gains else 0.0001
    avg_loss = mean(losses) if losses else 0.0001
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices):
    ema12 = mean(prices[-12:])
    ema26 = mean(prices[-26:])
    macd = ema12 - ema26
    signal = mean(prices[-9:])  # pseudo signal line
    histogram = macd - signal
    return macd, histogram

def calculate_supertrend(prices):
    base = mean(prices[-10:])
    return prices[-1] > base

def evaluate_signal(prices, volumes):
    ema9 = calculate_ema(prices, 9)
    ema21 = calculate_ema(prices, 21)
    rsi = calculate_rsi(prices)
    _, macd_hist = calculate_macd(prices)
    volume_spike = volumes[-1] > mean(volumes[-10:])
    supertrend = calculate_supertrend(prices)

    score = 0
    if ema9 > ema21: score += 0.2
    if rsi > 50: score += 0.2
    if macd_hist > 0: score += 0.2
    if volume_spike: score += 0.2
    if supertrend: score += 0.2

    direction = "LONG" if ema9 > ema21 else "SHORT" if ema9 < ema21 else "HOLD"
    return score, direction, {"ema9": ema9, "ema21": ema21, "rsi": rsi, "macd": macd_hist, "volume": volume_spike, "trend": supertrend}