"""
🐼 PANDA TACTICAL COMMAND CENTER - Final Layout Fixed
=====================================================
Layout: Vertical Stack (Matrix -> Log)
Fixes: HTML Rendering for Table & Log
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
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
# 🖼️ 图片加载器
# ==========================================
def load_image_as_base64(filename):
    possible_paths = [filename, os.path.join("images", filename), os.path.join(os.getcwd(), filename)]
    for filepath in possible_paths:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    return base64.b64encode(f.read()).decode()
            except:
                continue
    return "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

REST_IMAGE = load_image_as_base64('rest.png')
ATTACK_IMAGE = load_image_as_base64('attack.png')
BULL_IMAGE = load_image_as_base64('Bull.png') 
BEAR_IMAGE = load_image_as_base64('Bear.png')
MELTDOWN_IMAGE = load_image_as_base64('meltdown.png')

# ==========================================
# 💎 CSS 样式系统
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
    
    .stApp { background: linear-gradient(135deg, #0a0e27 0%, #1a1a2e 50%, #16213e 100%); background-attachment: fixed; }
    h1, h2, h3 { font-family: 'Orbitron', monospace !important; color: #00ffff !important; }
    
    [data-testid="stMetricValue"] { font-family: 'Orbitron'; color: #00ff00; font-size: 1.8rem; }
    [data-testid="stMetricLabel"] { font-family: 'Share Tech Mono'; color: #00ffff; }

    .tactical-card-base {
        position: relative; background: rgba(0, 0, 0, 0.85); border: 2px solid;
        padding: 1.2rem; height: 360px; display: flex; flex-direction: column;
        justify-content: space-between; overflow: hidden; box-shadow: 0 0 20px rgba(0,0,0,0.6);
    }
    .tactical-card-base::before {
        content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-size: cover; background-position: center; opacity: 0.3; filter: brightness(0.6) contrast(1.2); z-index: 0;
    }
    .card-content { position: relative; z-index: 1; text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
    .card-title { font-family: 'Orbitron'; font-weight: 900; letter-spacing: 2px; font-size: 1.3rem; margin-bottom: 5px; text-shadow: 0 0 5px currentColor; }
    .card-data { font-family: 'Share Tech Mono'; font-size: 1.0rem; color: #fff; margin: auto 0; font-weight: bold; background: rgba(0,0,0,0.6); padding: 15px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); }
    .card-status { font-family: 'Orbitron'; font-size: 1.4rem; font-weight: 900; padding: 10px; border-top: 1px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.7); letter-spacing: 1px; }
    
    .scanline::after {
        content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: linear-gradient(to bottom, transparent 0%, rgba(0, 255, 255, 0.05) 50%, transparent 100%);
        animation: scan 6s linear infinite; pointer-events: none; z-index: 2;
    }
    @keyframes scan { 0% { transform: translateY(-100%); } 100% { transform: translateY(100%); } }

    /* 表格样式优化 */
    .perf-table { width: 100%; border-collapse: collapse; color: #fff; font-family: 'Share Tech Mono'; margin-bottom: 20px; }
    .perf-table th { border-bottom: 1px solid #00ffff; color: #00ffff; padding: 12px; text-align: right; background: rgba(0,255,255,0.05); }
    .perf-table td { padding: 12px; border-bottom: 1px solid #333; text-align: right; }
    .highlight-pos { color: #00ff00; }
    .highlight-neg { color: #ff0055; }
    
    .log-container { background: rgba(0,0,0,0.4); border: 1px solid #333; padding: 15px; border-radius: 5px; }
    .log-item { border-left: 3px solid #555; padding: 8px 15px; margin-bottom: 8px; font-family: 'Share Tech Mono'; font-size: 0.95rem; background: rgba(255,255,255,0.02); }
</style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 侧边栏
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
# 📥 数据与逻辑核心 (全历史回测版)
# ==========================================
@st.cache_data(ttl=3600)
def get_data_and_backtest():
    tickers = ['SPY', 'QQQ', '^VIX']
    # 下载数据
    data = yf.download(tickers, period="25y", progress=False, group_by='ticker', auto_adjust=True)
    
    df = pd.DataFrame()
    # 兼容性处理
    try:
        df['SPY'] = data['SPY']['Close']
        df['QQQ'] = data['QQQ']['Close']
        df['VIX'] = data['^VIX']['Close']
    except:
        # 如果数据结构不同，尝试回退方法
        if isinstance(data.columns, pd.MultiIndex):
            df['SPY'] = data.xs('SPY', axis=1, level=0)['Close']
            df['QQQ'] = data.xs('QQQ', axis=1, level=0)['Close']
            df['VIX'] = data.xs('^VIX', axis=1, level=0)['Close']
        else:
            # 最后的尝试
            df['SPY'] = data['SPY']
            df['QQQ'] = data['QQQ']
            df['VIX'] = data['^VIX']
    
    df = df.dropna()

    # === 指标计算 ===
    df['SPY_MA'] = df['SPY'].rolling(PANDA_MA).mean()
    df['QQQ_MOM_Ref'] = df['QQQ'].shift(PANDA_MOM)
    
    # 回撤
    spy_max = df['SPY'].rolling(252).max()
    df['Drawdown'] = (df['SPY'] / spy_max) - 1
    
    # 布林带
    sma = df['QQQ'].rolling(SQ_BB_N).mean()
    std = df['QQQ'].rolling(SQ_BB_N).std()
    df['Lower_Band'] = sma - (SQ_BB_STD * std)
    
    # RSI
    delta = df['QQQ'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # === 回测逻辑 (Vectorized) ===
    # 1. 信号判断
    df['Signal_Bull'] = (df['SPY'] > df['SPY_MA']) & (df['QQQ'] > df['QQQ_MOM_Ref'])
    df['Signal_Squad'] = (df['QQQ'] < df['Lower_Band']) & (df['RSI'] < SQ_RSI_ENTRY)
    df['Signal_Meltdown'] = df['Drawdown'] < -CB_DROP
    
    # 2. 策略持仓判定
    conditions = [
        df['Signal_Meltdown'],  # 优先级 1: 熔断
        df['Signal_Squad'],     # 优先级 2: 敢死队
        df['Signal_Bull']       # 优先级 3: 牛市
    ]
    choices = [1, 2, 2] # 仓位系数
    df['Position'] = np.select(conditions, choices, default=0)
    
    # 3. 收益计算
    df['QQQ_Ret'] = df['QQQ'].pct_change()
    df['SPY_Ret'] = df['SPY'].pct_change()
    df['Strat_Ret'] = df['Position'].shift(1) * df['QQQ_Ret']
    df['Strat_Ret'] = df['Strat_Ret'].fillna(0)
    
    # 累计净值
    df['Strategy_Eq'] = (1 + df['Strat_Ret']).cumprod()
    df['SPY_Eq'] = (1 + df['SPY_Ret']).cumprod()

    # === 状态变更记录 ===
    status_conds = [
        df['Signal_Meltdown'],
        df['Signal_Squad'],
        df['Signal_Bull']
    ]
    status_names = ['☢️ 熔断 (1x)', '🏴‍☠️ 突击 (2x)', '🐂 满仓 (2x)']
    df['Status_Label'] = np.select(status_conds, status_names, default='🐻 空仓 (0x)')
    df['Status_Change'] = df['Status_Label'] != df['Status_Label'].shift(1)
    
    return df

try:
    df = get_data_and_backtest()
    if df.empty: st.stop()
    latest = df.iloc[-1]
    curr_date = df.index[-1]
except Exception as e:
    st.error(f"SYSTEM FAILURE: {e}")
    st.stop()

# ==========================================
# 🧠 实时逻辑计算
# ==========================================
price_qqq = latest['QQQ']
lower_band = latest['Lower_Band']
current_dd_pct = abs(latest['Drawdown'])
month_end = curr_date + MonthEnd(0)
days_to_rebalance = (month_end - curr_date).days

# 熔断
dist_to_meltdown = max(0, CB_DROP - current_dd_pct) * 100
is_meltdown = current_dd_pct >= CB_DROP

# 敢死队
dist_to_lower = ((price_qqq - lower_band) / price_qqq) * 100 
is_attack = (price_qqq < lower_band) and (latest['RSI'] < SQ_RSI_ENTRY)

# 熊猫
is_bull = (latest['SPY'] > latest['SPY_MA']) and (latest['QQQ'] > latest['QQQ_MOM_Ref'])
if is_bull:
    dist_spy_ma = ((latest['SPY'] - latest['SPY_MA']) / latest['SPY']) * 100
    dist_qqq_mom = ((latest['QQQ'] - latest['QQQ_MOM_Ref']) / latest['QQQ']) * 100
    dist_to_flip = min(dist_spy_ma, dist_qqq_mom)
else:
    dist_spy_ma = ((latest['SPY_MA'] - latest['SPY']) / latest['SPY']) * 100
    dist_qqq_mom = ((latest['QQQ_MOM_Ref'] - latest['QQQ']) / latest['QQQ']) * 100
    dist_to_flip = max(dist_spy_ma, dist_qqq_mom)

# ==========================================
# 🖥️ 头部 & 倒计时
# ==========================================
st.markdown(f"""
<div style='text-align: center; border-bottom: 2px solid #00ffff; padding-bottom: 10px; margin-bottom: 20px;'>
    <h1 style='margin:0; letter-spacing: 5px;'>🐼 PANDA TACTICAL COMMAND</h1>
    <p style='font-family: Share Tech Mono; color: #00ff00;'>DATA SYNC: {curr_date.strftime('%Y-%m-%d')} | SYSTEM: ONLINE</p>
