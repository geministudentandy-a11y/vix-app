"""
🐼 PANDA COMMANDER - Trading Strategy Dashboard
================================================
A Streamlit-based trading dashboard that implements two strategies:
1. Panda Main Force (熊猫主力): Trend-following with circuit breaker
2. Suicide Squad (敢死队): Mean-reversion based on Bollinger Bands & RSI

Author: Beautified Version
Last Updated: 2025
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pandas.tseries.offsets import MonthEnd
from datetime import datetime


# ==========================================
# 🎨 PAGE CONFIGURATION & STYLING
# ==========================================

st.set_page_config(
    page_title="PANDA COMMANDER",
    page_icon="🐼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for enhanced UI
st.markdown("""
<style>
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Global font optimization */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Metric card styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #9CA3AF;
    }
    
    /* Alert box refinement */
    .stAlert {
        padding: 0.5rem 1rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# ⚙️ SIDEBAR CONFIGURATION
# ==========================================

with st.sidebar:
    st.title("⚙️ Strategy Parameters")
    st.markdown("---")
    
    # Panda Main Force settings
    st.caption("🐼 Panda Main Force")
    PANDA_MA = st.number_input(
        "SPY Moving Average (MA)", 
        value=200, 
        help="Trend filter for SPY"
    )
    PANDA_MOM = st.number_input(
        "QQQ Momentum (Days)", 
        value=95,
        help="Lookback period for QQQ momentum"
    )
    CB_DROP = st.number_input(
        "Circuit Breaker Threshold", 
        value=0.075, 
        step=0.005, 
        format="%.3f",
        help="Drawdown threshold to trigger emergency exit"
    )
    
    st.markdown("---")
    
    # Suicide Squad settings
    st.caption("🏴‍☠️ Suicide Squad")
    SQ_BB_N = st.number_input(
        "Bollinger Period", 
        value=20,
        help="Number of periods for Bollinger Bands calculation"
    )
    SQ_BB_STD = st.number_input(
        "Bollinger Std Dev", 
        value=2.5,
        help="Standard deviation multiplier for bands"
    )
    SQ_RSI_ENTRY = st.number_input(
        "RSI Entry Threshold", 
        value=30,
        help="RSI level to trigger buy signal"
    )


# ==========================================
# 📥 DATA ENGINE
# ==========================================

@st.cache_data(ttl=1800)
def get_market_data():
    """
    Fetch and process market data with technical indicators.
    
    Returns:
        pd.DataFrame: Processed dataframe with all technical indicators
    """
    # Download data
    tickers = ['SPY', 'QQQ']
    data = yf.download(tickers, period="1y", progress=False, auto_adjust=True)
    
    # Handle multi-index columns
    if isinstance(data.columns, pd.MultiIndex):
        df = data['Close'].copy()
    else:
        df = data.copy()
    
    df = df.dropna()
    
    # --- Calculate Technical Indicators ---
    
    # 1. Panda indicators
    df['SPY_MA'] = df['SPY'].rolling(PANDA_MA).mean()
    df['QQQ_MOM_Ref'] = df['QQQ'].shift(PANDA_MOM)
    
    # 2. Drawdown calculation
    spy_max = df['SPY'].rolling(5).max()
    df['Drawdown'] = (df['SPY'] / spy_max) - 1
    
    # 3. Bollinger Bands
    sma = df['QQQ'].rolling(SQ_BB_N).mean()
    std = df['QQQ'].rolling(SQ_BB_N).std()
    df['Lower_Band'] = sma - (SQ_BB_STD * std)
    
    # 4. RSI calculation
    delta = df['QQQ'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df


# Fetch data with error handling
try:
    df = get_market_data()
    latest = df.iloc[-1]
    curr_date = df.index[-1]
except Exception as e:
    st.error(f"🚨 System Offline: {e}")
    st.stop()


# ==========================================
# 🧠 CORE STRATEGY LOGIC
# ==========================================

# --- 1. Monthly Rebalance Logic ---
month_end = curr_date + MonthEnd(0)
days_to_end = (month_end - curr_date).days
is_month_end = days_to_end == 0

# --- 2. Panda Main Force Logic ---
panda_bull = (
    latest['SPY'] > latest['SPY_MA'] and 
    latest['QQQ'] > latest['QQQ_MOM_Ref']
)
panda_cb = latest['Drawdown'] < -CB_DROP

# --- 3. Suicide Squad Logic ---
dist_val = latest['QQQ'] - latest['Lower_Band']
dist_pct = (dist_val / latest['QQQ']) * 100
sq_fire = (
    latest['QQQ'] < latest['Lower_Band'] and 
    latest['RSI'] < SQ_RSI_ENTRY
)
sq_alert = dist_pct < 2.0


# ==========================================
# 🖥️ DASHBOARD LAYOUT
# ==========================================

# --- Top Bar: Market Overview ---
col_head1, col_head2 = st.columns([2, 1])

with col_head1:
    st.title("🐼 PANDA COMMANDER")
    market_status = 'OPEN' if datetime.now().hour < 21 else 'CLOSED'
    st.caption(
        f"LAST UPDATE: {curr_date.strftime('%Y-%m-%d')} | "
        f"MARKET STATUS: {market_status}"
    )

with col_head2:
    # Mini ticker board
    c1, c2 = st.columns(2)
    spy_change = df['SPY'].diff().iloc[-1]
    qqq_change = df['QQQ'].diff().iloc[-1]
    
    c1.metric("SPY", f"{latest['SPY']:.1f}", delta=f"{spy_change:.2f}")
    c2.metric("QQQ", f"{latest['QQQ']:.1f}", delta=f"{qqq_change:.2f}")

st.markdown("---")


# --- Strategy Cards (3-Column Layout) ---
col1, col2, col3 = st.columns(3)

# Card 1: Monthly Rebalance Indicator
with col1:
    st.subheader("🗓️ Monthly Rebalance")
    
    if is_month_end:
        st.error("⚠️ REBALANCE DAY")
        st.markdown("**Action: Review Panda status and adjust positions**")
    else:
        progress = max(0, min(100, int((1 - days_to_end/30) * 100)))
        st.metric(
            "Days to Month End", 
            f"{days_to_end} days", 
            delta="Off-cycle", 
            delta_color="off"
        )
        st.progress(progress, text="Monthly Progress")

# Card 2: Suicide Squad Status
with col2:
    st.subheader("🏴‍☠️ Suicide Squad")
    
    if sq_fire:
        st.error("🔴 ACTIVE: Full Deployment")
        st.metric(
            "Trade Signal", 
            "BUY QLD", 
            delta="SIGNAL FIRED", 
            delta_color="inverse"
        )
    elif sq_alert:
        st.warning("🟡 WARNING: High Alert")
        st.metric(
            "Distance to Band", 
            f"{dist_pct:.2f}%", 
            delta="Near trigger", 
            delta_color="inverse"
        )
    else:
        st.success("🟢 SLEEP: Stand Down")
        st.metric(
            "Safety Margin", 
            f"+{dist_pct:.2f}%", 
            f"RSI: {latest['RSI']:.1f}"
        )

# Card 3: Panda Main Force Status
with col3:
    st.subheader("🐼 Panda Main Force")
    
    if panda_cb:
        st.error("🚨 CRASH: Circuit Breaker Triggered")
        st.metric(
            "Emergency Action", 
            "Switch to QQQ", 
            delta=f"Drop: {latest['Drawdown']*100:.1f}%", 
            delta_color="inverse"
        )
    else:
        if panda_bull:
            st.success("🐂 BULL: Trend Offensive")
            st.metric(
                "Position", 
                "QLD (2x)", 
                delta="Circuit breaker: OK"
            )
        else:
            st.info("🐻 BEAR: Trend Defensive")
            st.metric(
                "Position", 
                "CASH (0x)", 
                delta="Risk-off mode", 
                delta_color="off"
            )

st.markdown("---")


# ==========================================
# 📈 TACTICAL CHART
# ==========================================

st.subheader("📉 Tactical Map")

# Create subplot figure
fig = make_subplots(
    rows=2, 
    cols=1, 
    shared_xaxes=True,
    vertical_spacing=0.05, 
    row_heights=[0.75, 0.25]
)

# --- Top Panel: Price & Bollinger Bands ---

# Price line (white)
fig.add_trace(
    go.Scatter(
        x=df.index, 
        y=df['QQQ'], 
        mode='lines', 
        name='QQQ Price',
        line=dict(color='#F3F4F6', width=1.5)
    ), 
    row=1, col=1
)

# Lower Bollinger Band (red dashed)
fig.add_trace(
    go.Scatter(
        x=df.index, 
        y=df['Lower_Band'], 
        mode='lines', 
        name='Panic Line',
        line=dict(color='#EF4444', width=1.5, dash='dash')
    ), 
    row=1, col=1
)

# Buy signals (yellow triangles)
sq_signals = df[
    (df['QQQ'] < df['Lower_Band']) & 
    (df['RSI'] < SQ_RSI_ENTRY)
]
if len(sq_signals) > 0:
    fig.add_trace(
        go.Scatter(
            x=sq_signals.index, 
            y=sq_signals['QQQ'],
            mode='markers', 
            name='Buy Signal',
            marker=dict(color='#F59E0B', size=10, symbol='triangle-up')
        ), 
        row=1, col=1
    )

# --- Bottom Panel: RSI ---

# RSI line (cyan)
fig.add_trace(
    go.Scatter(
        x=df.index, 
        y=df['RSI'], 
        mode='lines', 
        name='RSI',
        line=dict(color='#22D3EE', width=1.5)
    ), 
    row=2, col=1
)

# RSI threshold lines
fig.add_hline(y=30, line_width=1, line_color="#EF4444", row=2, col=1)  # Oversold
fig.add_hline(y=70, line_width=1, line_color="#4B5563", row=2, col=1)  # Overbought

# --- Chart Styling (Dark Financial Theme) ---
fig.update_layout(
    height=500,
    paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=10, r=10, t=20, b=10),
    xaxis=dict(fixedrange=True, showgrid=False, color='#9CA3AF'),
    yaxis=dict(fixedrange=True, showgrid=True, gridcolor='#374151', color='#9CA3AF'),
    yaxis2=dict(
        fixedrange=True, 
        showgrid=True, 
        gridcolor='#374151', 
        color='#9CA3AF', 
        range=[0, 100]
    ),
    showlegend=False,
    hovermode="x unified"
)

# Render chart
st.plotly_chart(
    fig, 
    use_container_width=True,
    config={
        'displayModeBar': False,
        'staticPlot': False,
        'scrollZoom': False
    }
)


# ==========================================
# 📊 RAW DATA VIEWER (Collapsible)
# ==========================================

with st.expander("🔍 View Raw Tactical Data"):
    # Select relevant columns
    cols = ['SPY', 'QQQ', 'RSI', 'Lower_Band', 'Drawdown']
    display_df = df[cols].tail(10)
    
    # Apply styling
    def highlight_rsi(val):
        """Highlight RSI values below 30 with dark red background"""
        return 'background-color: #450a0a' if val < 30 else ''
    
    styled_df = display_df.style.format("{:.2f}").applymap(
        highlight_rsi, 
        subset=['RSI']
    )
    
    st.dataframe(styled_df, use_container_width=True)


# ==========================================
# 📝 FOOTER
# ==========================================

st.markdown("---")
st.caption(
    "🐼 PANDA COMMANDER | "
    "Data: Yahoo Finance | "
    "Refresh: Every 30 min"
)
