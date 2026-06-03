import os
import requests
import tweepy
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TWELVEDATA_API_KEY = os.environ.get("TWELVEDATA_API_KEY")
X_CONSUMER_KEY = os.environ.get("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.environ.get("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET")

JST = timezone(timedelta(hours=9))

PAIRS = [
    ("GBP/JPY", "GBPJPY"),
    ("EUR/USD", "EURUSD"),
    ("GBP/USD", "GBPUSD"),
    ("USD/JPY", "USDJPY"),
    ("XAU/USD", "XAUUSD"),
]

def get_candles(symbol):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": "1day",
        "outputsize": 3,
        "apikey": TWELVEDATA_API_KEY,
    }
    r = requests.get(url, params=params)
    data = r.json()
    return data.get("values", [])

def judge_bias(candles):
    if len(candles) < 3:
        return "判定不可", "データ不足"
    prev2 = candles[2]
    prev1 = candles[1]
    p2_high = float(prev2["high"])
    p2_low  = float(prev2["low"])
    p1_open = float(prev1["open"])
    p1_close= float(prev1["close"])
    p1_high = float(prev1["high"])
    p1_low  = float(prev1["low"])

    body_top    = max(p1_open, p1_close)
    body_bottom = min(p1_open, p1_close)
    swept_high  = p1_high > p2_high
    swept_low   = p1_low  < p2_low

    if swept_high and p1_close < p2_high:
        return "スイープリバーサル", "OB→CRT（ショート狙い）"
    elif swept_low and p1_close > p2_low:
        return "スイープリバーサル", "OB→CRT（ロング狙い）"
    elif body_top > p2_high:
        return "ボディブレイク継続", "FVG→CRT（ロング狙い）"
    elif body_bottom < p2_low:
        return "ボディブレイク継続", "FVG→CRT（ショート狙い）"
    else:
        return "コンソリ", "セットアップ待ち"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def send_x(message):
    try:
        client = tweepy.Client(
            consumer_key=X_CONSUMER_KEY,
            consumer_secret=X_CONSUMER_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET
        )
        client.create_tweet(text=message)
        print("X投稿成功")
    except Exception as e:
        print(f"X投稿失敗: {e}")

def main():
    now = datetime.now(JST)
    date_str = now.strftime("%Y/%m/%d")
    lines = [f"📊 DBFバイアス速報 {date_str}\n"]

    for name, symbol in PAIRS:
        candles = get_candles(symbol)
        bias, model = judge_bias(candles)
        lines.append(f"*{name}*\nバイアス: {bias}\nモデル: {model}\n")

    full_message = "\n".join(lines)
    send_telegram(full_message)

    # X用（140文字以内に要約）
    x_lines = [f"📊DBFバイアス {date_str}"]
    for name, symbol in PAIRS:
        candles = get_candles(symbol)
        bias, _ = judge_bias(candles)
        emoji = "🔴" if "ショート" in bias else "🟢" if "ロング" in bias else "⚪"
        x_lines.append(f"{emoji}{name}:{bias}")
    x_lines.append("#FX #DBF #CRT")
    x_message = "\n".join(x_lines)
    send_x(x_message)

if __name__ == "__main__":
    main()
