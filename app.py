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
    page_title="Kung Fu Panda Dashboard",
    page_icon="🐼",
    layout="wide",
    initial_sidebar_state="collapsed" # 默认收起侧边栏，视野更开阔
)

# CSS 样式微调：隐藏图表右上角的工具栏，让界面更干净
st.markdown("""
<style>
    [data-testid="stHeader"] {display: none;}
    .modebar {display: none !important;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🎛️ 侧边栏：参数 (默认隐藏)
# ==========================================
with st.sidebar:
    st.header("⚙️ 战术参数")
    st.subheader("🐼 熊猫")
    PANDA_MA = st.number_input("SPY 均线", value=200)
    PANDA_MOM = st.number_input("QQQ 动量", value=95)
    CB_DROP = st.number_input("熔断阈值", value=0.075, step=0.005, format="%.3f")

    st.subheader("🏴‍☠️ 敢死队")
    SQ_BB_N = st.number_input("布林周期", value=20)
    SQ_BB_STD = st.number_input("布林偏差", value=2.5)
    SQ_RSI_ENTRY = st.number_input("RSI 入场", value=30)
    SQ_RSI_ALERT = st.number_input("RSI 预警", value=35)

# ==========================================
# 📥 数据获取
# ==========================================
@st.cache_data(ttl=1800) 
def get_data_and_calc():
    tickers = ['SPY', 'QQQ']
    # 下载数据
    data = yf.download(tickers, period="1y", progress=False, auto_adjust=True) # 改为1年，视图更聚焦
    if isinstance(data.columns, pd.MultiIndex):
        df = data['Close'].copy()
    else:
        df = data.copy()
    df = df.dropna()

    # --- 计算指标 ---
    # 1. 熊猫
    df['SPY_MA'] = df['SPY'].rolling(PANDA_MA).mean()
    df['QQQ_MOM_Ref'] = df['QQQ'].shift(PANDA_MOM)
    # 熔断计算 (5日最高点跌幅)
    spy_max = df['SPY'].rolling(5).max()
    df['Drawdown'] = (df['SPY'] / spy_max) - 1
    
    # 2. 敢死队
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
    df = get_data_and_calc()
    latest = df.iloc[-1]
    curr_date = df.index[-1]
except Exception as e:
    st.error(f"数据连接断开: {e}")
    st.stop()

# ==========================================
# 🧠 逻辑判定
# ==========================================
# 日历
month_end = curr_date + MonthEnd(0)
days_to_end = (month_end - curr_date).days
is_month_end = days_to_end == 0

# 熊猫状态
panda_bull = (latest['SPY'] > latest['SPY_MA']) and (latest['QQQ'] > latest['QQQ_MOM_Ref'])
panda_cb = latest['Drawdown'] < -CB_DROP

# 敢死队状态
dist_pct = (latest['QQQ'] - latest['Lower_Band']) / latest['QQQ'] * 100
sq_fire = (latest['QQQ'] < latest['Lower_Band']) and (latest['RSI'] < SQ_RSI_ENTRY)
sq_alert = (dist_pct < 2.0) or (latest['RSI'] < SQ_RSI_ALERT)

# ==========================================
# 🖥️ 仪表盘 UI
# ==========================================

st.title("🐼 功夫熊猫 · 指挥官仪表盘")
st.caption(f"数据更新: {curr_date.strftime('%Y-%m-%d')} | SPY: {latest['SPY']:.2f} | QQQ: {latest['QQQ']:.2f}")

st.divider()

# --- 核心信号区 ---
c1, c2, c3 = st.columns(3)

# 1. 月历
with c1:
    st.subheader("🗓️ 调仓日历")
    if is_month_end:
        st.error("⚠️ 今天是月底")
        st.markdown("**动作: 检查熊猫状态调仓**")
    elif days_to_end <= 3:
        st.warning(f"⏳ 临近月底 ({days_to_end}天)")
    else:
        st.success("💤 非调仓期")
        st.caption(f"距离月底还有 {days_to_end} 天")

# 2. 敢死队 (SQ)
with c2:
    st.subheader("🏴‍☠️ 敢死队 (SQ)")
    if sq_fire:
        st.error("🔴 全员出击")
        st.markdown("**👉 买入 QLD**")
    elif sq_alert:
        st.warning("🟡 高度警惕")
        st.markdown(f"**距下轨: {dist_pct:.2f}%**")
    else:
        st.success("🟢 回营休息")
        st.markdown(f"距下轨: +{dist_pct:.2f}%")

# 3. 熊猫主力 (含熔断灯)
with c3:
    st.subheader("🐼 熊猫主力")
    
    # --- 熔断信号灯逻辑 ---
    if panda_cb:
        # 🔴 红灯闪烁 (熔断)
        st.error("🚨 熔断触发 (CRASH)")
        st.markdown("### 👉 QLD 换 QQQ")
        st.progress(100, text=f"5日暴跌: {latest['Drawdown']*100:.2f}%")
    else:
        # 检查是否牛市
        if panda_bull:
            # 🟢 绿灯 (牛市)
            st.success("🐂 牛市进攻 (BULL)")
            st.markdown("### 👉 持有 QLD")
            # 显示一个绿色的安全条
            st.markdown("✅ 熔断监测: 安全")
        else:
            # ⚪ 灰灯 (熊市)
            st.info("🐻 熊市防御 (BEAR)")
            st.markdown("### 👉 空仓/现金")
            st.markdown("✅ 熔断监测: 安全")

st.divider()

# ==========================================
# 📉 锁定视图的图表 (无缩放)
# ==========================================
st.subheader("📉 战术地形图 (固定视图)")

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.75, 0.25])

# 主图: 价格 + 布林带
fig.add_trace(go.Scatter(x=df.index, y=df['QQQ'], mode='lines', name='Price', line=dict(color='white', width=1.5)), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['Lower_Band'], mode='lines', name='Panic Line', line=dict(color='red', width=1.5, dash='dot')), row=1, col=1)

# 信号点
sq_signals = df[(df['QQQ'] < df['Lower_Band']) & (df['RSI'] < SQ_RSI_ENTRY)]
if len(sq_signals) > 0:
    fig.add_trace(go.Scatter(x=sq_signals.index, y=sq_signals['QQQ'], mode='markers', name='Buy Signal',
                             marker=dict(color='yellow', size=12, symbol='triangle-up')), row=1, col=1)

# 副图: RSI
fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI', line=dict(color='#00F0FF', width=1)), row=2, col=1)
fig.add_hline(y=30, line_dash="solid", line_color="red", row=2, col=1)
fig.add_hline(y=70, line_dash="solid", line_color="gray", row=2, col=1)

# --- 关键修改: 锁定坐标轴，禁止缩放 ---
fig.update_layout(
    height=500,
    template="plotly_dark",
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis=dict(fixedrange=True, showgrid=False),  # 锁定 X轴
    yaxis=dict(fixedrange=True, showgrid=True, gridcolor='#333'),  # 锁定 Y轴
    xaxis2=dict(fixedrange=True, showgrid=False), # 锁定 副图X轴
    yaxis2=dict(fixedrange=True, showgrid=True, gridcolor='#333'), # 锁定 副图Y轴
    showlegend=False,
    hovermode="x unified" # 保留悬停十字光标，这是看数据的关键
)

#config={'staticPlot': True} 会完全变成图片，连鼠标悬停都没了。
#config={'displayModeBar': False} 隐藏工具栏
#配合上面的 fixedrange=True，实现了“只能看数值，不能动图表”的效果
st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

# 显示详细数据表
with st.expander("📊 查看详细数据"):
    cols = ['SPY', 'QQQ', 'RSI', 'Lower_Band', 'Drawdown']
    st.dataframe(df[cols].tail(5).style.format("{:.2f}"))
