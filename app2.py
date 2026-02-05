"""
🐼 PANDA TACTICS v3.3 - COMMANDER EDITION
=========================================
Logic Kernel: v3.3 (Smart Takeover / Dual-Track)
UI Theme: Ultimate Visibility (High Contrast / Cyberpunk)
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
# 🎨 页面配置 & 样式
# ==========================================
st.set_page_config(
    page_title="PANDA TACTICS v3.3",
    page_icon="🐼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 加载图片 (请确保当前目录下有 images 文件夹或直接放图片)
def load_image_as_base64(filename):
    # 这里使用占位符，实际部署时请确保图片路径正确，或删除相关CSS
    return "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

# 定义图片变量 (您可以替换为真实的本地图片路径)
REST_IMAGE = load_image_as_base64('rest.png')
ATTACK_IMAGE = load_image_as_base64('attack.png')
BULL_IMAGE = load_image_as_base64('Bull.png') 
BEAR_IMAGE = load_image_as_base64('Bear.png')
MELTDOWN_IMAGE = load_image_as_base64('meltdown.png')

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
    
    .stApp { background: linear-gradient(135deg, #050510 0%, #101025 50%, #0a0f20 100%); background-attachment: fixed; }
    h1, h2, h3 { font-family: 'Orbitron', monospace !important; color: #00ffff !important; text-shadow: 0 0 10px rgba(0,255,255,0.6); }
    
    [data-testid="stMetricValue"] { font-family: 'Orbitron'; color: #00ff00; font-size: 2.2rem; text-shadow: 0 0 15px rgba(0,255,0,0.4); }
    [data-testid="stMetricLabel"] { font-family: 'Share Tech Mono'; color: #00ffff; font-size: 1.0rem; }

    /* 卡片容器 */
    .tactical-card-base {
        position: relative; 
        background: rgba(10, 16, 33, 0.6); 
        border: 2px solid;
        padding: 0; height: 380px; display: flex; flex-direction: column;
        justify-content: space-between; overflow: hidden; 
        box-shadow: 0 0 20px rgba(0,0,0,0.8);
        border-radius: 8px;
    }
    
    /* 背景图层 */
    .tactical-card-base::before {
        content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-size: cover; background-position: center;
        opacity: 0.2; /* 调低背景图透明度，保证文字清晰 */
        z-index: 0;
        filter: grayscale(80%) contrast(1.2);
    }
    
    .card-content { 
        position: relative; z-index: 1; text-align: center; height: 100%; 
        display: flex; flex-direction: column; padding: 15px;
    }
    
    .card-header {
        font-family: 'Orbitron'; font-weight: 900; letter-spacing: 2px; font-size: 1.4rem; 
        margin-bottom: 10px; text-transform: uppercase;
        border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 8px;
    }
    
    .card-body {
        flex-grow: 1; display: flex; flex-direction: column; justify-content: center;
        font-family: 'Share Tech Mono'; font-size: 1.1rem; color: #eee;
    }
    
    .card-footer {
        font-family: 'Orbitron'; font-size: 1.3rem; font-weight: 900; padding: 12px; 
        background: rgba(0,0,0,0.5); 
        border-top: 1px solid rgba(255,255,255,0.2);
        letter-spacing: 1px;
    }

    .highlight-val { font-size: 2.2rem; font-weight: bold; text-shadow: 0 0 10px currentColor; display: block; margin: 5px 0; }
    
    .perf-table { width: 100%; border-collapse: collapse; color: #fff; font-family: 'Share Tech Mono'; margin-top: 10px; }
    .perf-table th { border-bottom: 2px solid #00ffff; color: #00ffff; padding: 10px; text-align: right; }
    .perf-table td { padding: 10px; border-bottom: 1px solid #333; text-align: right; }
    .pos-val { color: #00ff00; } .neg-val { color: #ff0055; }
    
    .log-row { 
        display: flex; justify-content: space-between; align-items: center; 
        padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.1);
        font-family: 'Share Tech Mono'; font-size: 0.95rem;
    }
    .log-badge { padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; margin-left: 10px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 战术参数 (侧边栏)
# ==========================================
with st.sidebar:
    st.markdown("### 🛠️ TACTICAL SETTINGS")
    
    st.markdown("#### 🏴‍☠️ SQUAD (敢死队)")
    VIX_TRIGGER = st.number_input("VIX 触发阈值", value=35)
    WAIT_DAYS = st.number_input("企稳观察天数", value=4)
    SQUAD_POS_PCT = st.slider("敢死队仓位 %", 50, 100, 100, 10) / 100.0
    TRAIL_STOP = st.slider("移动止盈阈值 %", 10, 40, 25, 5) / 100.0
    
    st.markdown("---")
    st.markdown("#### 🐼 PANDA (主力)")
    PANDA_MA = st.number_input("SPY 均线周期", value=200)
    PANDA_MOM = st.number_input("QQQ 动量周期", value=95)
    
    st.markdown("---")
    st.markdown("#### ☢️ MELTDOWN (熔断)")
    MELTDOWN_PCT = st.number_input("熔断触发跌幅 % (负数)", value=-7.5, step=0.5) / 100.0

# ==========================================
# 🧠 核心逻辑 (v3.3 Smart Takeover)
# ==========================================
@st.cache_data(ttl=3600)
def run_strategy_engine():
    tickers = ['SPY', 'QQQ', '^VIX']
    data = yf.download(tickers, period="25y", progress=False, group_by='ticker', auto_adjust=True)
    
    df = pd.DataFrame()
    try:
        if isinstance(data.columns, pd.MultiIndex):
            try:
                df['SPY'] = data.xs('SPY', axis=1, level=0)['Close']
                df['QQQ'] = data.xs('QQQ', axis=1, level=0)['Close']
                df['VIX'] = data.xs('^VIX', axis=1, level=0)['Close']
            except:
                df['SPY'] = data['SPY']['Close']
                df['QQQ'] = data['QQQ']['Close']
                df['VIX'] = data['^VIX']['Close']
        else:
            df['SPY'] = data['SPY']
            df['QQQ'] = data['QQQ']
            df['VIX'] = data['^VIX']
    except Exception as e:
        return None, f"数据解析失败: {e}"
    
    df = df.dropna()
    
    # --- 1. 预计算指标 ---
    df['Month'] = df.index.month
    df['Is_Month_End'] = df['Month'] != df['Month'].shift(-1)
    
    df['SPY_MA'] = df['SPY'].rolling(PANDA_MA).mean()
    df['QQQ_MOM'] = df['QQQ'].shift(PANDA_MOM)
    
    spy_max = df['SPY'].rolling(252).max()
    df['Drawdown'] = (df['SPY'] / spy_max) - 1
    
    df['QLD_Price'] = (1 + df['QQQ'].pct_change() * 2).cumprod() # QLD 仿真
    df['QLD_Ret'] = df['QLD_Price'].pct_change()
    df['QQQ_Ret'] = df['QQQ'].pct_change()

    # --- 2. 事件驱动循环 (v3.3) ---
    panda_signal = 0 
    squad_state = 'IDLE' 
    squad_wait_days = 0
    squad_high = 0 
    
    positions = []      # 0=Cash, 1=QQQ, 2=QLD
    pos_pcts = []       # 仓位比例
    status_log = []     # 状态文本
    
    vals = df[['SPY', 'QQQ', 'VIX', 'Is_Month_End', 'SPY_MA', 'QQQ_MOM', 'Drawdown', 'QLD_Price']].values
    
    for i in range(len(df)):
        spy = vals[i, 0]
        qqq = vals[i, 1]
        vix = vals[i, 2]
        is_month_end = vals[i, 3]
        spy_ma = vals[i, 4]
        qqq_mom = vals[i, 5]
        dd = vals[i, 6]
        qld_price = vals[i, 7]
        
        curr_pos = 0
        curr_pct = 0.0
        curr_status = "🐻 空仓 (CASH)"
        
        is_squad_dominant = False
        
        # --- 优先级 1: 敢死队 (SQUAD) ---
        if squad_state == 'ACTIVE':
            if qld_price > squad_high: squad_high = qld_price
            
            drawdown = (squad_high - qld_price) / squad_high
            
            if drawdown >= TRAIL_STOP:
                # 触发止损，进行【智能接管判定】
                if panda_signal == 1:
                    # 豁免止损 -> 转为主力
                    squad_state = 'IDLE'
                    curr_pos = 2
                    curr_pct = 1.0 # 主力通常满仓
                    curr_status = "🐂 主力接管 (止损豁免)"
                    is_squad_dominant = True
                else:
                    # 执行止损 -> 掉落
                    squad_state = 'IDLE'
                    curr_status = "🛑 敢死队止损" # 暂存状态，后续可能变为熔断
                    is_squad_dominant = False # 掉落
            else:
                curr_pos = 2
                curr_pct = SQUAD_POS_PCT
                curr_status = f"🔫 敢死队 ({int(SQUAD_POS_PCT*100)}%)"
                is_squad_dominant = True
                
        elif squad_state == 'WAITING':
            if vix < VIX_TRIGGER:
                squad_wait_days += 1
                if squad_wait_days >= WAIT_DAYS:
                    squad_state = 'ACTIVE'
                    squad_high = qld_price
                    curr_pos = 2
                    curr_pct = SQUAD_POS_PCT
                    curr_status = "🚀 敢死队进场"
                    is_squad_dominant = True
                else:
                    curr_status = f"🟡 瞄准中 ({squad_wait_days}/{WAIT_DAYS})"
            else:
                squad_wait_days = 0
                curr_status = "🔴 恐慌持续 (VIX High)"
                
        elif squad_state == 'IDLE':
            if vix > VIX_TRIGGER:
                squad_state = 'WAITING'
                squad_wait_days = 0
                curr_status = "🔴 敢死队解锁"

        # --- 优先级 2 & 3: 熔断与主力 (掉落逻辑) ---
        if not is_squad_dominant:
            if dd < MELTDOWN_PCT:
                curr_pos = 1
                curr_pct = 1.0
                if "止损" in curr_status: curr_status += " -> ☢️ 降级防御 (1x)"
                else: curr_status = "☢️ 熔断防御 (1x)"
            else:
                if panda_signal == 1:
                    curr_pos = 2
                    curr_pct = 1.0
                    curr_status = "🐂 熊猫满仓 (2x)"
                else:
                    curr_pos = 0
                    curr_pct = 0.0
                    if "止损" in curr_status: curr_status += " -> 🐻 现金避险"
                    elif "空仓" not in curr_status and "瞄准" not in curr_status and "恐慌" not in curr_status:
                         curr_status = "🐻 趋势空仓"
        
        positions.append(curr_pos)
        pos_pcts.append(curr_pct)
        status_log.append(curr_status)
        
        # 月末更新 Panda 信号
        if is_month_end:
            panda_signal = 1 if (spy > spy_ma) and (vals[i, 1] > qqq_mom) else 0

    # --- 3. 结算 ---
    df['Pos'] = positions
    df['Pct'] = pos_pcts
    df['Status'] = status_log
    
    df['Base_Ret'] = 0.0
    df.loc[df['Pos'].shift(1)==2, 'Base_Ret'] = df['QLD_Ret']
    df.loc[df['Pos'].shift(1)==1, 'Base_Ret'] = df['QQQ_Ret']
    
    df['Strat_Ret'] = df['Base_Ret'] * df['Pct'].shift(1).fillna(0)
    df['Strategy_Eq'] = (1 + df['Strat_Ret'].fillna(0)).cumprod()
    df['SPY_Eq'] = (1 + df['SPY'].pct_change().fillna(0)).cumprod()
    
    df['Status_Change'] = df['Status'] != df['Status'].shift(1)
    
    return df, None

# 执行策略
with st.spinner('SYSTEM INITIALIZING... DECRYPTING MARKET DATA...'):
    df, error = run_strategy_engine()

if error:
    st.error(error)
    st.stop()

# 获取最新状态
latest = df.iloc[-1]
curr_date = df.index[-1]
month_end = curr_date + MonthEnd(0)
days_to_rebalance = (month_end - curr_date).days

# 判断逻辑变量
price_qqq = latest['QQQ']
curr_dd = latest['Drawdown']
is_meltdown = curr_dd < MELTDOWN_PCT
is_squad_active = "敢死队" in latest['Status']
is_panda_bull = (latest['SPY'] > latest['SPY_MA']) and (latest['QQQ'] > latest['QQQ_MOM'])

# ==========================================
# 🖥️ 仪表盘头部
# ==========================================
st.markdown(f"""
<div style='text-align: center; border-bottom: 2px solid #00ffff; padding-bottom: 10px; margin-bottom: 25px;'>
    <h1 style='margin:0; letter-spacing: 5px; font-size: 3rem;'>🐼 PANDA TACTICS <span style='font-size:1.5rem; color:#666;'>v3.3</span></h1>
    <p style='font-family: Share Tech Mono; color: #00ff00; letter-spacing: 2px;'>COMMANDER INTERFACE | DATA: {curr_date.strftime('%Y-%m-%d')} | STATUS: ONLINE</p>
