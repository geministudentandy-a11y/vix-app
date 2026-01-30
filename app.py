import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import altair as alt
import json
from github import Github

# ==========================================
# 1. 页面配置 & 云端同步
# ==========================================
st.set_page_config(page_title="VixBooster ASX", page_icon="⚡", layout="wide")
st.title("⚡ VixBooster (信号增强版)")

# --- GitHub 云存储函数 ---
def load_data_from_github():
    try:
        if "GITHUB_TOKEN" not in st.secrets:
            return {"hgbl": 0, "ggus": 0, "cash": 300000.0}
        token = st.secrets["GITHUB_TOKEN"]
        g = Github(token)
        repo = g.get_user().get_repo("vix-app") 
        try:
            contents = repo.get_contents("portfolio.json")
            data = json.loads(contents.decoded_content.decode())
            return data
        except:
            return {"hgbl": 0, "ggus": 0, "cash": 300000.0}
    except:
        return {"hgbl": 0, "ggus": 0, "cash": 300000.0}

def save_data_to_github(hgbl, ggus, cash):
    try:
        token = st.secrets["GITHUB_TOKEN"]
        g = Github(token)
        repo = g.get_user().get_repo("vix-app")
        data = {"hgbl": hgbl, "ggus": ggus, "cash": cash}
        content = json.dumps(data, indent=2)
        try:
            file = repo.get_contents("portfolio.json")
            repo.update_file(file.path, "Update portfolio", content, file.sha)
        except:
            repo.create_file("portfolio.json", "Init portfolio", content)
        st.toast("✅ 云端同步成功！", icon="☁️")
        return True
    except Exception as e:
        st.error(f"保存失败: {e}")
        return False

# 初始化
if 'data_loaded' not in st.session_state:
    with st.spinner('正在从云端拉取数据...'):
        cloud_data = load_data_from_github()
        st.session_state.my_hgbl = cloud_data.get('hgbl', 0)
        st.session_state.my_ggus = cloud_data.get('ggus', 0)
        st.session_state.my_cash = cloud_data.get('cash', 300000.0)
        st.session_state.data_loaded = True

# ==========================================
# 2. 侧边栏：资产与参数
# ==========================================
with st.sidebar:
    st.header("☁️ 云端资产库")
    new_hgbl = st.number_input("HGBL 持仓", min_value=0, step=100, value=st.session_state.my_hgbl)
    new_ggus = st.number_input("GGUS 持仓", min_value=0, step=100, value=st.session_state.my_ggus)
    new_cash = st.number_input("可用现金", min_value=0.0, step=1000.0, value=float(st.session_state.my_cash))
    
    if st.button("💾 保存并同步", type="primary"):
        if save_data_to_github(new_hgbl, new_ggus, new_cash):
            st.session_state.my_hgbl = new_hgbl
            st.session_state.my_ggus = new_ggus
            st.session_state.my_cash = new_cash
            st.rerun()

    st.markdown("---")
    st.header("⚙️ 核心参数")
    st.info("""
    **🟢 买入标准**
    * **牛市**: RSI < 70
    * **熊市**: RSI < 40 + VIX > 33
    
    **🔴 卖出标准**
    * **止盈**: RSI > 80
    * **止损**: 熊市 + RSI > 35
    
    **🔥 VIX 仓位**
    * **> 20**: 40% 仓位
    * **> 30**: 60% 仓位
    """)

# ==========================================
# 3. 策略逻辑
# ==========================================
SMA_PERIOD = 200
RSI_PERIOD = 14
RSI_BULL_ENTER = 70
RSI_BEAR_ENTER = 40
RSI_EXIT_PROFIT = 80
RSI_BEAR_EXIT = 35
VIX_LEVEL_1 = 20
VIX_LEVEL_2 = 30
TARGET_PCT_BASE = 0.20
TARGET_PCT_BOOST_1 = 0.40
TARGET_PCT_BOOST_2 = 0.60

@st.cache_data(ttl=3600)
def get_market_data():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=450)
    spy = yf.download("SPY", start=start_date, end=end_date, progress=False)
    vix = yf.download("^VIX", start=start_date, end=end_date, progress=False)
    try:
        tickers = yf.download(["HGBL.AX", "GGUS.AX"], period="5d", progress=False)['Close']
        p_hgbl = tickers['HGBL.AX'].dropna().iloc[-1]
        p_ggus = tickers['GGUS.AX'].dropna().iloc[-1]
    except:
        p_hgbl = 0
        p_ggus = 0
    if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
    if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)
    return spy, vix, p_hgbl, p_ggus

