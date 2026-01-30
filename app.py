import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import requests
import altair as alt  # 引入绘图库

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(page_title="VixBooster Pro", page_icon="🚀", layout="wide") # 宽屏模式
st.title("🚀 VixBooster Pro 指挥台")

# ==========================================
# 2. 策略参数
# ==========================================
SMA_PERIOD = 200
RSI_PERIOD = 14
RSI_BULL_ENTER = 55
RSI_BEAR_ENTER = 30
RSI_EXIT_PROFIT = 75
RSI_BEAR_EXIT = 30
VIX_LEVEL_1 = 20
VIX_LEVEL_2 = 30

# ==========================================
# 3. 核心功能函数
# ==========================================
@st.cache_data(ttl=3600)
def get_market_data():
    end_date = datetime.datetime.now()
    #以此保证有足够数据计算200日均线
    start_date = end_date - datetime.timedelta(days=400) 
    
    spy = yf.download("SPY", start=start_date, end=end_date, progress=False)
    vix = yf.download("^VIX", start=start_date, end=end_date, progress=False)
    
    if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
    if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)
    
    return spy, vix

@st.cache_data(ttl=3600)
def get_cnn_index():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data['fear_and_greed']['score'], data['fear_and_greed']['rating']
    except:
        pass
    return None, "获取失败"

def analyze_strategy(spy, vix):
    spy['SMA200'] = ta.sma(spy['Close'], length=SMA_PERIOD)
    spy['RSI'] = ta.rsi(spy['Close'], length=RSI_PERIOD)
    
    current_price = spy['Close'].iloc[-1]
    current_sma = spy['SMA200'].iloc[-1]
    current_rsi = spy['RSI'].iloc[-1]
    current_vix = vix['Close'].iloc[-1]
    last_date = spy.index[-1].strftime('%Y-%m-%d')
    
    is_bull = current_price > current_sma
    
    signal = "无操作 (Hold)"
    color = "gray"
    detail = "市场平稳，持有现有仓位。"
    
    if not is_bull:
        if current_rsi > RSI_BEAR_EXIT:
            signal = "🛡️ 红色警报：防御！"
            color = "red"
            detail = "熊市反弹结束。清空所有 QLD，换回 SPY！"
        elif current_rsi < RSI_BEAR_ENTER and current_vix > 33:
            signal = "💎 钻石坑：博弈买入！"
            color = "green"
            detail = f"熊市极度恐慌 (VIX {current_vix:.1f})，轻仓抢 QLD 反弹！"
    elif current_rsi > RSI_EXIT_PROFIT:
        signal = "💰 止盈时刻"
        color = "orange"
        detail = f"RSI 高达 {current_rsi:.1f}，过热。卖出部分 QLD。"
    elif is_bull:
        if current_rsi < RSI_BULL_ENTER:
            if current_vix > VIX_LEVEL_2:
                signal = "🚀 强力进攻 (重注 60%)"
                color = "green"
                detail = f"极度恐慌 (VIX {current_vix:.1f})！大幅加仓 QLD！"
            elif current_vix > VIX_LEVEL_1:
                signal = "⚔️ 加力进攻 (买入 35%)"
                color = "green"
                detail = f"恐慌机会 (VIX {current_vix:.1f})，加仓买入 QLD。"
            else:
                signal = "🔫 常规进攻 (买入 20%)"
                color = "green"
                detail = "牛市温和回调，买入 20% QLD。"
        else:
            signal = "☕ 拿住 SPY"
            color = "blue"
            detail = "牛市中，没跌到位。持有 SPY，不追高。"

    return locals()

# ==========================================
# 4. 主程序运行
# ==========================================
if st.button('🔄 刷新数据'):
    st.cache_data.clear()
    st.rerun()

with st.spinner('正在分析市场数据...'):
    spy, vix = get_market_data()
    cnn_val, cnn_rating = get_cnn_index()
    res = analyze_strategy(spy, vix)

st.caption(f"📅 数据日期: {res['last_date']}")

# 信号卡片
if res['color'] == 'green': st.success(f"## {res['signal']}")
elif res['color'] == 'red': st.error(f"## {res['signal']}")
elif res['color'] == 'orange': st.warning(f"## {res['signal']}")
else: st.info(f"## {res['signal']}")

st.info(f"👉 **指令**: {res['detail']}")

st.markdown("---")

# 核心数据
c1, c2, c3, c4 = st.columns(4)
c1.metric("SPY 价格", f"${res['current_price']:.0f}", 
          delta=f"{res['current_price'] - res['current_sma']:.0f} (距年线)",
          delta_color="normal" if res['is_bull'] else "inverse")
c2.metric("RSI (14)", f"{res['current_rsi']:.1f}", "买点 < 55")
c3.metric("VIX 恐慌", f"{res['current_vix']:.1f}", "爆点 > 30")
if cnn_val:
    c4.metric("CNN 贪婪", f"{cnn_val:.0f}", cnn_rating)
else:
    c4.metric("CNN 贪婪", "N/A", "获取失败")

st.markdown("---")

# ==========================================
# 5. 高级图表区 (Altair 动态图)
# ==========================================
st.markdown("#### 📊 SPY 近120天走势 (动态坐标)")

# 准备绘图数据：取最后120天
chart_data = spy.tail(120).reset_index()
# 确保列名正确
if 'Date' not in chart_data.columns:
    chart_data = chart_data.rename(columns={'index': 'Date'})

# 绘制饱满的折线图 (scale=Zero:False 是关键)
line_chart = alt.Chart(chart_data).mark_line(
    color='#2962FF',  # 鲜艳的蓝色
    strokeWidth=2
).encode(
    x=alt.X('Date', axis=alt.Axis(format='%m-%d', title='日期')),
    y=alt.Y('Close', 
            scale=alt.Scale(zero=False),  # 关键：不从0开始，自动适配波动范围
            title='价格 ($)'),
    tooltip=['Date', 'Close']
).properties(
    height=350  # 图表高度
).interactive() # 允许缩放和拖拽

st.altair_chart(line_chart, use_container_width=True)
