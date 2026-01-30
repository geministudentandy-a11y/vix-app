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
st.title("🦘 VixBooster (澳股实盘计算器)")

# ==========================================
# 2. 侧边栏：输入您的实盘数据
# ==========================================
with st.sidebar:
    st.header("💼 我的实盘资产 (AUD)")
    st.caption("每次交易前更新此处，计算器会给出精确买卖建议。")
    
    my_hgbl_qty = st.number_input("HGBL 持仓股数", min_value=0, value=0, step=100)
    my_ggus_qty = st.number_input("GGUS 持仓股数", min_value=0, value=0, step=100)
    my_cash = st.number_input("账户可用现金", min_value=0.0, value=300000.0, step=1000.0)
    
    st.markdown("---")
    st.markdown("### 📊 策略参数")
    st.code("""
RSI买入: <70
VIX爆发: >20/30
止盈线: >80
    """, language="text")

# ==========================================
# 3. 核心策略参数
# ==========================================
SMA_PERIOD = 200
RSI_PERIOD = 14

# 信号阈值
RSI_BULL_ENTER = 70
RSI_BEAR_ENTER = 40
RSI_EXIT_PROFIT = 80
RSI_BEAR_EXIT = 35

VIX_LEVEL_1 = 20
VIX_LEVEL_2 = 30

# 目标仓位 (Target Allocation)
TARGET_PCT_EMPTY = 0.00
TARGET_PCT_BASE = 0.20  # 20%
TARGET_PCT_BOOST_1 = 0.40 # 40%
TARGET_PCT_BOOST_2 = 0.60 # 60%

# ==========================================
# 4. 数据获取 (美股信号 + 澳股价格)
# ==========================================
@st.cache_data(ttl=3600)
def get_market_data():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=450)
    
    # 1. 下载信号源 (美股)
    spy = yf.download("SPY", start=start_date, end=end_date, progress=False)
    vix = yf.download("^VIX", start=start_date, end=end_date, progress=False)
    
    # 2. 下载澳股实时价格 (计算资产用)
    # 取最后几天数据即可，减少流量
    start_short = end_date - datetime.timedelta(days=10)
    au_tickers = yf.download(["HGBL.AX", "GGUS.AX"], start=start_short, end=end_date, progress=False)['Close']
    
    # 清洗数据
    if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
    if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)
    
    # 提取澳股最新价格
    try:
        price_hgbl = au_tickers['HGBL.AX'].dropna().iloc[-1]
        price_ggus = au_tickers['GGUS.AX'].dropna().iloc[-1]
    except:
        price_hgbl = 0
        price_ggus = 0
    
    return spy, vix, price_hgbl, price_ggus

@st.cache_data(ttl=3600)
def get_cnn_index():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data['fear_and_greed']['score'], data['fear_and_greed']['rating']
    except:
        pass
    return None, "获取失败"

def calculate_strategy(spy, vix, p_hgbl, p_ggus, h_qty, g_qty, cash):
    # --- A. 计算信号 (美股) ---
    spy['SMA200'] = ta.sma(spy['Close'], length=SMA_PERIOD)
    spy['RSI'] = ta.rsi(spy['Close'], length=RSI_PERIOD)
    
    curr_price = spy['Close'].iloc[-1]
    curr_sma = spy['SMA200'].iloc[-1]
    curr_rsi = spy['RSI'].iloc[-1]
    curr_vix = vix['Close'].iloc[-1]
    last_date = spy.index[-1].strftime('%Y-%m-%d')
    is_bull = curr_price > curr_sma
    
    # --- B. 确定目标仓位 ---
    target_ggus_pct = 0.0
    signal_name = "观望"
    color = "gray"
    reason = "无操作"

    if not is_bull: # 熊市
        if curr_rsi > RSI_BEAR_EXIT:
            target_ggus_pct = 0.0
            signal_name = "🛡️ 红色警报 (清空)"
            color = "red"
            reason = "熊市反弹结束，清空 GGUS。"
        elif curr_rsi < RSI_BEAR_ENTER and curr_vix > 33:
            target_ggus_pct = TARGET_PCT_BASE # 熊市抄底只买20%
            signal_name = "💎 钻石坑 (抄底)"
            color = "green"
            reason = "极度恐慌，轻仓抢反弹。"
        else:
            target_ggus_pct = 0.0
            signal_name = "🛡️ 熊市防御"
            color = "red"
            reason = "熊市下跌中，空仓观望。"
            
    elif curr_rsi > RSI_EXIT_PROFIT: # 止盈
        target_ggus_pct = TARGET_PCT_BASE # 降回 20%
        signal_name = "💰 止盈 (减仓)"
        color = "orange"
        reason = "RSI 过热，减仓至基础水位。"
        
    elif is_bull: # 牛市
        if curr_rsi < RSI_BULL_ENTER:
            if curr_vix > VIX_LEVEL_2:
                target_ggus_pct = TARGET_PCT_BOOST_2 # 60%
                signal_name = "🚀 强力进攻 (重仓 60%)"
                color = "green"
                reason = "极度恐慌机会，大幅加仓。"
            elif curr_vix > VIX_LEVEL_1:
                target_ggus_pct = TARGET_PCT_BOOST_1 # 40%
                signal_name = "⚔️ 加力进攻 (加仓 40%)"
                color = "green"
                reason = "恐慌机会，加码买入。"
            else:
                target_ggus_pct = TARGET_PCT_BASE # 20%
                signal_name = "🔫 常规进攻 (持有 20%)"
                color = "green"
                reason = "牛市常态持有。"
        else:
            target_ggus_pct = 0.0
            signal_name = "☕ 暂时休息 (持有现金/HGBL)"
            color = "blue"
            reason = "牛市短期过热，暂时不持仓 GGUS。"

    # --- C. 计算实盘交易指令 ---
    total_assets = (h_qty * p_hgbl) + (g_qty * p_ggus) + cash
    target_ggus_val = total_assets * target_ggus_pct
    current_ggus_val = g_qty * p_ggus
    
    diff_val = target_ggus_val - current_ggus_val
    trade_action = "无操作"
    trade_qty = 0
    trade_amount = 0
    
    if abs(diff_val) < 1000: # 变动小于1000刀就不折腾了
        trade_action = "✅ 仓位达标 (Hold)"
    elif diff_val > 0:
        trade_qty = int(diff_val / p_ggus)
        trade_amount = diff_val
        trade_action = f"🔵 买入 {trade_qty} 股 GGUS"
    else:
        trade_qty = int(abs(diff_val) / p_ggus)
        trade_amount = abs(diff_val)
        trade_action = f"🔴 卖出 {trade_qty} 股 GGUS"

    return locals()

