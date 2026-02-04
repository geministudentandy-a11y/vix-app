import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pandas.tseries.offsets import MonthEnd
from datetime import datetime
import base64
import os

# ==========================================
# 🎨 PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="PANDA COMMAND",
    page_icon="🐼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🖼️ IMAGE LOADER
# ==========================================

def load_image_as_base64(filename):
    possible_paths = [
        filename,
        os.path.join("images", filename),
        os.path.join(os.getcwd(), filename),
    ]
    for filepath in possible_paths:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    return base64.b64encode(f.read()).decode()
            except:
                continue
    return "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

# Load Images
REST_IMAGE = load_image_as_base64('rest.png')
ATTACK_IMAGE = load_image_as_base64('attack.png')
BULL_IMAGE = load_image_as_base64('Bull.png') 
BEAR_IMAGE = load_image_as_base64('Bear.png')
MELTDOWN_IMAGE = load_image_as_base64('meltdown.png') # Changed from rebalance

# ==========================================
# 💎 CSS STYLING
# ==========================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1a2e 50%, #16213e 100%);
        background-attachment: fixed;
    }
    
    /* Headers */
    h1, h2, h3 { font-family: 'Orbitron', monospace !important; color: #00ffff !important; }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-family: 'Orbitron', monospace !important;
        color: #00ff00 !important;
        font-size: 1.8rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Share Tech Mono', monospace !important;
        color: #00ffff !important;
    }

    /* Card Styling */
    .tactical-card-base {
        position: relative;
        background: rgba(0, 0, 0, 0.75);
        border: 2px solid;
        padding: 1.2rem;
        height: 350px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        overflow: hidden;
        box-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    
    .tactical-card-base::before {
        content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-size: cover; background-position: center;
        opacity: 0.35; filter: brightness(0.7) contrast(1.2); z-index: 0;
    }
    
    .card-content { position: relative; z-index: 1; text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
    
    .card-title { font-family: 'Orbitron'; font-weight: 900; letter-spacing: 2px; font-size: 1.2rem; margin-bottom: 10px; text-shadow: 0 0 5px currentColor; }
    .card-data { font-family: 'Share Tech Mono'; font-size: 1.1rem; color: #fff; margin: auto 0; font-weight: bold; background: rgba(0,0,0,0.5); padding: 10px; border-radius: 4px; }
    .card-status { font-family: 'Orbitron'; font-size: 1.4rem; font-weight: 900; padding: 10px; border-top: 1px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.6); }

    .scanline::after {
        content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: linear-gradient(to bottom, transparent 0%, rgba(0, 255, 255, 0.05) 50%, transparent 100%);
        animation: scan 6s linear infinite; pointer-events: none; z-index: 2;
    }
    @keyframes scan { 0% { transform: translateY(-100%); } 100% { transform: translateY(100%); } }
</style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ CONTROL PANEL
# ==========================================

with st.sidebar:
    st.markdown("### ⚙️ SYSTEM PARAMETERS")
    PANDA_MA = st.number_input("SPY MA FILTER", value=200)
    PANDA_MOM = st.number_input("QQQ MOMENTUM", value=95)
    CB_DROP = st.number_input("MELTDOWN TRIGGER (%)", value=7.5, step=0.5) / 100.0
    
    st.markdown("---")
    st.markdown("### 🏴‍☠️ SQUAD SETTINGS")
    SQ_BB_N = st.number_input("BB PERIOD", value=20)
    SQ_BB_STD = st.number_input("BB DEVIATION", value=2.5)
    SQ_RSI_ENTRY = st.number_input("RSI TRIGGER", value=30)

# ==========================================
# 📥 DATA CORE
# ==========================================

@st.cache_data(ttl=300)
def get_market_data():
    # Added ^VIX to download
    tickers = ['SPY', 'QQQ', '^VIX']
    data = yf.download(tickers, period="2y", progress=False, group_by='ticker', auto_adjust=True)
    
    # Process Data into single DF for ease of use
    df = pd.DataFrame()
    df['SPY'] = data['SPY']['Close']
    df['QQQ'] = data['QQQ']['Close']
    df['VIX'] = data['^VIX']['Close']
    df = df.dropna()

    # Calculations
    df['SPY_MA'] = df['SPY'].rolling(PANDA_MA).mean()
    df['QQQ_MOM_Ref'] = df['QQQ'].shift(PANDA_MOM)
    
    # Drawdown (Peak to Trough)
    spy_max = df['SPY'].rolling(252).max() # 1 year rolling max
    df['Drawdown'] = (df['SPY'] / spy_max) - 1
    
    # Bollinger Bands for QQQ
    sma = df['QQQ'].rolling(SQ_BB_N).mean()
    std = df['QQQ'].rolling(SQ_BB_N).std()
    df['Lower_Band'] = sma - (SQ_BB_STD * std)
    df['Upper_Band'] = sma + (SQ_BB_STD * std) # Added Upper for "Retreat" logic check
    
    # RSI
    delta = df['QQQ'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

try:
    df = get_market_data()
    if df.empty: st.stop()
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    curr_date = df.index[-1]
except Exception as e:
    st.error(f"DATA ERROR: {e}")
    st.stop()

# ==========================================
# 🧠 LOGIC ENGINE
# ==========================================

# 1. Date Logic (Rebalance)
month_end = curr_date + MonthEnd(0)
days_to_rebalance = (month_end - curr_date).days

# 2. Meltdown Logic (Card 1)
# Drawdown is negative (e.g., -0.02). CB_DROP is positive (0.075).
# Meltdown happens when Drawdown <= -CB_DROP
current_dd_pct = abs(latest['Drawdown'])
cb_target_pct = CB_DROP
dist_to_meltdown = max(0, cb_target_pct - current_dd_pct) * 100
is_meltdown = current_dd_pct >= cb_target_pct

# 3. Squad Logic (Card 2)
# Distance to Lower Band (Attack Trigger)
price_qqq = latest['QQQ']
lower_band = latest['Lower_Band']
dist_to_attack_pct = ((price_qqq - lower_band) / price_qqq) * 100
is_attack = price_qqq < lower_band and latest['RSI'] < SQ_RSI_ENTRY

# 4. Panda Force Logic (Card 3)
# Bull Condition: SPY > MA AND QQQ > Momentum
is_bull = latest['SPY'] > latest['SPY_MA'] and latest['QQQ'] > latest['QQQ_MOM_Ref']

# Calculate distance to flip state
if is_bull:
    # How much drop to become Bear?
    # 1. SPY drop to MA
    dist_spy_ma = ((latest['SPY'] - latest['SPY_MA']) / latest['SPY']) * 100
    # 2. QQQ drop to Mom Ref
    dist_qqq_mom = ((latest['QQQ'] - latest['QQQ_MOM_Ref']) / latest['QQQ']) * 100
    # The closest threat
    dist_to_flip = min(dist_spy_ma, dist_qqq_mom)
else:
    # Bear mode. How much rise to become Bull?
    # We need BOTH to be true, so we need the larger distance
    dist_spy_ma = ((latest['SPY_MA'] - latest['SPY']) / latest['SPY']) * 100
    dist_qqq_mom = ((latest['QQQ_MOM_Ref'] - latest['QQQ']) / latest['QQQ']) * 100
    dist_to_flip = max(dist_spy_ma, dist_qqq_mom)

# ==========================================
# 🖥️ DASHBOARD HEADER
# ==========================================

st.markdown(f"""
<div style='text-align: center; border-bottom: 2px solid #00ffff; padding-bottom: 10px; margin-bottom: 20px;'>
    <h1 style='margin:0; letter-spacing: 5px;'>🐼 PANDA TACTICAL COMMAND</h1>
    <p style='font-family: Share Tech Mono; color: #00ff00;'>DATA SYNC: {curr_date.strftime('%Y-%m-%d')} | SYSTEM: ONLINE</p>
</div>
""", unsafe_allow_html=True)

# === TOP METRICS BAR (SPY, QQQ, VIX, DAYS) ===
m1, m2, m3, m4 = st.columns(4)

with m1:
    delta = (latest['SPY'] - prev['SPY']) / prev['SPY'] * 100
    st.metric("SPY 500", f"${latest['SPY']:.2f}", f"{delta:+.2f}%")

with m2:
    delta = (latest['QQQ'] - prev['QQQ']) / prev['QQQ'] * 100
    st.metric("QQQ TECH", f"${latest['QQQ']:.2f}", f"{delta:+.2f}%")

with m3:
    delta = (latest['VIX'] - prev['VIX']) / prev['VIX'] * 100
    st.metric("VIX FEAR", f"{latest['VIX']:.2f}", f"{delta:+.2f}%", delta_color="inverse")

with m4:
    color = "#ff0055" if days_to_rebalance == 0 else "#00ffff"
    st.markdown(f"""
    <div style='text-align: center;'>
        <p style='margin:0; font-family: Share Tech Mono; color: #888;'>REBALANCE COUNTDOWN</p>
        <p style='margin:0; font-family: Orbitron; font-size: 2rem; color: {color};'>T-{days_to_rebalance} DAYS</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 🎴 战术卡片 (修复版)
# ==========================================

c1, c2, c3 = st.columns(3)

# 辅助函数：去除缩进，防止被识别为代码块
def clean_html(html_str):
    return html_str.replace("\n    ", "\n").replace("\n\t", "\n").strip()

# === 卡片 1: 熔断监测 (MELTDOWN) ===
with c1:
    border_c = "#ff0055" if is_meltdown else "#00ffff"
    status_text = "🚨 已熔断 (EMERGENCY)" if is_meltdown else "🟢 正常 (SECURE)"
    
    # 构建无缩进的 HTML
    html_content = f"""
<div class='tactical-card-base scanline card-1' style='border-color: {border_c};'>
<style>.card-1::before {{ background-image: url('data:image/png;base64,{MELTDOWN_IMAGE}'); }}</style>
<div class='card-content'>
<div class='card-title' style='color: {border_c};'>☢️ 熔断监测 (MELTDOWN)</div>
<div class='card-data'>
<div>当前回撤: <span style='color: #ff0055;'>{current_dd_pct*100:.2f}%</span></div>
<div style='margin-top: 5px; border-top: 1px dashed #555; padding-top:5px;'>触发阈值: {cb_target_pct*100:.1f}%</div>
<div style='font-size: 1.2rem; color: #00ffff; margin-top: 10px;'>离熔断触发还差: <br><span style='font-size: 1.8rem; color: #ff0055;'>{dist_to_meltdown:.2f}%</span> 跌幅</div>
</div>
<div class='card-status' style='color: {border_c};'>{status_text}</div>
</div>
</div>
"""
    st.markdown(clean_html(html_content), unsafe_allow_html=True)

# === 卡片 2: 敢死队 (SQUAD) ===
with c2:
    if is_attack:
        state_text = "🔴 突击 (ATTACK)"
        state_color = "#ff0055"
        bg_img = ATTACK_IMAGE
        current_label = "当前 RSI"
        current_val = f"{latest['RSI']:.1f}"
        target_label = "RSI 退出阈值"
        target_val = "30.0"
        dist_label = "状态确认"
        dist_val = "已击穿"
        dist_unit = ""
    else:
        state_text = "🟡 休整 (REST)"
        state_color = "#ffa500" if dist_to_lower < 2.0 else "#00ff00"
        bg_img = REST_IMAGE
        current_label = "当前价格 (QQQ)"
        current_val = f"${price_qqq:.2f}"
        target_label = "下轨触发价"
        target_val = f"${lower_band:.2f}"
        dist_label = "离突击区还差"
        dist_val = f"{dist_to_lower:.2f}%"
        dist_unit = "跌幅"

    html_content = f"""
<div class='tactical-card-base scanline card-2' style='border-color: {state_color};'>
<style>.card-2::before {{ background-image: url('data:image/png;base64,{bg_img}'); }}</style>
<div class='card-content'>
<div class='card-title' style='color: {state_color};'>🏴‍☠️ 敢死队 (SQUAD)</div>
<div class='card-data'>
<div>{current_label}: <span style='color: {state_color};'>{current_val}</span></div>
<div style='margin-top: 5px; border-top: 1px dashed #555; padding-top:5px;'>{target_label}: {target_val}</div>
<div style='font-size: 1.2rem; color: #00ffff; margin-top: 10px;'>{dist_label}: <br><span style='font-size: 1.8rem; color: {state_color};'>{dist_val}</span> {dist_unit}</div>
</div>
<div class='card-status' style='color: {state_color};'>{state_text}</div>
</div>
</div>
"""
    st.markdown(clean_html(html_content), unsafe_allow_html=True)

# === 卡片 3: 熊猫主力 (PANDA FORCE) ===
with c3:
    if is_bull:
        state_text = "🐂 满仓 (LNAS)"
        state_color = "#00ff00"
        bg_img = BULL_IMAGE
        current_label = "当前趋势"
        current_val = "多头排列"
        target_label = "反转条件"
        target_val = "跌破 MA/MOM"
        dist_label = "离转熊还差 (安全垫)"
        dist_val = f"{dist_to_flip:.2f}%"
        dist_unit = "跌幅"
        dist_color = "#00ff00"
    else:
        state_text = "🐻 空仓 (CASH)"
        state_color = "#00bfff"
        bg_img = BEAR_IMAGE
        current_label = "当前趋势"
        current_val = "空头/震荡"
        target_label = "反转条件"
        target_val = "突破 MA & MOM"
        dist_label = "离转牛还差 (需上涨)"
        dist_val = f"{dist_to_flip:.2f}%"
        dist_unit = "涨幅"
        dist_color = "#ff0055"

    html_content = f"""
<div class='tactical-card-base scanline card-3' style='border-color: {state_color};'>
<style>.card-3::before {{ background-image: url('data:image/png;base64,{bg_img}'); }}</style>
<div class='card-content'>
<div class='card-title' style='color: {state_color};'>🐼 熊猫主力 (MAIN)</div>
<div class='card-data'>
<div>{current_label}: <span style='color: {state_color};'>{current_val}</span></div>
<div style='margin-top: 5px; border-top: 1px dashed #555; padding-top:5px;'>{target_label}: {target_val}</div>
<div style='font-size: 1.2rem; color: #00ffff; margin-top: 10px;'>{dist_label}: <br><span style='font-size: 1.8rem; color: {dist_color};'>{dist_val}</span> {dist_unit}</div>
</div>
<div class='card-status' style='color: {state_color};'>{state_text}</div>
</div>
</div>
"""
    st.markdown(clean_html(html_content), unsafe_allow_html=True)

# ==========================================
# 📉 LOCKED CHART (DO NOT TOUCH)
# ==========================================

st.markdown("""
<div style='background: rgba(0,255,255,0.05); border: 1px solid #00ffff; padding: 5px; margin-bottom: 5px;'>
    <p style='font-family: Orbitron; color: #00ffff; text-align: center; margin: 0; font-size: 1rem;'>
        ▸ TACTICAL CHART DISPLAY ◂
    </p>
</div>
""", unsafe_allow_html=True)

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])

# Main Price & Bands
fig.add_trace(go.Scatter(x=df.index, y=df['QQQ'], mode='lines', name='QQQ', line=dict(color='#00ffff', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 255, 0.1)'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['Lower_Band'], mode='lines', name='Buy Zone', line=dict(color='#ff0055', width=1, dash='dot')), row=1, col=1)

# Signals
sq_signals = df[(df['QQQ'] < df['Lower_Band']) & (df['RSI'] < SQ_RSI_ENTRY)]
if not sq_signals.empty:
    fig.add_trace(go.Scatter(x=sq_signals.index, y=sq_signals['QQQ'], mode='markers', name='BUY SIGNAL', marker=dict(color='#00ff00', size=10, symbol='triangle-up', line=dict(color='#fff', width=1))), row=1, col=1)

# RSI
fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI', line=dict(color='#ff00ff', width=2)), row=2, col=1)
fig.add_hline(y=30, line_width=1, line_dash="dash", line_color="#00ff00", row=2, col=1)
fig.add_hline(y=70, line_width=1, line_dash="dash", line_color="#ff0055", row=2, col=1)

fig.update_layout(height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(10, 14, 39, 0.8)', margin=dict(l=10, r=10, t=20, b=10), font=dict(family='Share Tech Mono', color='#888', size=10), showlegend=False)
fig.update_xaxes(showgrid=True, gridcolor='rgba(0,255,255,0.1)')
fig.update_yaxes(showgrid=True, gridcolor='rgba(0,255,255,0.1)')

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
