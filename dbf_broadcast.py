import os
import requests
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TWELVEDATA_API_KEY = os.environ.get("TWELVEDATA_API_KEY")

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

    swept_high = p1_high > p2_high
    swept_low  = p1_low  < p2_low
    broke_high = body_top    > p2_high
    broke_low  = body_bottom < p2_low

    if swept_high and not broke_high:
        return "🔴 ベアリッシュ", "スイープ反転（戻り売り）OB→CRT"
    elif swept_low and not broke_low:
        return "🟢 ブリッシュ", "スイープ反転（押し目買い）OB→CRT"
    elif broke_high:
        return "🟢 ブリッシュ", "ボディブレイク継続（買い継続）FVG→CRT"
    elif broke_low:
        return "🔴 ベアリッシュ", "ボディブレイク継続（売り継続）FVG→CRT"
    else:
        return "⚪ 中立", "収縮／様子見（レンジ）"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})

def main():
    now = datetime.now(JST)
    date_str = now.strftime("%Y/%m/%d %H:%M JST")
    lines = [f"📊 *DBF デイリーバイアス*\n{date_str}\n"]

    for symbol, label in PAIRS:
        candles = get_candles(symbol)
        bias, model = judge_bias(candles)
        lines.append(f"*{label}*\nバイアス: {bias}\nモデル: {model}\n")

    message = "\n".join(lines)
    send_telegram(message)
    print(message)

if __name__ == "__main__":
    main()