</div>
""", unsafe_allow_html=True)

# 核心指标
k1, k2, k3, k4 = st.columns(4)
prev = df.iloc[-2]
with k1: st.metric("SPY (S&P 500)", f"${latest['SPY']:.2f}", f"{(latest['SPY']/prev['SPY']-1)*100:.2f}%")
with k2: st.metric("QQQ (NASDAQ)", f"${latest['QQQ']:.2f}", f"{(latest['QQQ']/prev['QQQ']-1)*100:.2f}%")
with k3: st.metric("VIX (FEAR)", f"{latest['VIX']:.2f}", f"{(latest['VIX']-prev['VIX']):.2f}", delta_color="inverse")
with k4: 
    color = "#ff0055" if days_to_rebalance == 0 else "#00ffff"
    st.markdown(f"""
    <div style='text-align: center; border: 1px solid {color}; padding: 5px; border-radius: 5px; background: rgba(0,0,0,0.3);'>
        <div style='color: #888; font-size: 0.8rem; font-family: Share Tech Mono;'>REBALANCE COUNTDOWN</div>
        <div style='color: {color}; font-size: 1.8rem; font-family: Orbitron; font-weight: bold;'>T-{days_to_rebalance}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 🎴 战术卡片 (v3.3 逻辑映射)
# ==========================================
c1, c2, c3 = st.columns(3)

