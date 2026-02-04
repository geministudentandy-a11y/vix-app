import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pandas.tseries.offsets import MonthEnd
from datetime import datetime

# ==========================================
# ⚙️ 页面配置
# ==========================================
st.set_page_config(
    page_title="Kung Fu Panda Command Center",
    page_icon="🐼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🎛️ 侧边栏：参数控制
# ==========================================
st.sidebar.title("🛠️ 战术参数配置")

st.sidebar.subheader("🐼 熊猫 (趋势)")
PANDA_MA = st.sidebar.number_input("SPY 均线周期", value=200)
PANDA_MOM = st.sidebar.number_input("QQQ 动量周期", value=95)
CB_DROP = st.sidebar.number_input("熔断阈值 (小数)", value=0.075, step=0.005, format="%.3f")

st.sidebar.subheader("🏴‍☠️ 敢死队 (反转)")
SQ_BB_N = st.sidebar.number_input("布林带周期", value=20)
SQ_BB_STD = st.sidebar.number_input("布林带偏差", value=2.5)
SQ_RSI_ENTRY = st.sidebar.number_input("RSI 入场阈值", value=30)
SQ_RSI_ALERT = st.sidebar.number_input("RSI 预警阈值", value=35)

# ==========================================
# 📥 数据获取与计算
# ==========================================
@st.cache_data(ttl=3600) # 缓存1小时，避免重复下载
def get_data():
    tickers = ['SPY', 'QQQ']
    data = yf.download(tickers, period="2y", progress=False, auto_adjust=True)
    if isinstance(data.columns, pd.MultiIndex):
        df = data['Close'].copy()
    else:
        df = data.copy()
    return df.dropna()

def calculate_metrics(df):
    # 1. 熊猫计算
    df['SPY_MA'] = df['SPY'].rolling(PANDA_MA).mean()
    df['QQQ_MOM_Ref'] = df['QQQ'].shift(PANDA_MOM)
    
    spy_max = df['SPY'].rolling(5).max()
    df['Drawdown'] = (df['SPY'] / spy_max) - 1
    
    # 2. 敢死队计算
    sma = df['QQQ'].rolling(SQ_BB_N).mean()
    std = df['QQQ'].rolling(SQ_BB_N).std()
    df['Lower_Band'] = sma - (SQ_BB_STD * std)
    
    delta = df['QQQ'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

try:
    with st.spinner('📡 正在连接前线数据中心...'):
        raw_df = get_data()
        df = calculate_metrics(raw_df)
        
    latest = df.iloc[-1]
    curr_date = df.index[-1]
    
except Exception as e:
    st.error(f"数据获取失败: {e}")
    st.stop()

# ==========================================
# 📊 仪表盘逻辑
# ==========================================

# 1. 状态判定
# 日历
month_end = curr_date + MonthEnd(0)
days_to_end = (month_end - curr_date).days
is_month_end = days_to_end == 0

# 熊猫
panda_bull = (latest['SPY'] > latest['SPY_MA']) and (latest['QQQ'] > latest['QQQ_MOM_Ref'])
panda_cb = latest['Drawdown'] < -CB_DROP

# 敢死队
sq_fire = (latest['QQQ'] < latest['Lower_Band']) and (latest['RSI'] < SQ_RSI_ENTRY)
dist_pct = (latest['QQQ'] - latest['Lower_Band']) / latest['QQQ'] * 100
sq_alert = (dist_pct < 2.0) or (latest['RSI'] < SQ_RSI_ALERT)

# ==========================================
# 🖥️ UI 显示层
# ==========================================

st.title("🐼 功夫熊猫 · 指挥官仪表盘")
st.markdown(f"📅 **数据日期**: {curr_date.strftime('%Y-%m-%d')} | 📊 **SPY**: ${latest['SPY']:.2f} | 💻 **QQQ**: ${latest['QQQ']:.2f}")

st.divider()

# --- 三大卡片布局 ---
col1, col2, col3 = st.columns(3)

# 卡片 1: 月度日历
with col1:
    st.subheader("🗓️ 月度战略")
    if is_month_end:
        st.warning("⚠️ 今天是月底最后一天")
        st.markdown("**👉 请检查熊猫状态决定是否调仓**")
    elif days_to_end <= 3:
        st.info(f"⏳ 临近月底 (剩 {days_to_end} 天)")
    else:
        st.success(f"💤 非调仓期 (剩 {days_to_end} 天)")
        st.caption("保持当前战略不动")

# 卡片 2: 敢死队 (Suicide Squad)
with col2:
    st.subheader("🏴‍☠️ 敢死队 (SQ)")
    
    if sq_fire:
        st.error("🔴 全员出击 (ACTIVE)")
        st.markdown("### 👉 买入 QLD")
        st.caption(f"击穿下轨 & RSI {latest['RSI']:.1f}")
    elif sq_alert:
        st.warning("🟡 高度警惕 (WATCHING)")
        st.metric("距离下轨", f"{dist_pct:.2f}%", delta_color="inverse")
        st.metric("当前 RSI", f"{latest['RSI']:.1f}")
    else:
        st.success("🟢 回营休息 (SLEEP)")
        st.metric("安全距离", f"+{dist_pct:.2f}%")
        st.caption(f"当前 RSI: {latest['RSI']:.1f}")

# 卡片 3: 熊猫主力 (Panda)
with col3:
    st.subheader("🐼 熊猫主力")
    
    if panda_cb:
        st.error("🚨 熔断触发 (CRASH)")
        st.markdown("### 👉 全换 QQQ")
        st.caption(f"5日回撤: {latest['Drawdown']*100:.2f}%")
    elif panda_bull:
        st.success("🐂 牛市进攻 (BULL)")
        st.markdown("### 👉 持有 QLD")
        st.caption("趋势向上 & 动能充足")
    else:
        st.info("🐻 熊市防御 (BEAR)")
        st.markdown("### 👉 空仓/现金")
        st.caption("趋势转弱")

st.divider()

# ==========================================
# 📈 交互式图表 (Plotly)
# ==========================================
st.subheader("📉 战术地形图 (QQQ)")

# 创建子图: 上面是价格+布林带，下面是RSI
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, row_heights=[0.7, 0.3])

# 主图: QQQ 价格
fig.add_trace(go.Scatter(x=df.index, y=df['QQQ'], mode='lines', name='QQQ Price', line=dict(color='white', width=1)), row=1, col=1)

# 主图: 布林带下轨
fig.add_trace(go.Scatter(x=df.index, y=df['Lower_Band'], mode='lines', name='Lower Band (Panic)', 
                         line=dict(color='red', width=1, dash='dash')), row=1, col=1)

# 标记: 敢死队触发点
sq_signals = df[(df['QQQ'] < df['Lower_Band']) & (df['RSI'] < SQ_RSI_ENTRY)]
fig.add_trace(go.Scatter(x=sq_signals.index, y=sq_signals['QQQ'], mode='markers', name='SQ Buy Signal',
                         marker=dict(color='yellow', size=10, symbol='triangle-up')), row=1, col=1)

# 副图: RSI
fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI', line=dict(color='#00F0FF')), row=2, col=1)

# RSI 辅助线
fig.add_hline(y=30, line_dash="dot", line_color="red", row=2, col=1, annotation_text="Oversold (30)")
fig.add_hline(y=70, line_dash="dot", line_color="gray", row=2, col=1)

fig.update_layout(height=600, template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20))
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 📋 原始数据查看
# ==========================================
with st.expander("🔍 查看最近 5 天详细数据"):
    cols = ['SPY', 'QQQ', 'RSI', 'Lower_Band', 'Drawdown']
    st.dataframe(df[cols].tail(5).style.format("{:.2f}"))
