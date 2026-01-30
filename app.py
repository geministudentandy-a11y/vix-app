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
st.set_page_config(page_title="VixBooster Pro", page_icon="🏆", layout="wide")
st.title("🏆 VixBooster Pro 指挥台 (终极版)")

# ==========================================
# 2. 策略参数 (已更新为 1300万回测参数)
# ==========================================
SMA_PERIOD = 200
RSI_PERIOD = 14

# --- 新参数 ---
RSI_BULL_ENTER = 70     # 激进：牛市只要不崩盘，几乎常态持有
RSI_BEAR_ENTER = 40     # 激进：熊市反弹抢得更早
RSI_EXIT_PROFIT = 80    # 贪婪：疯牛到了 80 才止盈
RSI_BEAR_EXIT = 35      # 熊市逃跑线放宽到 35

VIX_LEVEL_1 = 20
VIX_LEVEL_2 = 30

# 仓位显示用 (逻辑判断)
PCT_BASE_TXT = "20%"    # 基础仓位
PCT_BOOST_1_TXT = "40%" # 加码 (原35% -> 现40%)
PCT_BOOST_2_TXT = "60%" # 重仓

# ==========================================
# 3. 核心功能函数
# ==========================================
@st.cache_data(ttl=3600)
def get_market_data():
    end_date = datetime.datetime.now()
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
    
    # --- 策略逻辑 (基于新参数) ---
    
    if not is_bull:
        # 熊市逻辑
        if current_rsi > RSI_BEAR_EXIT:
            signal = "🛡️ 红色警报：防御！"
            color = "red"
            detail = f"熊市反弹结束 (RSI > {RSI_BEAR_EXIT})。清空 QLD，换回 SPY！"
        elif current_rsi < RSI_BEAR_ENTER and current_vix > 33:
            signal = "💎 钻石坑：博弈买入！"
            color = "green"
            detail = f"熊市极度恐慌，轻仓抢 QLD 反弹 (买点 < {RSI_BEAR_ENTER})！"
    
    elif current_rsi > RSI_EXIT_PROFIT:
        # 止盈逻辑
        signal = "💰 止盈时刻"
        color = "orange"
        detail = f"RSI 高达 {current_rsi:.1f} (超过 {RSI_EXIT_PROFIT})，严重过热。卖出部分 QLD，落袋为安。"
        
    elif is_bull:
        # 牛市逻辑
        if current_rsi < RSI_BULL_ENTER:
            # 只要 RSI < 70，就持有/买入 (常态化持有)
            if current_vix > VIX_LEVEL_2:
                signal = f"🚀 强力进攻 (重注 {PCT_BOOST_2_TXT})"
                color = "green"
                detail = f"极度恐慌 (VIX {current_vix:.1f})！大幅加仓 QLD！"
            elif current_vix > VIX_LEVEL_1:
                signal = f"⚔️ 加力进攻 (买入 {PCT_BOOST_1_TXT})"
                color = "green"
                detail = f"恐慌机会 (VIX {current_vix:.1f})，加仓买入 QLD。"
            else:
                signal = f"🔫 常规进攻 (买入 {PCT_BASE_TXT})"
                color = "green"
                detail = f"牛市常态持有/加仓 (RSI < {RSI_BULL_ENTER})，持有 {PCT_BASE_TXT} QLD。"
        else:
            signal = "☕ 拿住 SPY"
            color = "blue"
            detail = f"牛市极端过热前期 (RSI > {RSI_BULL_ENTER})，暂时持有 SPY，等待微调或止盈。"

    return locals()

# ==========================================
# 4. 主程序运行
# ==========================================
if st.button('🔄 刷新数据'):
    st.cache_data.clear()
    st.rerun()

with st.spinner('正在计算 1300万 策略模型...'):
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
# 更新了副标题显示的阈值
c2.metric("RSI (14)", f"{res['current_rsi']:.1f}", f"买点 < {RSI_BULL_ENTER}") 
c3.metric("VIX 恐慌", f"{res['current_vix']:.1f}", "爆点 > 30")
if cnn_val:
    c4.metric("CNN 贪婪", f"{cnn_val:.0f}", cnn_rating)
else:
    c4.metric("CNN 贪婪", "N/A", "获取失败")

st.markdown("---")

# ==========================================
# 5. 高级图表 (120天 动态)
# ==========================================
st.markdown("#### 📊 SPY 近120天走势")

chart_data = spy.tail(120).reset_index()
if 'Date' not in chart_data.columns:
    chart_data = chart_data.rename(columns={'index': 'Date'})

line_chart = alt.Chart(chart_data).mark_line(
    color='#2962FF',
    strokeWidth=2
).encode(
    x=alt.X('Date', axis=alt.Axis(format='%m-%d', title='日期')),
    y=alt.Y('Close', scale=alt.Scale(zero=False), title='价格'),
    tooltip=['Date', 'Close']
).properties(height=350).interactive()

st.altair_chart(line_chart, use_container_width=True)
