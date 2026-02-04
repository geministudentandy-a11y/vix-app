import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pandas.tseries.offsets import MonthEnd
from datetime import datetime

# ==========================================
# 🎨 1. 页面配置与 CSS 注入 (美化核心)
# ==========================================
st.set_page_config(
    page_title="PANDA COMMANDER",
    page_icon="🐼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 注入自定义 CSS：隐藏默认元素，调整字体，增加卡片质感
st.markdown("""
<style>
    /* 隐藏 Streamlit 默认顶部和菜单 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 全局字体优化 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* 指标卡片样式优化 */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #9CA3AF;
    }
    
    /* 成功/警告/错误 框体微调 */
    .stAlert {
        padding: 0.5rem 1rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 侧边栏配置
# ==========================================
with st.sidebar:
    st.title("⚙️ 系统参数")
    st.markdown("---")
    st.caption("🐼 熊猫主力")
    PANDA_MA = st.number_input("SPY 均线 (MA)", value=200)
    PANDA_MOM = st.number_input("QQQ 动量 (Days)", value=95)
    CB_DROP = st.number_input("熔断阈值", value=0.075, step=0.005, format="%.3f")
    
    st.markdown("---")
    st.caption("🏴‍☠️ 敢死队")
    SQ_BB_N = st.number_input("布林周期", value=20)
    SQ_BB_STD = st.number_input("布林偏差", value=2.5)
    SQ_RSI_ENTRY = st.number_input("RSI 入场", value=30)
    
# ==========================================
# 📥 数据引擎
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
    
    # 指标计算
    df['SPY_MA'] = df['SPY'].rolling(PANDA_MA).mean()
    df['QQQ_MOM_Ref'] = df['QQQ'].shift(PANDA_MOM)
    
    spy_max = df['SPY'].rolling(5).max()
    df['Drawdown'] = (df['SPY'] / spy_max) - 1
    
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
    df = get_market_data()
    latest = df.iloc[-1]
    curr_date = df.index[-1]
except Exception as e:
    st.error(f"系统离线: {e}")
    st.stop()

# ==========================================
# 🧠 核心逻辑
# ==========================================
# 1. 月历逻辑
month_end = curr_date + MonthEnd(0)
days_to_end = (month_end - curr_date).days
is_month_end = days_to_end == 0

# 2. 熊猫逻辑
panda_bull = (latest['SPY'] > latest['SPY_MA']) and (latest['QQQ'] > latest['QQQ_MOM_Ref'])
panda_cb = latest['Drawdown'] < -CB_DROP

# 3. 敢死队逻辑
dist_val = latest['QQQ'] - latest['Lower_Band']
dist_pct = (dist_val / latest['QQQ']) * 100
sq_fire = (latest['QQQ'] < latest['Lower_Band']) and (latest['RSI'] < SQ_RSI_ENTRY)
sq_alert = (dist_pct < 2.0)

# ==========================================
# 🖥️ 仪表盘布局 (Dashboard Layout)
# ==========================================

# --- 顶栏：市场概览 ---
col_head1, col_head2 = st.columns([2, 1])
with col_head1:
    st.title("🐼 PANDA COMMANDER")
    st.caption(f"LAST UPDATE: {curr_date.strftime('%Y-%m-%d')} | MARKET STATUS: {'OPEN' if datetime.now().hour < 21 else 'CLOSED'}")
with col_head2:
    # 迷你行情板
    c1, c2 = st.columns(2)
    c1.metric("SPY", f"{latest['SPY']:.1f}", delta=f"{df['SPY'].diff().iloc[-1]:.2f}")
    c2.metric("QQQ", f"{latest['QQQ']:.1f}", delta=f"{df['QQQ'].diff().iloc[-1]:.2f}")

st.markdown("---")

# --- 核心指示器区 (Card View) ---
col1, col2, col3 = st.columns(3)

# 1. 月度战术卡
with col1:
    st.subheader("🗓️ 月度战术 (Schedule)")
    if is_month_end:
        st.error("⚠️ 月底调仓日 (ACTION)")
        st.markdown("**指令：检查熊猫状态，决定去留**")
    else:
        # 使用进度条展示时间
        progress = max(0, min(100, int((1 - days_to_end/30)*100)))
        st.metric("距离月底", f"{days_to_end} 天", delta="非调仓期", delta_color="off")
        st.progress(progress, text="本月时间进度")

# 2. 敢死队卡 (Suicide Squad)
with col2:
    st.subheader("🏴‍☠️ 敢死队 (S.Q.)")
    if sq_fire:
        st.error("🔴 ACTIVE: 全员出击")
        st.metric("操作指令", "买入 QLD", delta="SIGNAL FIRED", delta_color="inverse")
    elif sq_alert:
        st.warning("🟡 WARNING: 高度警惕")
        st.metric("距离下轨", f"{dist_pct:.2f}%", delta="接近射程", delta_color="inverse")
    else:
        st.success("🟢 SLEEP: 回营休息")
        st.metric("安全边际", f"+{dist_pct:.2f}%", f"RSI: {latest['RSI']:.1f}")

# 3. 熊猫主力卡 (Panda Main)
with col3:
    st.subheader("🐼 熊猫主力 (Main)")
    
    if panda_cb:
        st.error("🚨 CRASH: 熔断触发")
        st.metric("紧急指令", "换仓 QQQ", delta=f"暴跌 {latest['Drawdown']*100:.1f}%", delta_color="inverse")
    else:
        if panda_bull:
            st.success("🐂 BULL: 趋势进攻")
            st.metric("持仓建议", "QLD (2x)", delta="熔断监测正常")
        else:
            st.info("🐻 BEAR: 趋势防御")
            st.metric("持仓建议", "CASH (0x)", delta="空仓避险", delta_color="off")

st.markdown("---")

# --- 图表区 (Fixed Chart) ---
st.subheader("📉 战术地形图 (Tactical Map)")

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, row_heights=[0.75, 0.25])

# 价格线 (白色)
fig.add_trace(go.Scatter(x=df.index, y=df['QQQ'], mode='lines', name='Price', 
                         line=dict(color='#F3F4F6', width=1.5)), row=1, col=1)
# 恐慌线 (红色虚线)
fig.add_trace(go.Scatter(x=df.index, y=df['Lower_Band'], mode='lines', name='Panic Line', 
                         line=dict(color='#EF4444', width=1.5, dash='dash')), row=1, col=1)

# 买入信号 (黄色三角)
sq_signals = df[(df['QQQ'] < df['Lower_Band']) & (df['RSI'] < SQ_RSI_ENTRY)]
if len(sq_signals) > 0:
    fig.add_trace(go.Scatter(x=sq_signals.index, y=sq_signals['QQQ'], mode='markers', name='Buy',
                             marker=dict(color='#F59E0B', size=10, symbol='triangle-up')), row=1, col=1)

# RSI (青色)
fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI', 
                         line=dict(color='#22D3EE', width=1.5)), row=2, col=1)
# RSI 阈值
fig.add_hline(y=30, line_width=1, line_color="#EF4444", row=2, col=1)
fig.add_hline(y=70, line_width=1, line_color="#4B5563", row=2, col=1)

# 布局美化 (黑金风格/深色金融风)
fig.update_layout(
    height=500,
    paper_bgcolor='rgba(0,0,0,0)', # 透明背景
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=10, r=10, t=20, b=10),
    xaxis=dict(fixedrange=True, showgrid=False, color='#9CA3AF'),
    yaxis=dict(fixedrange=True, showgrid=True, gridcolor='#374151', color='#9CA3AF'),
    yaxis2=dict(fixedrange=True, showgrid=True, gridcolor='#374151', color='#9CA3AF', range=[0, 100]),
    showlegend=False,
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': False, 'scrollZoom': False})

# --- 底部数据折叠 ---
with st.expander("🔍 查看原始战术数据 (Raw Data)"):
    cols = ['SPY', 'QQQ', 'RSI', 'Lower_Band', 'Drawdown']
    style_df = df[cols].tail(10).style.format("{:.2f}")
    # 高亮 RSI < 30 的行
    def highlight_rsi(val):
        color = '#450a0a' if val < 30 else '' # 深红色背景
        return f'background-color: {color}'
    st.dataframe(style_df.applymap(highlight_rsi, subset=['RSI']), use_container_width=True)