def clean_html(html): return html.strip()

# 卡片 1: 熔断 (Meltdown)
with c1:
    state_color = "#ff0055" if is_meltdown else "#00ffff"
    state_text = "🚨 已熔断 (ACTIVE)" if is_meltdown else "🟢 正常 (SECURE)"
    dist_to_melt = max(0, MELTDOWN_PCT - curr_dd) * 100
    
    html_1 = f"""
    <div class='tactical-card-base' style='border-color: {state_color};'>
        <style>.tactical-card-base::before {{ background-image: url('data:image/png;base64,{MELTDOWN_IMAGE}'); }}</style>
        <div class='card-content'>
            <div class='card-header' style='color: {state_color};'>☢️ 熔断防御 (MELTDOWN)</div>
            <div class='card-body'>
                <div>当前回撤: <span style='color: #ff0055;'>{curr_dd*100:.2f}%</span></div>
                <div>触发阈值: <span style='color: #fff;'>{MELTDOWN_PCT*100:.1f}%</span></div>
                <div style='margin-top: 15px; border-top: 1px dashed #555; padding-top: 10px;'>
                    距离熔断还差:
                    <span class='highlight-val' style='color: {state_color};'>{dist_to_melt:.2f}%</span>
                    跌幅
                </div>
            </div>
            <div class='card-footer' style='color: {state_color};'>{state_text}</div>
        </div>
    </div>
    """
    st.markdown(clean_html(html_1), unsafe_allow_html=True)

