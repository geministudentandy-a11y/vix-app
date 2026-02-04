import yfinance as yf
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import MonthEnd
import os

# ==========================================
# ⚙️ 策略参数
# ==========================================
PANDA_MA_PERIOD = 200
PANDA_MOM_PERIOD = 95
CB_N = 5
CB_DROP = 0.075
SQ_BB_PERIOD = 20
SQ_BB_STD = 2.5
SQ_RSI_PERIOD = 14
SQ_RSI_ENTRY = 30
SQ_RSI_ALERT = 35

def generate_html():
    print("📡 正在获取数据并生成网页...")
    tickers = ['SPY', 'QQQ']
    try:
        data = yf.download(tickers, period="2y", progress=False, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex):
            df = data['Close'].copy()
        else:
            df = data.copy()
        df = df.dropna()
    except Exception as e:
        print(f"Error: {e}")
        return

    # === 计算指标 ===
    latest = df.iloc[-1]
    curr_date = df.index[-1]
    date_str = curr_date.strftime('%Y-%m-%d')
    weekday_str = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][curr_date.weekday()]
    
    # 日历
    month_end_date = curr_date + MonthEnd(0)
    days_to_end = (month_end_date - curr_date).days
    
    # 熊猫
    spy_ma200 = df['SPY'].rolling(PANDA_MA_PERIOD).mean().iloc[-1]
    qqq_old = df['QQQ'].shift(PANDA_MOM_PERIOD).iloc[-1]
    spy_max = df['SPY'].rolling(CB_N).max().iloc[-1]
    drawdown = (latest['SPY'] / spy_max) - 1
    
    panda_bull = (latest['SPY'] > spy_ma200) and (latest['QQQ'] > qqq_old)
    panda_cb = drawdown < -CB_DROP
    
    # 敢死队
    sma = df['QQQ'].rolling(SQ_BB_PERIOD).mean()
    std = df['QQQ'].rolling(SQ_BB_PERIOD).std()
    lower_band = sma - (SQ_BB_STD * std)
    
    delta = df['QQQ'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(SQ_RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(SQ_RSI_PERIOD).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    curr_rsi = rsi.iloc[-1]
    curr_lower = lower_band.iloc[-1]
    
    sq_fire = (latest['QQQ'] < curr_lower) and (curr_rsi < SQ_RSI_ENTRY)
    sq_gap_pct = (latest['QQQ'] - curr_lower) / latest['QQQ'] * 100
    sq_alert = (sq_gap_pct < 2.0) or (curr_rsi < SQ_RSI_ALERT)

    # === 🎨 生成 HTML ===
    # 颜色定义
    color_bg = "#111827" # 深黑底
    color_card = "#1F2937" # 卡片灰
    color_text = "#F3F4F6"
    color_green = "#10B981"
    color_red = "#EF4444"
    color_yellow = "#F59E0B"
    
    # 逻辑判断颜色和文字
    # 1. 月历状态
    if days_to_end == 0:
        cal_status = "⚠️ 月底调仓日 (Last Day)"
        cal_color = color_yellow
    elif days_to_end <= 3:
        cal_status = f"⏳ 临近月底 (剩 {days_to_end} 天)"
        cal_color = color_text
    else:
        cal_status = f"💤 非调仓期 (剩 {days_to_end} 天)"
        cal_color = "#9CA3AF"

    # 2. 敢死队状态
    if sq_fire:
        sq_title = "🔴 全员出击 (ACTIVE)"
        sq_class = "bg-red-600 animate-pulse"
        sq_msg = "立即买入 $10,000 QLD"
    elif sq_alert:
        sq_title = "🟡 高度警惕 (WATCHING)"
        sq_class = "bg-yellow-600"
        sq_msg = "接近射程，准备弹药"
    else:
        sq_title = "🟢 回营休息 (SLEEP)"
        sq_class = "bg-green-600"
        sq_msg = "无操作"

    # 3. 熊猫状态
    if panda_cb:
        p_title = "🚨 熔断触发 (CRASH)"
        p_bg = "border-red-500 border-2"
        p_act = "QLD 换 QQQ"
    elif panda_bull:
        p_title = "🐂 牛市进攻 (BULL)"
        p_bg = "border-green-500 border-2"
        p_act = "持有 QLD"
    else:
        p_title = "🐻 熊市防御 (BEAR)"
        p_bg = "border-gray-500 border-2"
        p_act = "空仓 / 现金"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Kung Fu Panda Command Center</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {{ background-color: {color_bg}; color: {color_text}; font-family: sans-serif; }}
        </style>
    </head>
    <body class="p-6 max-w-md mx-auto">
        
        <div class="text-center mb-6">
            <h1 class="text-3xl font-bold tracking-wider text-white">🐼 KUNG FU PANDA</h1>
            <p class="text-gray-400 mt-2">{date_str} <span class="text-xs bg-gray-700 px-2 py-1 rounded">{weekday_str}</span></p>
        </div>

        <div class="bg-gray-800 rounded-xl p-4 mb-4 shadow-lg">
            <h2 class="text-gray-400 text-xs uppercase tracking-widest mb-1">Monthly Schedule</h2>
            <div class="text-lg font-semibold" style="color: {cal_color}">{cal_status}</div>
        </div>

        <div class="rounded-xl p-5 mb-4 shadow-lg text-white {sq_class}">
            <div class="flex justify-between items-center mb-2">
                <h2 class="font-bold text-xl">🏴‍☠️ 敢死队 (SQ)</h2>
                <span class="text-xs bg-black bg-opacity-20 px-2 py-1 rounded">QQQ</span>
            </div>
            <div class="text-2xl font-black mb-2">{sq_title}</div>
            <div class="bg-black bg-opacity-20 rounded p-3 text-sm">
                <p>👉 指令: <strong>{sq_msg}</strong></p>
                <div class="mt-2 border-t border-white border-opacity-20 pt-2 flex justify-between">
                    <span>距下轨: {sq_gap_pct:.2f}%</span>
                    <span>RSI: {curr_rsi:.1f}</span>
                </div>
            </div>
        </div>

        <div class="bg-gray-800 rounded-xl p-5 mb-6 shadow-lg {p_bg}">
            <div class="flex justify-between items-center mb-2">
                <h2 class="font-bold text-xl">🐼 熊猫主力</h2>
                <span class="text-xs bg-gray-700 px-2 py-1 rounded">SPY Trend</span>
            </div>
            <div class="text-xl font-bold mb-2">{p_title}</div>
            <div class="text-gray-300 text-sm">
                建议持仓: <strong class="text-white text-lg">{p_act}</strong>
            </div>
            <div class="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-500">
                <div>SPY > MA200: {str(latest['SPY'] > spy_ma200)}</div>
                <div>QQQ Momentum: {str(latest['QQQ'] > qqq_old)}</div>
            </div>
        </div>

        <div class="text-center text-gray-600 text-xs">
            SPY: ${latest['SPY']:.2f} | QQQ: ${latest['QQQ']:.2f}<br>
            Updated at {datetime.now().strftime('%H:%M:%S UTC')}
        </div>

    </body>
    </html>
    """

    with open("index.html", "w", encoding='utf-8') as f:
        f.write(html_content)
    print("✅ 网页生成完毕: index.html")

if __name__ == "__main__":
    generate_html()