</div>
""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
prev = df.iloc[-2]
with m1: st.metric("SPY 500", f"${latest['SPY']:.2f}", f"{(latest['SPY']-prev['SPY'])/prev['SPY']*100:+.2f}%")
with m2: st.metric("QQQ TECH", f"${latest['QQQ']:.2f}", f"{(latest['QQQ']-prev['QQQ'])/prev['QQQ']*100:+.2f}%")
with m3: st.metric("VIX FEAR", f"{latest['VIX']:.2f}", f"{(latest['VIX']-prev['VIX'])/prev['VIX']*100:+.2f}%", delta_color="inverse")
with m4:
    color = "#ff0055" if days_to_rebalance == 0 else "#00ffff"
    # 使用无缩进HTML
    st.markdown(f"<div style='text-align: center;'><p style='margin:0; font-family: Share Tech Mono; color: #888;'>REBALANCE COUNTDOWN</p><p style='margin:0; font-family: Orbitron; font-size: 2rem; color: {color};'>T-{days_to_rebalance} DAYS</p></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 🎴 战术卡片
# ==========================================
c1, c2, c3 = st.columns(3)
# 核心修复函数：去除缩进
def clean_html(html_str): 
    return "".join([line.strip() for line in html_str.split('\n') if line.strip()])

# 卡片1
with c1:
    border_c = "#ff0055" if is_meltdown else "#00ffff"
    status_text = "🚨 已熔断 (EMERGENCY)" if is_meltdown else "🟢 正常 (SECURE)"
    html_1 = f"""
    <div class='tactical-card-base scanline card-1' style='border-color: {border_c};'>
    <style>.card-1::before {{ background-image: url('data:image/png;base64,{MELTDOWN_IMAGE}'); }}</style>
    <div class='card-content'><div class='card-title' style='color: {border_c};'>☢️ 熔断监测 (MELTDOWN)</div>
    <div class='card-data'><div>当前回撤: <span style='color: #ff0055;'>{current_dd_pct*100:.2f}%</span></div>
    <div style='margin-top: 5px; border-top: 1px dashed #555; padding-top:5px;'>触发阈值: {CB_DROP*100:.1f}%</div>
    <div style='font-size: 1.2rem; color: #00ffff; margin-top: 10px;'>离熔断触发还差: <br><span style='font-size: 1.8rem; color: #ff0055;'>{dist_to_meltdown:.2f}%</span> 跌幅</div></div>
    <div class='card-status' style='color: {border_c};'>{status_text}</div></div></div>
    """
    st.markdown(clean_html(html_1), unsafe_allow_html=True)

# 卡片2
with c2:
    if is_attack:
        state_text, state_color, bg_img = "🔴 突击 (ATTACK)", "#ff0055", ATTACK_IMAGE
        dist_val, dist_unit = "已击穿", ""
    else:
        state_text, state_color, bg_img = "🟡 休整 (REST)", "#ffa500" if dist_to_lower < 2.0 else "#00ff00", REST_IMAGE
        dist_val, dist_unit = f"{dist_to_lower:.2f}%", "跌幅"
    html_2 = f"""
    <div class='tactical-card-base scanline card-2' style='border-color: {state_color};'>
    <style>.card-2::before {{ background-image: url('data:image/png;base64,{bg_img}'); }}</style>
    <div class='card-content'><div class='card-title' style='color: {state_color};'>🏴‍☠️ 敢死队 (SQUAD)</div>
    <div class='card-data'><div>当前价格: <span style='color: {state_color};'>${price_qqq:.2f}</span></div>
    <div style='margin-top: 5px; border-top: 1px dashed #555; padding-top:5px;'>下轨触发价: ${lower_band:.2f}</div>
    <div style='font-size: 1.2rem; color: #00ffff; margin-top: 10px;'>离突击区还差: <br><span style='font-size: 1.8rem; color: {state_color};'>{dist_val}</span> {dist_unit}</div></div>
    <div class='card-status' style='color: {state_color};'>{state_text}</div></div></div>
    """
    st.markdown(clean_html(html_2), unsafe_allow_html=True)

# 卡片3
with c3:
    if is_bull:
        state_text, state_color, bg_img, dist_unit_p, dist_color = "🐂 满仓 (LNAS)", "#00ff00", BULL_IMAGE, "跌幅", "#00ff00"
        dist_label = "离转熊还差 (安全垫)"
    else:
        state_text, state_color, bg_img, dist_unit_p, dist_color = "🐻 空仓 (CASH)", "#00bfff", BEAR_IMAGE, "涨幅", "#ff0055"
        dist_label = "离转牛还差 (需上涨)"
    html_3 = f"""
    <div class='tactical-card-base scanline card-3' style='border-color: {state_color};'>
    <style>.card-3::before {{ background-image: url('data:image/png;base64,{bg_img}'); }}</style>
    <div class='card-content'><div class='card-title' style='color: {state_color};'>🐼 熊猫主力 (MAIN)</div>
    <div class='card-data'><div>当前趋势: <span style='color: {state_color};'>{'多头' if is_bull else '空头'}</span></div>
    <div style='margin-top: 5px; border-top: 1px dashed #555; padding-top:5px;'>反转条件: MA/MOM</div>
    <div style='font-size: 1.2rem; color: #00ffff; margin-top: 10px;'>{dist_label}: <br><span style='font-size: 1.8rem; color: {dist_color};'>{dist_to_flip:.2f}%</span> {dist_unit_p}</div></div>
    <div class='card-status' style='color: {state_color};'>{state_text}</div></div></div>
    """
    st.markdown(clean_html(html_3), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 📊 历史回测数据矩阵 (PERFORMANCE MATRIX)
# ==========================================
st.markdown("""
<div style='background: rgba(0,255,255,0.1); border-left: 4px solid #00ffff; padding: 5px 15px; margin-top: 20px;'>
    <h3 style='margin:0; font-size: 1.2rem;'>📈 理论历史年化回报 (THEORETICAL CAGR)</h3>
</div>
""", unsafe_allow_html=True)

# 计算 CAGR
def calc_cagr_diff(years):
    days = years * 252
    if len(df) < days: return "N/A", "N/A", "N/A"
    subset = df.iloc[-days:]
    strat_total_ret = subset['Strategy_Eq'].iloc[-1] / subset['Strategy_Eq'].iloc[0] - 1
    strat_cagr = (1 + strat_total_ret) ** (1/years) - 1
    spy_total_ret = subset['SPY_Eq'].iloc[-1] / subset['SPY_Eq'].iloc[0] - 1
    spy_cagr = (1 + spy_total_ret) ** (1/years) - 1
    diff = strat_cagr - spy_cagr
    return strat_cagr, spy_cagr, diff

periods = [20, 10, 5, 1]
table_html = "<table class='perf-table'><thead><tr><th>周期 (Period)</th><th>熊猫策略 (Panda)</th><th>标普500 (SPY)</th><th>超额收益 (Alpha)</th></tr></thead><tbody>"

for p in periods:
    strat, spy, diff = calc_cagr_diff(p)
    if strat == "N/A":
        row_html = f"<tr><td>{p} YEAR</td><td>N/A</td><td>N/A</td><td>N/A</td></tr>"
    else:
        diff_class = "highlight-pos" if diff > 0 else "highlight-neg"
        diff_sign = "+" if diff > 0 else ""
        row_html = f"""
        <tr>
            <td>{p} YEAR</td>
            <td style='color: #00ffff;'>{strat*100:.2f}%</td>
            <td style='color: #aaa;'>{spy*100:.2f}%</td>
            <td class='{diff_class}'>{diff_sign}{diff*100:.2f}%</td>
        </tr>
        """
    table_html += row_html

table_html += "</tbody></table>"
# 使用 clean_html 修复白框问题
st.markdown(clean_html(table_html), unsafe_allow_html=True)
st.markdown("<p style='font-family: Share Tech Mono; font-size: 0.8rem; color: #666; margin-top: 0px;'>*注: 理论回测假设 牛市/突击=2x杠杆, 熔断=1x, 熊市=空仓. 未包含交易损耗.</p>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 📜 最近信号日志 (SIGNAL LOG) - 已移动到下方
# ==========================================
st.markdown("""
<div style='background: rgba(255,0,85,0.1); border-left: 4px solid #ff0055; padding: 5px 15px;'>
    <h3 style='margin:0; font-size: 1.2rem;'>📝 最近 10 次状态改变 (SIGNAL LOG)</h3>
</div>
""", unsafe_allow_html=True)

changes = df[df['Status_Change']].tail(10).sort_index(ascending=False)
log_html = "<div class='log-container'>"

for date, row in changes.iterrows():
    status = row['Status_Label']
    color = "#fff"
    if "满仓" in status: color = "#00ff00"
    elif "空仓" in status: color = "#00bfff"
    elif "突击" in status: color = "#ff0055"
    elif "熔断" in status: color = "#ffa500"
    
    log_html += f"""
    <div class='log-item' style='border-color: {color};'>
        <span style='color: #888;'>[{date.strftime('%Y-%m-%d')}]</span> 
        <span style='color: {color}; font-weight: bold; margin-left: 10px;'>{status}</span>
    </div>
    """

log_html += "</div>"
# 使用 clean_html 修复白框问题
st.markdown(clean_html(log_html), unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
