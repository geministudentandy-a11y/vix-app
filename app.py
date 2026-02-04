"""
🐼 PANDA TACTICAL COMMAND CENTER - Final Fix Edition
====================================================
Cyberpunk dashboard with dynamic visual status indicators
Fixes: HTML indentation issues & Variable scope errors
"""

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
# 🎨 页面配置
# ==========================================

st.set_page_config(
    page_title="PANDA COMMAND",
    page_icon="🐼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🖼️ 图片加载器 (智能路径识别)
# ==========================================

def load_image_as_base64(filename):
    """
    尝试从多个位置加载图片，并转换为 base64。
    如果找不到图片，返回一个透明像素，防止程序崩溃。
    """
    possible_paths = [
        filename,                          # 优先找根目录
        os.path.join("images", filename),  # 其次找 images 文件夹
        os.path.join(os.getcwd(), filename),
    ]

    for filepath in possible_paths:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    return base64.b64encode(f.read()).decode()
            except Exception as e:
                continue
    
    # 没找到图片时的容错处理 (1x1透明GIF)
    return "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

# === 加载所有战术图片 ===
REST_IMAGE = load_image_as_base64('rest.png')
ATTACK_IMAGE = load_image_as_base64('attack.png')
BULL_IMAGE = load_image_as_base64('Bull.png') 
BEAR_IMAGE = load_image_as_base64('Bear.png')
MELTDOWN_IMAGE = load_image_as_base64('meltdown.png')

# ==========================================
# 💎 CSS 样式系统 (Cyberpunk)
# ==========================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1a2e 50%, #16213e 100%);
        background-attachment: fixed;
    }
    
    /* 字体定义 */
    h1, h2, h3 { font-family: 'Orbitron', monospace !important; color: #00ffff !important; }
    
    /* 指标组件样式 */
    [data-testid="stMetricValue"] {
        font-family: 'Orbitron', monospace !important;
        color: #00ff00 !important;
        font-size: 1.8rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Share Tech Mono', monospace !important;
        color: #00ffff !important;
    }

    /* 战术卡片基础容器 */
    .tactical-card-base {
        position: relative;
        background: rgba(0, 0, 0, 0.85); /* 加深背景以突出文字 */
        border: 2px solid;
        padding: 1.2rem;
        height: 360px; /* 统一高度 */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        overflow: hidden;
        box-shadow: 0 0 20px rgba(0,0,0,0.6);
    }
    
    /* 背景图遮罩 */
    .tactical-card-base::before {
        content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-size: cover; background-position: center;
        opacity: 0.3; filter: brightness(0.6) contrast(1.2); z-index: 0;
    }
    
    /* 内容层 */
    .card-content { 
        position: relative; z-index: 1; text-align: center; height: 100%; 
        display: flex; flex-direction: column; justify-content: space-between; 
    }
    
    /* 卡片标题 */
    .card-title { 
        font-family: 'Orbitron'; font-weight: 900; letter-spacing: 2px; 
        font-size: 1.3rem; margin-bottom: 5px; text-shadow: 0 0 5px currentColor; 
    }
    
    /* 卡片核心数据区 (统一格式) */
    .card-data { 
        font-family: 'Share Tech Mono'; 
        font-size: 1.0rem; 
        color: #fff; 
        margin: auto 0; 
        font-weight: bold; 
        background: rgba(0,0,0,0.6); 
        padding: 15px; 
        border-radius: 6px; 
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* 底部状态栏 */
    .card-status { 
        font-family: 'Orbitron'; 
        font-size: 1.4rem; 
        font-weight: 900; 
        padding: 10px; 
        border-top: 1px solid rgba(255,255,255,0.2); 
        background: rgba(0,0,0,0.7); 
        letter-spacing: 1px;
    }

    /* 扫描线动画 */
    .scanline::after {
        content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: linear-gradient(to bottom, transparent 0%, rgba(0, 255, 255, 0.05) 50%, transparent 100%);
        animation: scan 6s linear infinite; pointer-events: none; z-index: 2;
    }
    @keyframes scan { 0% { transform: translateY(-100%); } 100% { transform: translateY(100%); } }
</style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 侧边栏控制
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
# 📥 数据核心
# ==========================================

@st.cache_data(ttl=300)
def get_market_data():
    tickers = ['SPY', 'QQQ', '^VIX']
    # 下载数据
    data = yf.download(tickers, period="2y", progress=False, group_by='ticker', auto_adjust=True)
    
    # 数据清洗与重组
    df = pd.DataFrame()
    # 处理 MultiIndex
    try:
        df['SPY'] = data['SPY']['Close']
        df['QQQ'] = data['QQQ']['Close']
        df['VIX'] = data['^VIX']['Close']
    except KeyError:
        # 兼容性回退
        if isinstance(data.columns, pd.MultiIndex):
            df['SPY'] = data.xs('SPY', axis=1, level=0)['Close']
            df['QQQ'] = data.xs('QQQ', axis=1, level=0)['Close']
            df['VIX'] = data.xs('^VIX', axis=1, level=0)['Close']
        else:
            st.error("Data structure error from Yahoo Finance.")
            st.stop()
            
    df = df.dropna()

    # 指标计算
    df['SPY_MA'] = df['SPY'].rolling(PANDA_MA).mean()
    df['QQQ_MOM_Ref'] = df['QQQ'].shift(PANDA_MOM)
    
    # 熔断回撤计算 (252天最高点)
    spy_max = df['SPY'].rolling(252).max()
    df['Drawdown'] = (df['SPY'] / spy_max) - 1
    
    # 布林带计算
    sma = df['QQQ'].rolling(SQ_BB_N).mean()
    std = df['QQQ'].rolling(SQ_BB_N).std()
    df['Lower_Band'] = sma - (SQ_BB_STD * std)
    
    # RSI 计算
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
# 🧠 逻辑引擎 (Logic Engine)
# ==========================================

# 1. 基础数据准备
price_qqq = latest['QQQ']
lower_band = latest['Lower_Band']
current_dd_pct = abs(latest['Drawdown'])

# 2. 调仓倒计时
month_end = curr_date + MonthEnd(0)
days_to_rebalance = (month_end - curr_date).days

# 3. 熔断逻辑 (Card 1)
cb_target_pct = CB_DROP
dist_to_meltdown = max(0, cb_target_pct - current_dd_pct) * 100
is_meltdown = current_dd_pct >= cb_target_pct

# 4. 敢死队逻辑 (Card 2) - 【关键：提前计算所有变量】
# 计算距离下轨的距离（百分比）
# 如果价格高于下轨，dist > 0；如果跌穿，dist < 0
dist_to_lower = ((price_qqq - lower_band) / price_qqq) * 100 

# 判断状态
is_below_band = price_qqq < lower_band
is_rsi_low = latest['RSI'] < SQ_RSI_ENTRY
is_attack = is_below_band and is_rsi_low

# 5. 熊猫主力逻辑 (Card 3)
is_bull = latest['SPY'] > latest['SPY_MA'] and latest['QQQ'] > latest['QQQ_MOM_Ref']

if is_bull:
    # 找最近的那个支撑位（跌破任意一个即转熊）
    dist_spy_ma = ((latest['SPY'] - latest['SPY_MA']) / latest['SPY']) * 100
    dist_qqq_mom = ((latest['QQQ'] - latest['QQQ_MOM_Ref']) / latest['QQQ']) * 100
    dist_to_flip = min(dist_spy_ma, dist_qqq_mom) # 最小安全垫
else:
    # 找最远的那个阻力位（突破两个才能转牛）
    dist_spy_ma = ((latest['SPY_MA'] - latest['SPY']) / latest['SPY']) * 100
    dist_qqq_mom = ((latest['QQQ_MOM_Ref'] - latest['QQQ']) / latest['QQQ']) * 100
    dist_to_flip = max(dist_spy_ma, dist_qqq_mom) # 最大阻力

# ==========================================
# 🖥️ 仪表盘头部 (Header)
# ==========================================

st.markdown(f"""
<div style='text-align: center; border-bottom: 2px solid #00ffff; padding-bottom: 10px; margin-bottom: 20px;'>
    <h1 style='margin:0; letter-spacing: 5px;'>🐼 PANDA TACTICAL COMMAND</h1>
    <p style='font-family: Share Tech Mono; color: #00ff00;'>DATA SYNC: {curr_date.strftime('%Y-%m-%d')} | SYSTEM: ONLINE</p>
</div>
""", unsafe_allow_html=True)

# === 顶部核心指标 ===
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
    # 使用紧凑 HTML 防止代码块渲染
    countdown_html = f"<div style='text-align: center;'><p style='margin:0; font-family: Share Tech Mono; color: #888;'>REBALANCE COUNTDOWN</p><p style='margin:0; font-family: Orbitron; font-size: 2rem; color: {color};'>T-{days_to_rebalance} DAYS</p></div>"
    st.markdown(countdown_html, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 🎴 战术卡片 (HTML 无缩进修复版)
# ==========================================

c1, c2, c3 = st.columns(3)

# 辅助函数：彻底清除 HTML 缩进，防止显示为代码块
def clean_html(html_str):
    lines = html_str.split('\n')
    cleaned = [line.strip() for line in lines if line.strip()]
    return "".join(cleaned)

# === 卡片 1: 熔断监测 (MELTDOWN) ===
with c1:
    border_c = "#ff0055" if is_meltdown else "#00ffff"
    status_text = "🚨 已熔断 (EMERGENCY)" if is_meltdown else "🟢 正常 (SECURE)"
    
    html_1 = f"""
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
    st.markdown(clean_html(html_1), unsafe_allow_html=True)

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
        # 此时 dist_to_lower 已经在上面逻辑引擎计算好了，不会报错
        state_color = "#ffa500" if dist_to_lower < 2.0 else "#00ff00"
        bg_img = REST_IMAGE
        current_label = "当前价格 (QQQ)"
        current_val = f"${price_qqq:.2f}"
        target_label = "下轨触发价"
        target_val = f"${lower_band:.2f}"
        dist_label = "离突击区还差"
        dist_val = f"{dist_to_lower:.2f}%"
        dist_unit = "跌幅"

    html_2 = f"""
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
    st.markdown(clean_html(html_2), unsafe_allow_html=True)

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

    html_3 = f"""
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
    st.markdown(clean_html(html_3), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 📉 锁定图表 (LOCKED CHART)
# ==========================================

st.markdown("""
<div style='background: rgba(0,255,255,0.05); border: 1px solid #00ffff; padding: 5px; margin-bottom: 5px;'>
    <p style='font-family: Orbitron; color: #00ffff; text-align: center; margin: 0; font-size: 1rem;'>
        ▸ TACTICAL CHART DISPLAY ◂
    </p>
</div>
""", unsafe_allow_html=True)

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])

# 主图: 价格与下轨
fig.add_trace(go.Scatter(x=df.index, y=df['QQQ'], mode='lines', name='QQQ', line=dict(color='#00ffff', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 255, 0.1)'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['Lower_Band'], mode='lines', name='Buy Zone', line=dict(color='#ff0055', width=1, dash='dot')), row=1, col=1)

# 信号标记
sq_signals = df[(df['QQQ'] < df['Lower_Band']) & (df['RSI'] < SQ_RSI_ENTRY)]
if not sq_signals.empty:
    fig.add_trace(go.Scatter(x=sq_signals.index, y=sq_signals['QQQ'], mode='markers', name='BUY SIGNAL', marker=dict(color='#00ff00', size=10, symbol='triangle-up', line=dict(color='#fff', width=1))), row=1, col=1)

# 副图: RSI
fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI', line=dict(color='#ff00ff', width=2)), row=2, col=1)
fig.add_hline(y=30, line_width=1, line_dash="dash", line_color="#00ff00", row=2, col=1)
fig.add_hline(y=70, line_width=1, line_dash="dash", line_color="#ff0055", row=2, col=1)

fig.update_layout(height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(10, 14, 39, 0.8)', margin=dict(l=10, r=10, t=20, b=10), font=dict(family='Share Tech Mono', color='#888', size=10), showlegend=False)
fig.update_xaxes(showgrid=True, gridcolor='rgba(0,255,255,0.1)')
fig.update_yaxes(showgrid=True, gridcolor='rgba(0,255,255,0.1)')

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
