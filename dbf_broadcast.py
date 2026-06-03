import os
import requests
from datetime import datetime, timezone, timedelta

# 環境変数から設定を読み込む
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
OANDA_API_KEY = os.environ.get("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID")

JST = timezone(timedelta(hours=9))

PAIRS = [
    ("GBP_JPY", "GBPJPY"),
    ("EUR_USD", "EURUSD"),
    ("GBP_USD", "GBPUSD"),
    ("USD_JPY", "USDJPY"),
    ("XAU_USD", "XAUUSD"),
]

def get_candles(instrument):
    url = f"https://api-fxtrade.oanda.com/v3/instruments/{instrument}/candles"
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}
    params = {"count": 3, "granularity": "D", "price": "M"}
    r = requests.get(url, headers=headers, params=params)
    return r.json().get("candles", [])

def judge_bias(candles):
    if len(candles) < 3:
        return "判定不可", "データ不足"
    prev2 = candles[-3]["mid"]
    prev1 = candles[-2]["mid"]
    p2_high = float(prev2["h"])
    p2_low  = float(prev2["l"])
    p1_open = float(prev1["o"])
    p1_close= float(prev1["c"])
    p1_high = float(prev1["h"])
    p1_low  = float(prev1["l"])

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

    for oanda_id, label in PAIRS:
        candles = get_candles(oanda_id)
        bias, model = judge_bias(candles)
        lines.append(f"*{label}*\nバイアス: {bias}\nモデル: {model}\n")

    message = "\n".join(lines)
    send_telegram(message)
    print(message)

if __name__ == "__main__":
    main()