# 卡片 2: 敢死队 (Squad)
with c2:
    if "敢死队" in latest['Status']:
        s_color = "#ff0055"
        s_text = "⚔️ 作战中 (ENGAGED)"
        s_bg = ATTACK_IMAGE
        main_info = f"仓位: {int(latest['Pct']*100)}% QLD"
    elif "瞄准" in latest['Status']:
        s_color = "#ffa500"
        s_text = "🟡 瞄准中 (AIMING)"
        s_bg = REST_IMAGE
        main_info = f"VIX < {VIX_TRIGGER} 计数中"
    else:
        s_color = "#00ff00"
        s_text = "⚪️ 待命 (STANDBY)"
        s_bg = REST_IMAGE
        main_info = f"等待 VIX > {VIX_TRIGGER}"
        
    html_2 = f"""
    <div class='tactical-card-base' style='border-color: {s_color};'>
        <style>.tactical-card-base::before {{ background-image: url('data:image/png;base64,{s_bg}'); }}</style>
        <div class='card-content'>
            <div class='card-header' style='color: {s_color};'>🏴‍☠️ 敢死队 (SQUAD)</div>
            <div class='card-body'>
                <div>当前 VIX: <span style='color: #fff;'>{latest['VIX']:.2f}</span></div>
                <div>触发条件: <span style='color: #aaa;'>VIX > {VIX_TRIGGER} + {WAIT_DAYS}d</span></div>
                <div style='margin-top: 15px; border-top: 1px dashed #555; padding-top: 10px;'>
                    当前状态:
                    <span class='highlight-val' style='color: {s_color}; font-size: 1.8rem;'>{main_info}</span>
                </div>
            </div>
            <div class='card-footer' style='color: {s_color};'>{s_text}</div>
        </div>
    </div>
    """
    st.markdown(clean_html(html_2), unsafe_allow_html=True)

