import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import requests
import altair as alt

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(page_title="VixBooster ASX", page_icon="🦘", layout="wide")
st.title("🦘 VixBooster (美股信号 -> 澳股执行)")

# ==========================================
# 2. 策略参数 (1300万回测版)
# ==========================================
SMA_PERIOD = 200
RSI_PERIOD = 14

# --- 激进参数 ---
RSI_BULL_ENTER = 70     # 牛市常态持有线
RSI_BEAR_ENTER = 40     # 熊市反弹线
RSI_EXIT_PROFIT = 80    # 疯牛止盈线
RSI_BEAR_EXIT = 35      # 熊市止损线

VIX_LEVEL_1 = 20
VIX_LEVEL_2 = 30

# 仓位显示 (针对 30万 AUD)
PCT_BASE_TXT = "20%"    # 约 $60k AUD
PCT_BOOST_1_TXT = "40%" # 约 $120k AUD
PCT_BOOST_2_TXT = "60%" # 约 $180k AUD

# ==========================================
# 3. 核心功能函数
# ==========================================
@st.cache_data(ttl=3600)
def get_market_data():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=400)
    
    # 核心：依然下载 SPY (美股) 作为信号源
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
    # 使用 SPY 计算指标 (最准确)
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
    detail = "市场平稳，全仓持有防守标的 (HGBL)。"
    
    # --- 策略逻辑 ---
    if not is_bull:
        if current_rsi > RSI_BEAR_EXIT:
            signal = "🛡️ 红色警报：防御！"
            color = "red"
            detail = f"美股熊市反弹结束。清空 GGUS，全仓切回 HGBL 或 现金！"
        elif current_rsi < RSI_BEAR_ENTER and current_vix > 33:
            signal = "💎 钻石坑：博弈买入！"
            color = "green"
            detail = f"美股极度恐慌 (VIX {current_vix:.1f})，在澳股轻仓买入 GGUS 抢反弹！"
    elif current_rsi > RSI_EXIT_PROFIT:
        signal = "💰 止盈时刻"
        color = "orange"
        detail = f"美股 RSI 过热 ({current_rsi:.1f})。卖出部分 GGUS，落袋为安，转入 HGBL。"
    elif is_bull:
        if current_rsi < RSI_BULL_ENTER:
            if current_vix > VIX_LEVEL_2:
                signal = f"🚀 强力进攻 (重注 {PCT_BOOST_2_TXT})"
                color = "green"
                detail = f"华尔街极度恐慌！澳股大幅加仓 GGUS！"
            elif current_vix > VIX_LEVEL_1:
                signal = f"⚔️ 加力进攻 (买入 {PCT_BOOST_1_TXT})"
                color = "green"
                detail = f"恐慌机会 (VIX {current_vix:.1f})，加仓买入 GGUS。"
            else:
                signal = f"🔫 常规进攻 (买入 {PCT_BASE_TXT})"
                color = "green"
                detail = f"美股牛市常态 (RSI < {RSI_BULL_ENTER})，持有 {PCT_BASE_TXT} GGUS，其余持有 HGBL。"
        else:
            signal = "☕ 拿住 HGBL"
            color = "blue"
            detail = f"美股短期过热，暂不加仓 GGUS，持有 HGBL 等待机会。"

    return locals()

# ==========================================
# 4. 主程序运行
# ==========================================
if st.button('🔄 刷新数据 (Signal: SPY)'):
    st.cache_data.clear()
    st.rerun()

with st.spinner('正在分析华尔街信号，生成澳股指令...'):
    spy, vix = get_market_data()
    cnn_val, cnn_rating = get_cnn_index()
    res = analyze_strategy(spy, vix)

st.caption(f"📅 信号基准日期 (美股): {res['last_date']}")

# 信号卡片
if res['color'] == 'green': st.success(f"## {res['signal']}")
elif res['color'] == 'red': st.error(f"## {res['signal']}")
elif res['color'] == 'orange': st.warning(f"## {res['signal']}")
else: st.info(f"## {res['signal']}")

st.info(f"👉 **ASX 操作指令**: {res['detail']}")

st.markdown("---")

# 核心数据面板
c1, c2, c3, c4 = st.columns(4)
c1.metric("SPY (美)", f"${res['current_price']:.0f}", 
          delta=f"{res['current_price'] - res['current_sma']:.0f} (距年线)",
          delta_color="normal" if res['is_bull'] else "inverse")
c2.metric("RSI (SPY)", f"{res['current_rsi']:.1f}", f"买点 < {RSI_BULL_ENTER}") 
c3.metric("VIX (美)", f"{res['current_vix']:.1f}", "爆点 > 30")

if cnn_val:
    c4.metric("CNN (美)", f"{cnn_val:.0f}", cnn_rating)
else:
    c4.metric("CNN", "N/A", "获取失败")

st.markdown("---")

# ==========================================
# 5. 图表 (依然看 SPY，因为它是信号源)
# ==========================================
st.markdown("#### 📊 SPY 走势 (信号来源)")

chart_data = spy.tail(120).reset_index()
if 'Date' not in chart_data.columns:
    chart_data = chart_data.rename(columns={'index': 'Date'})

line_chart = alt.Chart(chart_data).mark_line(
    color='#2962FF',
    strokeWidth=2
).encode(
    x=alt.X('Date', axis=alt.Axis(format='%m-%d', title='日期')),
    y=alt.Y('Close', scale=alt.Scale(zero=False), title='价格 (USD)'),
    tooltip=['Date', 'Close']
).properties(height=350).interactive()

st.altair_chart(line_chart, use_container_width=True)