# ==========================================
# 5. 主程序 UI
# ==========================================
if st.button('🔄 刷新信号与资产'):
    st.cache_data.clear()
    st.rerun()

with st.spinner('正在分析华尔街信号 & 计算您的澳股仓位...'):
    spy, vix, p_hgbl, p_ggus = get_market_data()
    cnn_val, cnn_rating = get_cnn_index()
    
    # 从侧边栏获取数据
    res = calculate_strategy(spy, vix, p_hgbl, p_ggus, st.session_state.get('shares_hgbl', 0) if 'shares_hgbl' not in st.session_state else my_hgbl_qty, my_ggus_qty, my_cash)

# --- 顶部：交易指令卡片 ---
st.markdown(f"### 📢 交易指令: {res['trade_action']}")

if "买入" in res['trade_action']:
    st.success(f"""
    **请立即执行以下操作：**
    * 标的: **GGUS.AX**
    * 方向: **买入 (Buy)**
    * 数量: **{res['trade_qty']} 股**
    * 预估金额: **${res['trade_amount']:,.2f}**
    
    *资金来源: 请使用账户现金或卖出同等金额的 HGBL。*
    """)
elif "卖出" in res['trade_action']:
    st.warning(f"""
    **请立即执行以下操作：**
    * 标的: **GGUS.AX**
    * 方向: **卖出 (Sell)**
    * 数量: **{res['trade_qty']} 股**
    * 回收金额: **${res['trade_amount']:,.2f}**
    """)
else:
    st.info("您的仓位非常完美，无需任何操作。享受生活吧！☕")

st.markdown("---")

# --- 中部：资产体检 ---
c1, c2, c3 = st.columns(3)
c1.metric("总资产 (AUD)", f"${res['total_assets']:,.0f}")
c2.metric("当前 GGUS 仓位", f"{res['current_ggus_val']/res['total_assets']*100:.1f}%", f"目标: {res['target_ggus_pct']*100:.0f}%")
c3.metric("当前 GGUS 价值", f"${res['current_ggus_val']:,.0f}", f"目标: ${res['target_ggus_val']:,.0f}")

st.caption(f"参考价格: HGBL ${res['p_hgbl']:.2f} | GGUS ${res['p_ggus']:.2f} (如有延迟请以券商为准)")

st.markdown("---")

# --- 底部：市场信号详情 ---
st.subheader("🔍 信号来源 (美股)")
m1, m2, m3, m4 = st.columns(4)
m1.metric("SPY 价格", f"${res['curr_price']:.0f}", 
          delta="牛市" if res['is_bull'] else "熊市", delta_color="normal" if res['is_bull'] else "inverse")
m2.metric("RSI (14)", f"{res['curr_rsi']:.1f}", f"买入线 < {RSI_BULL_ENTER}")
m3.metric("VIX 恐慌", f"{res['curr_vix']:.1f}", "爆发线 > 20")
if cnn_val:
    m4.metric("CNN 贪婪", f"{cnn_val:.0f}", cnn_rating)
else:
    m4.metric("CNN", "N/A", "获取失败")

st.info(f"**策略状态**: {res['signal_name']} - {res['reason']}")