# 卡片 3: 熊猫主力 (Panda)
with c3:
    if is_panda_bull:
        p_color = "#00ff00"
        p_text = "🐂 牛市趋势 (BULL)"
        p_bg = BULL_IMAGE
        dist_ma = (latest['SPY'] - latest['SPY_MA']) / latest['SPY'] * 100
        dist_mom = (latest['QQQ'] - latest['QQQ_MOM']) / latest['QQQ'] * 100
        safe_pad = min(dist_ma, dist_mom)
        p_info = f"安全垫: {safe_pad:.2f}%"
    else:
        p_color = "#00bfff"
        p_text = "🐻 熊市/震荡 (BEAR)"
        p_bg = BEAR_IMAGE
        dist_ma = (latest['SPY_MA'] - latest['SPY']) / latest['SPY'] * 100
        dist_mom = (latest['QQQ_MOM'] - latest['QQQ']) / latest['QQQ'] * 100
        req_rise = max(dist_ma, dist_mom)
        p_info = f"需上涨: {req_rise:.2f}%"

    html_3 = f"""
    <div class='tactical-card-base' style='border-color: {p_color};'>
        <style>.tactical-card-base::before {{ background-image: url('data:image/png;base64,{p_bg}'); }}</style>
        <div class='card-content'>
            <div class='card-header' style='color: {p_color};'>🐼 熊猫主力 (MAIN)</div>
            <div class='card-body'>
                <div>SPY > 200MA: <span style='color: {"#00ff00" if latest["SPY"]>latest["SPY_MA"] else "#ff0055"}'>{"YES" if latest["SPY"]>latest["SPY_MA"] else "NO"}</span></div>
                <div>QQQ > MOM95: <span style='color: {"#00ff00" if latest["QQQ"]>latest["QQQ_MOM"] else "#ff0055"}'>{"YES" if latest["QQQ"]>latest["QQQ_MOM"] else "NO"}</span></div>
                <div style='margin-top: 15px; border-top: 1px dashed #555; padding-top: 10px;'>
                    趋势反转距离:
                    <span class='highlight-val' style='color: {p_color};'>{p_info}</span>
                </div>
            </div>
            <div class='card-footer' style='color: {p_color};'>{p_text}</div>
        </div>
    </div>
    """
    st.markdown(clean_html(html_3), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 📊 战报与日志
# ==========================================
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.markdown("### 📈 历史战绩 (THEORETICAL PERFORMANCE)")
    
    def get_cagr_dd(equity, years):
        days = years * 252
        if len(equity) < days: return "N/A", "N/A"
        sub = equity.iloc[-days:]
        sub = sub / sub.iloc[0]
        cagr = (sub.iloc[-1])**(1/years) - 1
        dd = (sub - sub.cummax()) / sub.cummax()
        return cagr, dd.min()

    periods = [25, 20, 15, 10, 5]
    table_html = "<table class='perf-table'><thead><tr><th>周期</th><th>PANDA v3.3</th><th>回撤</th><th>S&P 500</th><th>超额收益</th></tr></thead><tbody>"
    
    for p in periods:
        strat_cagr, strat_dd = get_cagr_dd(df['Strategy_Eq'], p)
        spy_cagr, _ = get_cagr_dd(df['SPY_Eq'], p)
        
        if strat_cagr == "N/A": continue
        
        diff = strat_cagr - spy_cagr
        diff_cls = "pos-val" if diff > 0 else "neg-val"
        diff_str = f"+{diff*100:.2f}%" if diff > 0 else f"{diff*100:.2f}%"
        
        table_html += f"""
        <tr>
            <td>{p} YEAR</td>
            <td style='color: #00ffff; font-weight: bold;'>{strat_cagr*100:.2f}%</td>
            <td style='color: #ff0055;'>{strat_dd*100:.2f}%</td>
            <td style='color: #aaa;'>{spy_cagr*100:.2f}%</td>
            <td class='{diff_cls}'>{diff_str}</td>
        </tr>
        """
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)