def calculate_strategy(spy, vix):
    spy['SMA200'] = ta.sma(spy['Close'], length=SMA_PERIOD)
    spy['RSI'] = ta.rsi(spy['Close'], length=RSI_PERIOD)
    
    curr_price = spy['Close'].iloc[-1]
    curr_sma = spy['SMA200'].iloc[-1]
    curr_rsi = spy['RSI'].iloc[-1]
    curr_vix = vix['Close'].iloc[-1]
    is_bull = curr_price > curr_sma
    
    # 策略判断
    target_pct = 0.0
    signal_name = "观望"
    reason = "无操作"
    
    if not is_bull:
        if curr_rsi > RSI_BEAR_EXIT:
            target_pct = 0.0
            signal_name = "🛡️ 红色警报"
            reason = "熊市反弹结束，清空进攻仓位。"
        elif curr_rsi < RSI_BEAR_ENTER and curr_vix > 33:
            target_pct = TARGET_PCT_BASE
            signal_name = "💎 钻石坑"
            reason = "极度恐慌，抢反弹。"
        else:
            target_pct = 0.0
            signal_name = "🛡️ 熊市防御"
            reason = "熊市回避。"
    elif curr_rsi > RSI_EXIT_PROFIT:
        target_pct = TARGET_PCT_BASE
        signal_name = "💰 止盈减仓"
        reason = "RSI过热，获利了结。"
    elif is_bull:
        if curr_rsi < RSI_BULL_ENTER:
            if curr_vix > VIX_LEVEL_2:
                target_pct = TARGET_PCT_BOOST_2
                signal_name = "🚀 强力进攻 (60%)"
                reason = "VIX极高，重仓机会。"
            elif curr_vix > VIX_LEVEL_1:
                target_pct = TARGET_PCT_BOOST_1
                signal_name = "⚔️ 加力进攻 (40%)"
                reason = "VIX较高，加仓机会。"
            else:
                target_pct = TARGET_PCT_BASE
                signal_name = "🔫 常规进攻 (20%)"
                reason = "牛市常态持有。"
        else:
            target_pct = 0.0
            signal_name = "☕ 暂时休息"
            reason = "短期过热，暂不持仓。"
    return locals()

# ==========================================
# 4. 主程序 UI
# ==========================================
if st.button('🔄 刷新信号'):
    st.cache_data.clear()
    st.rerun()

with st.spinner('正在分析华尔街数据...'):
    spy, vix, p_hgbl, p_ggus = get_market_data()
    res = calculate_strategy(spy, vix)

    # 计算交易
    h_qty = st.session_state.my_hgbl
    g_qty = st.session_state.my_ggus
    cash = st.session_state.my_cash
    total_assets = (h_qty * p_hgbl) + (g_qty * p_ggus) + cash
    target_val = total_assets * res['target_pct']
    curr_val = g_qty * p_ggus
    diff = target_val - curr_val
    
    trade_text = "✅ 仓位完美 (Hold)"
    trade_amt = 0
    if abs(diff) > 1000:
        qty = int(abs(diff) / p_ggus) if p_ggus > 0 else 0
        trade_amt = abs(diff)
        if diff > 0: trade_text = f"🔵 买入 {qty} 股 GGUS"
        else: trade_text = f"🔴 卖出 {qty} 股 GGUS"

# --- 核心显示区 ---
if "买入" in trade_text: st.success(f"### {trade_text}\n**金额: ${trade_amt:,.0f}** | 原因: {res['reason']}")
elif "卖出" in trade_text: st.warning(f"### {trade_text}\n**金额: ${trade_amt:,.0f}** | 原因: {res['reason']}")
else: st.info(f"### {trade_text}\n原因: {res['reason']}")

st.markdown("---")

# Row 1: 个人资产 (AUD)
st.markdown("##### 💼 个人资产 (AUD)")
c1, c2 = st.columns(2)
c1.metric("总资产", f"${total_assets:,.0f}")
c2.metric("GGUS 仓位", f"{curr_val/total_assets*100:.1f}%", f"目标 {res['target_pct']*100:.0f}%")

st.markdown("---")

# Row 2: 市场信号 (USD) - 这里就是您要的数据
st.markdown("##### 📡 市场信号 (SPY/VIX)")
m1, m2, m3 = st.columns(3)

# 指标 1: SPY 价格与年线距离
dist_sma = res['curr_price'] - res['curr_sma']
m1.metric("SPY 价格", f"${res['curr_price']:.0f}", 
          delta=f"{dist_sma:.0f} (距年线)", 
          delta_color="normal" if res['is_bull'] else "inverse")

# 指标 2: RSI
m2.metric("RSI (14)", f"{res['curr_rsi']:.1f}", f"买点 < {RSI_BULL_ENTER}")

# 指标 3: VIX
m3.metric("VIX 恐慌", f"{res['curr_vix']:.1f}", "爆发 > 20")

st.caption(f"澳股参考价: HGBL ${p_hgbl:.2f} | GGUS ${p_ggus:.2f}")

st.markdown("---")
st.markdown("#### 📊 SPY 走势 (含200日均线)")

# 图表
chart_data = spy.tail(120).reset_index()
if 'Date' not in chart_data.columns: chart_data = chart_data.rename(columns={'index': 'Date'})

# K线(收盘价)
line = alt.Chart(chart_data).mark_line().encode(
    x=alt.X('Date', title='日期'),
    y=alt.Y('Close', scale=alt.Scale(zero=False), title='价格 (USD)'),
    tooltip=['Date', 'Close', 'SMA200']
)
# 均线(橙色)
sma = alt.Chart(chart_data).mark_line(color='orange', strokeDash=[5,5]).encode(
    x='Date', y='SMA200'
)

st.altair_chart((line + sma).interactive(), use_container_width=True)
