"""
🐼 PANDA TACTICAL COMMAND CENTER - Enhanced Edition
====================================================
Cyberpunk dashboard with dynamic visual status indicators
Fixed Version: Auto-detects image paths and handles missing files gracefully.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pandas.tseries.offsets import MonthEnd
from datetime import datetime
import base64
import os  # 新增：用于检测文件路径

# ==========================================
# 🎨 PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="PANDA TACTICAL COMMAND",
    page_icon="🐼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🖼️ LOAD IMAGES AS BASE64 (ROBUST VERSION)
# ==========================================

def load_image_as_base64(filename):
    """
    尝试从多个位置加载图片，并转换为 base64。
    如果找不到图片，返回一个透明像素，防止程序崩溃。
    """
    # 定义程序会去寻找图片的路径列表
    possible_paths = [
        os.path.join("images", filename),  # 优先找 images 文件夹
        filename,                          # 其次找根目录
        os.path.join(os.getcwd(), "images", filename), # 绝对路径尝试
    ]

    for filepath in possible_paths:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    # 找到文件，成功返回
                    return base64.b64encode(f.read()).decode()
            except Exception as e:
                # 文件存在但读取失败
                print(f"Error reading {filepath}: {e}")
                continue
    
    # 如果所有路径都找不到文件，打印警告并返回透明像素（防止报错）
    print(f"⚠️ Warning: Image {filename} not found in expected paths.")
    st.toast(f"⚠️ Warning: Could not find image: {filename}", icon="⚠️")
    return "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" # 1x1透明GIF

# 加载战术图片 (只需要写文件名即可，程序会自动找路径)
REST_IMAGE = load_image_as_base64('rest.png')
ATTACK_IMAGE = load_image_as_base64('attack.png')

# ==========================================
# 💎 CYBERPUNK CSS INJECTION
# ==========================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
    
    /* ===== HIDE STREAMLIT DEFAULTS ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* ===== GLOBAL DARK CYBERPUNK THEME ===== */
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1a2e 50%, #16213e 100%);
        background-attachment: fixed;
    }
    
    /* Animated grid overlay */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: 
            linear-gradient(rgba(0, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 255, 0.03) 1px, transparent 1px);
        background-size: 50px 50px;
        pointer-events: none;
        z-index: 0;
        animation: gridPulse 4s ease-in-out infinite;
    }
    
    @keyframes gridPulse {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 0.6; }
    }
    
    /* ===== TYPOGRAPHY ===== */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        position: relative;
        z-index: 1;
    }
    
    h1, h2, h3, .stMarkdown p {
        font-family: 'Orbitron', monospace !important;
        color: #00ffff !important;
        text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
    }
    
    h1 {
        font-size: 3rem !important;
        font-weight: 900 !important;
        letter-spacing: 4px;
        background: linear-gradient(90deg, #00ffff, #ff00ff, #00ffff);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: gradientShift 3s linear infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% center; }
        100% { background-position: 200% center; }
    }
    
    /* ===== METRIC CARDS ===== */
    [data-testid="stMetricValue"] {
        font-family: 'Orbitron', monospace !important;
        font-size: 2.2rem !important;
        font-weight: 900 !important;
        color: #00ff00 !important;
        text-shadow: 0 0 20px rgba(0, 255, 0, 0.8);
    }
    
    [data-testid="stMetricLabel"] {
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 0.75rem !important;
        color: #00ffff !important;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    /* ===== ALERT BOXES ===== */
    .stAlert {
        border: 2px solid;
        border-radius: 0;
        font-family: 'Share Tech Mono', monospace !important;
        backdrop-filter: blur(10px);
        animation: borderPulse 2s ease-in-out infinite;
    }
    
    @keyframes borderPulse {
        0%, 100% { box-shadow: 0 0 10px rgba(255, 0, 0, 0.3); }
        50% { box-shadow: 0 0 25px rgba(255, 0, 0, 0.6); }
    }
    
    /* ===== PROGRESS BAR ===== */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #00ffff, #ff00ff);
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.6);
    }
    
    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0e27 0%, #1a1a2e 100%);
        border-right: 2px solid #00ffff;
        box-shadow: 5px 0 30px rgba(0, 255, 255, 0.2);
    }
    
    /* ===== INPUT FIELDS ===== */
    .stNumberInput input {
        background: rgba(0, 0, 0, 0.6) !important;
        border: 1px solid #00ffff !important;
        color: #00ff00 !important;
        font-family: 'Share Tech Mono', monospace !important;
    }
    
    /* ===== TACTICAL CARD WITH BACKGROUND IMAGE ===== */
    .tactical-card {
        position: relative;
        background: rgba(0, 0, 0, 0.7);
        border: 2px solid;
        padding: 1.5rem;
        height: 320px;
        overflow: hidden;
        box-shadow: 0 0 30px rgba(255, 0, 255, 0.2);
    }
    
    .tactical-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-size: cover;
        background-position: center;
        opacity: 0.35;
        filter: brightness(0.8);
        z-index: 0;
    }
    
    .tactical-card-content {
        position: relative;
        z-index: 1;
    }
    
    .scanline {
        position: relative;
        overflow: hidden;
    }
    
    .scanline::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(
            to bottom,
            transparent 0%,
            rgba(0, 255, 255, 0.1) 50%,
            transparent 100%
        );
        animation: scan 4s linear infinite;
        pointer-events: none;
    }
    
    @keyframes scan {
        0% { transform: translateY(-100%); }
        100% { transform: translateY(100%); }
    }
    
    /* ===== GLITCH EFFECT ===== */
    .glitch {
        animation: glitch 1s infinite;
    }
    
    @keyframes glitch {
        0%, 90%, 100% { transform: translate(0); }
        92% { transform: translate(-2px, 2px); }
        94% { transform: translate(2px, -2px); }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ TACTICAL CONTROL PANEL
# ==========================================

with st.sidebar:
    st.markdown("# ⚙️ CONTROL PANEL")
    st.markdown("---")
    
    st.markdown("### 🐼 PANDA PROTOCOLS")
    PANDA_MA = st.number_input("SPY MA FILTER", value=200)
    PANDA_MOM = st.number_input("QQQ MOMENTUM", value=95)
    CB_DROP = st.number_input("CIRCUIT BREAKER", value=0.075, step=0.005, format="%.3f")
    
    st.markdown("---")
    st.markdown("### 🏴‍☠️ SQUAD PARAMETERS")
    SQ_BB_N = st.number_input("BB PERIOD", value=20)
    SQ_BB_STD = st.number_input("BB DEVIATION", value=2.5)
    SQ_RSI_ENTRY = st.number_input("RSI TRIGGER", value=30)
    
    st.markdown("---")
    st.markdown(f"""
    <div style='text-align: center; padding: 1rem; background: rgba(0,255,255,0.1); 
                border: 1px solid #00ffff;'>
        <p style='font-family: Share Tech Mono; font-size: 0.7rem; color: #00ffff; margin: 0;'>
            SYSTEM ONLINE<br>
            <span style='color: #00ff00;'>● ACTIVE</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 📥 DATA CORE
