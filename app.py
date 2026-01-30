import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import pytz

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
@st.cache_data(ttl=3600)  # 缓存1小时，避免刷新过快被雅虎封锁
def get_data():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=500)
    
    # 下载数据
    spy = yf.download("SPY", start=start_date, end=end_date, progress=False)
    vix = yf.download("^VIX", start=start_date, end=end_date, progress=False)
    
    # 清洗数据 (处理 MultiIndex)
    if isinstance(spy.columns, pd.MultiIndex):
        spy.columns = spy.columns.get_level_values(0)
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)
        
    return spy, vix

def analyze_market(spy, vix):
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
    
    # 策略逻辑
    if not is_bull:
        if current_rsi > RSI_BEAR_EXIT:
            signal = "🛡️ 红色警报：防御！"
            color = "red"
            detail = "SPY 跌破年线且反弹结束。清空所有 QLD，换回 SPY 或 现金！"
        elif current_rsi < RSI_BEAR_ENTER and current_vix > 33:
            signal = "💎 钻石坑：博弈买入！"
            color = "green"
            detail = f"熊市极度恐慌 (VIX {current_vix:.1f})，轻仓抢 QLD 反弹！"
    elif current_rsi > RSI_EXIT_PROFIT:
        signal = "💰 止盈时刻"
        color = "orange"
        detail = f"RSI 高达 {current_rsi:.1f}，情绪过热。卖出部分 QLD，落袋为安。"
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
            signal = "☕ 拿住 SPY/SGOV"
            color = "blue"
            detail = "牛市中，但没跌到位 (RSI > 55)。持有 SPY，不要追高，等待回调。"

    return locals()

# ==========================================
# 🎨 页面布局
# ==========================================
st.set_page_config(page_title="VixBooster", page_icon="📈")
st.title("🚀 VixBooster 指挥台")

if st.button('🔄 刷新数据'):
    st.cache_data.clear()
    st.rerun()

try:
    spy, vix = get_data()
    res = analyze_market(spy, vix)
    
    st.header(f"📅 日期: {res['last_date']}")
    
    if res['color'] == 'green': st.success(f"## {res['signal']}")
    elif res['color'] == 'red': st.error(f"## {res['signal']}")
    elif res['color'] == 'orange': st.warning(f"## {res['signal']}")
    else: st.info(f"## {res['signal']}")
        
    st.info(f"👉 **指令**: {res['detail']}")
    
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("SPY", f"{res['current_price']:.0f}", f"MA200: {res['current_sma']:.0f}")
    c2.metric("RSI (14)", f"{res['current_rsi']:.1f}", "买入线: 55")
    c3.metric("VIX", f"{res['current_vix']:.1f}", "恐慌线: 20")

    st.markdown("#### 📊 SPY 走势")
    st.line_chart(spy['Close'].tail(50))

except Exception as e:
    st.error(f"连接失败: {e}")
