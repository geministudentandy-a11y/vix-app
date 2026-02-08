import yfinance as yf
import pandas as pd
import requests

# ================================
# Telegram 配置（填入你的）
# ================================

BOT_TOKEN = "8243463752:AAFnJAe_0lmcHNHuEB0IYkaquuqE7n3KBG4"
CHAT_ID = "6580441390"

# ================================
# 策略配置
# ================================

MY_AVG_COST = None
SYMBOL = '^NYFANG'

MA_WINDOW = 180
RSI_WINDOW = 14
RSI_BUY = 25

GRID_STEP = 0.05


# ================================
# Telegram发送函数
# ================================

def send_telegram(msg):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": msg
    }

    requests.post(url, data=data)


# ================================
# RSI计算
# ================================

def calculate_rsi(series, window=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/window, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1/window, min_periods=window).mean()

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


# ================================
# 主策略
# ================================

def run_strategy():

    df = yf.download(SYMBOL, period="2y", progress=False, auto_adjust=True)

    if isinstance(df, pd.DataFrame):
        df = df['Close']

    price = float(df.iloc[-1])

    ma = float(df.rolling(MA_WINDOW).mean().iloc[-1])

    rsi = float(calculate_rsi(df).iloc[-1])

    date = df.index[-1].strftime('%Y-%m-%d')

    msg = f"""
📅 {date}
📊 NYFANG Strategy

💲Price: {price:.2f}
📈MA180: {ma:.2f}
📉RSI: {rsi:.2f}
"""

    if price > ma:

        msg += "\n🔥 Bull Market"
        msg += "\n✅ 满仓持有"

    else:

        msg += "\n❄️ Bear Market"

        if rsi < RSI_BUY:

            msg += "\n🚨 BUY SIGNAL"
            msg += "\n✅ 买入 20%"

        else:

            msg += "\n💤 Cash"


    send_telegram(msg)


run_strategy()