with col_right:
    st.markdown("### 📝 指挥日志 (COMMAND LOG)")
    
    recent_changes = df[df['Status_Change']].tail(10).sort_index(ascending=False)
    
    log_container = "<div style='background: rgba(0,0,0,0.4); border-radius: 5px; padding: 10px; max-height: 300px; overflow-y: auto;'>"
    
    for date, row in recent_changes.iterrows():
        status = row['Status']
        # 根据状态定义颜色
        if "敢死队" in status: badge_col = "#ff0055"; bg_col = "rgba(255,0,85,0.1)"
        elif "熔断" in status: badge_col = "#ffa500"; bg_col = "rgba(255,165,0,0.1)"
        elif "熊猫" in status or "主力" in status: badge_col = "#00ff00"; bg_col = "rgba(0,255,0,0.1)"
        else: badge_col = "#00bfff"; bg_col = "rgba(0,191,255,0.1)"
        
        log_container += f"""
        <div class='log-row' style='background: {bg_col}; border-left: 3px solid {badge_col}; margin-bottom: 5px;'>
            <div style='color: #aaa;'>{date.strftime('%Y-%m-%d')}</div>
            <div style='color: #fff; font-weight: bold;'>{status}</div>
        </div>
        """
    log_container += "</div>"
    st.markdown(log_container, unsafe_allow_html=True)
