import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import requests # 使用原生请求库

# ==========================================
# ⚙️ 策略参数
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
# 🛠️ 核心功能
# ==========================================
@st.cache_data(ttl=3600)
def get_market_data():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=500)
    
    spy = yf.download("SPY", start=start_date, end=end_date, progress=False)
    vix = yf.download("^VIX", start=start_date, end=end_date, progress=False)
    
    # 兼容性处理
    if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
    if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)
    
    return spy, vix

@st.cache_data(ttl=3600)
def get_cnn_index():
    # 🔥 修复版：直接伪装浏览器请求 CNN 接口
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            score = data['fear_and_greed']['score']
            rating = data['fear_and_greed']['rating']
            return score, rating
    except Exception as e:
        print(f"CNN Error: {e}")
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
            detail = "牛市中，没跌到位 (RSI > 55)。持有 SPY，不追高。"

    return locals()

# ==========================================
# 🎨 页面布局
# ==========================================
st.set_page_config(page_title="VixBooster Pro", page_icon="🚀")
st.title("🚀 VixBooster Pro 指挥台")

if st.button('🔄 刷新所有数据'):
    st.cache_data.clear()
    st.rerun()

try:
    with st.spinner('正在连接华尔街 & CNN...'):
        spy, vix = get_market_data()
        cnn_val, cnn_rating = get_cnn_index()
        res = analyze_strategy(spy, vix)
    
    st.caption(f"📅 数据日期: {res['last_date']}")
    
    if res['color'] == 'green': st.success(f"## {res['signal']}")
    elif res['color'] == 'red': st.error(f"## {res['signal']}")
    elif res['color'] == 'orange': st.warning(f"## {res['signal']}")
    else: st.info(f"## {res['signal']}")
    
    st.info(f"👉 **指令**: {res['detail']}")
    
    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("SPY", f"${res['current_price']:.0f}", 
              delta=f"{res['current_price'] - res['current_sma']:.0f} (距年线)")
    c2.metric("RSI (14)", f"{res['current_rsi']:.1f}", "买点 < 55")
    c3.metric("VIX", f"{res['current_vix']:.1f}", "爆点 > 30")
    
    if cnn_val is not None:
        c4.metric("CNN 贪婪", f"{cnn_val:.0f}", cnn_rating)
    else:
        c4.metric("CNN 贪婪", "N/A", "连接超时")

    st.markdown("---")
    st.line_chart