# ==========================================

@st.cache_data(ttl=1800)
def get_market_data():
    tickers = ['SPY', 'QQQ']
    data = yf.download(tickers, period="1y", progress=False, auto_adjust=True)
    
    if isinstance(data.columns, pd.MultiIndex):
        df = data['Close'].copy()
    else:
        df = data.copy()
    
    df = df.dropna()
    
    df['SPY_MA'] = df['SPY'].rolling(PANDA_MA).mean()
    df['QQQ_MOM_Ref'] = df['QQQ'].shift(PANDA_MOM)
    
    spy_max = df['SPY'].rolling(5).max()
    df['Drawdown'] = (df['SPY'] / spy_max) - 1
    
    sma = df['QQQ'].rolling(SQ_BB_N).mean()
    std = df['QQQ'].rolling(SQ_BB_N).std()
    df['Lower_Band'] = sma - (SQ_BB_STD * std)
    
    delta = df['QQQ'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

try:
    df = get_market_data()
    # Ensure we have data before proceeding
    if df.empty:
        st.error("⚠️ Data download returned empty. Market may be closed or ticker symbol error.")
        st.stop()
        
    latest = df.iloc[-1]
    curr_date = df.index[-1]
except Exception as e:
    st.error(f"⚠️ SYSTEM FAILURE: {e}")
    st.stop()

# ==========================================
# 🧠 STRATEGY LOGIC
# ==========================================

month_end = curr_date + MonthEnd(0)
days_to_end = (month_end - curr_date).days
is_month_end = days_to_end == 0

panda_bull = latest['SPY'] > latest['SPY_MA'] and latest['QQQ'] > latest['QQQ_MOM_Ref']
panda_cb = latest['Drawdown'] < -CB_DROP

dist_val = latest['QQQ'] - latest['Lower_Band']
dist_pct = (dist_val / latest['QQQ']) * 100
sq_fire = latest['QQQ'] < latest['Lower_Band'] and latest['RSI'] < SQ_RSI_ENTRY
sq_alert = dist_pct < 2.0

# ==========================================
# 🎮 COMMAND CENTER INTERFACE
# ==========================================

st.markdown(f"""
<div style='text-align: center; padding: 2rem 0 1rem 0;'>
    <h1 class='glitch'>🐼 PANDA TACTICAL COMMAND</h1>
    <p style='font-family: Share Tech Mono; color: #00ffff; font-size: 0.9rem; letter-spacing: 3px;'>
        LAST SYNC: {curr_date.strftime('%Y.%m.%d')} | 
        NETWORK: <span style='color: #00ff00;'>SECURED</span> | 
        STATUS: <span style='color: #ff00ff;'>OPERATIONAL</span>
    </p>
</div>
""", unsafe_allow_html=True)

# === QUICK STATUS BAR ===
col_q1, col_q2, col_q3, col_q4 = st.columns(4)

with col_q1:
    spy_delta = df['SPY'].diff().iloc[-1]
    st.metric("SPY INDEX", f"${latest['SPY']:.2f}", f"{spy_delta:+.2f}")

with col_q2:
    qqq_delta = df['QQQ'].diff().iloc[-1]
    st.metric("QQQ INDEX", f"${latest['QQQ']:.2f}", f"{qqq_delta:+.2f}")

with col_q3:
    st.metric("RSI LEVEL", f"{latest['RSI']:.1f}", 
              "OVERSOLD" if latest['RSI'] < 30 else "NORMAL",
              delta_color="inverse" if latest['RSI'] < 30 else "normal")

with col_q4:
    vol_change = ((df['QQQ'].iloc[-1] / df['QQQ'].iloc[-2] - 1) * 100)
    st.metric("VOLATILITY", f"{abs(vol_change):.2f}%", f"{vol_change:+.2f}%")

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("""
<div style='background: rgba(0,255,255,0.05); border: 2px solid #00ffff; 
            padding: 0.5rem; margin-bottom: 2rem; box-shadow: 0 0 20px rgba(0,255,255,0.2);'>
    <p style='font-family: Orbitron; color: #00ffff; text-align: center; 
              margin: 0; font-size: 1.1rem; letter-spacing: 3px;'>
        ▸ TACTICAL STATUS GRID ◂
    </p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

# === CARD 1: REBALANCE ===
with col1:
    st.markdown("""
    <div class='scanline' style='background: rgba(0,0,0,0.6); border: 2px solid #00ffff; 
                padding: 1.5rem; height: 320px; box-shadow: 0 0 30px rgba(0,255,255,0.2);'>
        <p style='font-family: Orbitron; color: #00ffff; font-size: 1.2rem; 
                  margin: 0 0 1rem 0; text-align: center; letter-spacing: 2px;'>
            🗓️ REBALANCE PROTOCOL
        </p>
    """, unsafe_allow_html=True)
    
    if is_month_end:
        st.markdown("""
        <div style='background: rgba(255,0,0,0.2); border: 2px solid #ff0055; 
                    padding: 1rem; text-align: center;'>
            <p style='font-family: Orbitron; color: #ff0055; font-size: 1.5rem; 
                      margin: 0; font-weight: 900;'>
                ⚠️ EXECUTE NOW
            </p>
            <p style='font-family: Share Tech Mono; color: #ff0055; 
                      font-size: 0.8rem; margin: 0.5rem 0 0 0;'>
                IMMEDIATE ACTION REQUIRED
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        progress = max(0, min(100, int((1 - days_to_end/30) * 100)))
        st.markdown(f"""
        <p style='font-family: Share Tech Mono; color: #00ff00; 
                  font-size: 1.8rem; text-align: center; margin: 1rem 0;'>
            T-{days_to_end} DAYS
        </p>
        """, unsafe_allow_html=True)
        st.progress(progress, text=f"CYCLE PROGRESS: {progress}%")
    
    st.markdown("</div>", unsafe_allow_html=True)

# === CARD 2: SUICIDE SQUAD WITH DYNAMIC BACKGROUND ===
with col2:
    # Determine which image to use based on status
    if sq_fire:
        bg_image = ATTACK_IMAGE
        border_color = "#ff0055"
        glow_color = "255, 0, 85"
    elif sq_alert:
        bg_image = ATTACK_IMAGE
        border_color = "#ffa500"
        glow_color = "255, 165, 0"
    else:
        bg_image = REST_IMAGE
        border_color = "#00ff00"
        glow_color = "0, 255, 0"
    
    st.markdown(f"""
    <div class='tactical-card scanline' style='border-color: {border_color}; 
                box-shadow: 0 0 30px rgba({glow_color}, 0.3);'>
        <style>
            .tactical-card::before {{
                background-image: url('data:image/png;base64,{bg_image}');
            }}
        </style>
        <div class='tactical-card-content'>
            <p style='font-family: Orbitron; color: #ff00ff; font-size: 1.2rem; 
                      margin: 0 0 1rem 0; text-align: center; letter-spacing: 2px;
                      text-shadow: 0 0 10px rgba(255, 0, 255, 0.8);'>
                🏴‍☠️ SUICIDE SQUAD
            </p>
    """, unsafe_allow_html=True)
    
    if sq_fire:
        st.markdown("""
            <div style='background: rgba(255,0,0,0.85); border: 2px solid #ff0055; 
                        padding: 1.5rem; text-align: center; margin-top: 2rem;
                        box-shadow: 0 0 30px rgba(255, 0, 85, 0.5);'>
                <p style='font-family: Orbitron; color: #ffffff; font-size: 2rem; 
                          margin: 0; font-weight: 900; text-shadow: 0 0 20px #ff0055;'>
                    🔴 DEPLOY
                </p>
                <p style='font-family: Share Tech Mono; color: #ffffff; 
                          font-size: 1.5rem; margin: 0.8rem 0; font-weight: 900;'>
                    BUY QLD
                </p>
                <p style='font-family: Share Tech Mono; color: #ffff00; 
                          font-size: 0.8rem; margin: 0;'>
                    SIGNAL: ACTIVE
                </p>
            </div>
        """, unsafe_allow_html=True)
    elif sq_alert:
        st.markdown(f"""
            <div style='background: rgba(255,165,0,0.85); border: 2px solid #ffa500; 
                        padding: 1.5rem; text-align: center; margin-top: 2rem;
                        box-shadow: 0 0 30px rgba(255, 165, 0, 0.5);'>
                <p style='font-family: Orbitron; color: #000000; font-size: 1.8rem; 
                          margin: 0; font-weight: 900;'>
                    🟡 ALERT
                </p>
                <p style='font-family: Share Tech Mono; color: #000000; 
                          font-size: 2rem; margin: 0.8rem 0; font-weight: 900;'>
                    {dist_pct:.2f}%
                </p>
                <p style='font-family: Share Tech Mono; color: #000000; 
                          font-size: 0.8rem; margin: 0;'>
                    PROXIMITY WARNING
                </p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style='background: rgba(0,255,0,0.85); border: 2px solid #00ff00; 
                        padding: 1.5rem; text-align: center; margin-top: 2rem;
                        box-shadow: 0 0 30px rgba(0, 255, 0, 0.5);'>
                <p style='font-family: Orbitron; color: #000000; font-size: 1.8rem; 
                          margin: 0; font-weight: 900;'>
                    🟢 STANDBY
                </p>
                <p style='font-family: Share Tech Mono; color: #000000; 
                          font-size: 2rem; margin: 0.8rem 0; font-weight: 900;'>
                    +{dist_pct:.2f}%
                </p>
                <p style='font-family: Share Tech Mono; color: #000000; 
                          font-size: 0.8rem; margin: 0;'>
                    RSI: {latest['RSI']:.1f} | SAFE
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div></div>", unsafe_allow_html=True)

# === CARD 3: PANDA FORCE ===
with col3:
    st.markdown("""
    <div class='scanline' style='background: rgba(0,0,0,0.6); border: 2px solid #00ff00; 
                padding: 1.5rem; height: 320px; box-shadow: 0 0 30px rgba(0,255,0,0.2);'>
        <p style='font-family: Orbitron; color: #00ff00; font-size: 1.2rem; 
                  margin: 0 0 1rem 0; text-align: center; letter-spacing: 2px;'>
            🐼 PANDA FORCE
        </p>
    """, unsafe_allow_html=True)
    
    if panda_cb:
        st.markdown(f"""
        <div style='background: rgba(255,0,0,0.3); border: 2px solid #ff0055; 
                    padding: 1rem; text-align: center;'>
            <p style='font-family: Orbitron; color: #ff0055; font-size: 1.5rem; 
                      margin: 0; font-weight: 900;'>
                🚨 EMERGENCY
            </p>
            <p style='font-family: Share Tech Mono; color: #ffffff; 
                      font-size: 1.2rem; margin: 0.5rem 0;'>
                SWITCH TO QQQ
            </p>
            <p style='font-family: Share Tech Mono; color: #ff0055; 
                      font-size: 0.9rem; margin: 0.5rem 0 0 0;'>
                DROP: {latest['Drawdown']*100:.2f}%
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        if panda_bull:
            st.markdown("""
            <div style='background: rgba(0,255,0,0.2); border: 2px solid #00ff00; 
                        padding: 1rem; text-align: center;'>
                <p style='font-family: Orbitron; color: #00ff00; font-size: 1.5rem; 
                          margin: 0; font-weight: 900;'>
                    🐂 BULL MODE
                </p>
                <p style='font-family: Share Tech Mono; color: #ffffff; 
                          font-size: 1.8rem; margin: 0.5rem 0; font-weight: 900;'>
                    QLD (2X)
                </p>
                <p style='font-family: Share Tech Mono; color: #00ff00; 
                          font-size: 0.7rem; margin: 0.5rem 0 0 0;'>
                    AGGRESSIVE STANCE
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background: rgba(0,191,255,0.1); border: 2px solid #00bfff; 
                        padding: 1rem; text-align: center;'>
                <p style='font-family: Orbitron; color: #00bfff; font-size: 1.5rem; 
                          margin: 0; font-weight: 700;'>
                    🐻 BEAR MODE
                </p>
                <p style='font-family: Share Tech Mono; color: #ffffff; 
                          font-size: 1.8rem; margin: 0.5rem 0; font-weight: 900;'>
                    CASH (0X)
                </p>
                <p style='font-family: Share Tech Mono; color: #00bfff; 
                          font-size: 0.7rem; margin: 0.5rem 0 0 0;'>
                    DEFENSIVE POSITION
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 📈 TACTICAL CHART
# ==========================================

st.markdown("""
<div style='background: rgba(0,255,255,0.05); border: 2px solid #00ffff; 
            padding: 0.5rem; margin-bottom: 1rem;'>
    <p style='font-family: Orbitron; color: #00ffff; text-align: center; 
              margin: 0; font-size: 1.1rem; letter-spacing: 3px;'>
        ▸ HOLOGRAPHIC TACTICAL DISPLAY ◂
    </p>
</div>
""", unsafe_allow_html=True)

fig = make_subplots(
    rows=2, cols=1, 
    shared_xaxes=True,
    vertical_spacing=0.08,
    row_heights=[0.7, 0.3]
)

fig.add_trace(
    go.Scatter(
        x=df.index, y=df['QQQ'], mode='lines', name='QQQ',
        line=dict(color='#00ffff', width=2),
        fill='tozeroy', fillcolor='rgba(0, 255, 255, 0.1)'
    ), row=1, col=1
)

fig.add_trace(
    go.Scatter(
        x=df.index, y=df['Lower_Band'], mode='lines', name='Panic Zone',
        line=dict(color='#ff0055', width=2, dash='dot')
    ), row=1, col=1
)

sq_signals = df[(df['QQQ'] < df['Lower_Band']) & (df['RSI'] < SQ_RSI_ENTRY)]
if len(sq_signals) > 0:
    fig.add_trace(
        go.Scatter(
            x=sq_signals.index, y=sq_signals['QQQ'], mode='markers', name='BUY',
            marker=dict(color='#00ff00', size=12, symbol='triangle-up',
                       line=dict(color='#ffffff', width=2))
        ), row=1, col=1
    )

fig.add_trace(
    go.Scatter(
        x=df.index, y=df['RSI'], mode='lines', name='RSI',
        line=dict(color='#ff00ff', width=2),
        fill='tozeroy', fillcolor='rgba(255, 0, 255, 0.15)'
    ), row=2, col=1
)

fig.add_hline(y=30, line_width=2, line_dash="dash", line_color="#00ff00", row=2, col=1)
fig.add_hline(y=70, line_width=2, line_dash="dash", line_color="#ff0055", row=2, col=1)

fig.update_layout(
    height=550,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(10, 14, 39, 0.8)',
    margin=dict(l=10, r=10, t=30, b=10),
    font=dict(family='Share Tech Mono', color='#00ffff', size=10),
    showlegend=False,
    hovermode='x unified'
)

fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0, 255, 255, 0.1)',
                 showline=True, linewidth=2, linecolor='#00ffff')
fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0, 255, 255, 0.1)',
                 showline=True, linewidth=2, linecolor='#00ffff')

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ==========================================
# 📊 DATA TERMINAL
# ==========================================

with st.expander("🔍 ACCESS RAW DATA TERMINAL"):
    st.markdown("""
    <div style='background: rgba(0,0,0,0.8); border: 1px solid #00ff00; padding: 1rem;'>
        <p style='font-family: Share Tech Mono; color: #00ff00; margin: 0; font-size: 0.8rem;'>
            > TACTICAL DATA STREAM | LAST 10 RECORDS
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    cols = ['SPY', 'QQQ', 'RSI', 'Lower_Band', 'Drawdown']
    display_df = df[cols].tail(10).copy()
    
    def highlight_critical(val):
        return 'background-color: rgba(255, 0, 85, 0.3); color: #ff0055;' if val < 30 else ''
    
    styled_df = display_df.style.format({
        'SPY': '${:.2f}', 'QQQ': '${:.2f}', 'RSI': '{:.1f}',
        'Lower_Band': '${:.2f}', 'Drawdown': '{:.2%}'
    }).applymap(highlight_critical, subset=['RSI'])
    
    st.dataframe(styled_df, use_container_width=True)

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; padding: 2rem; background: rgba(0,0,0,0.6); 
            border-top: 2px solid #00ffff;'>
    <p style='font-family: Share Tech Mono; color: #00ffff; font-size: 0.7rem; 
              margin: 0; letter-spacing: 2px;'>
        🐼 PANDA TACTICAL COMMAND CENTER | v2.1 ENHANCED EDITION<br>
        <span style='color: #00ff00;'>● SYSTEM OPERATIONAL</span> | 
        <span style='color: #ff00ff;'>● VISUAL INDICATORS ACTIVE</span>
    </p>
</div>
""", unsafe_allow_html=True)
