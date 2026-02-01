import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pandas.tseries.offsets import BMonthEnd

# ==========================================
# 0. 辅助函数：计算调仓日逻辑
# ==========================================
def get_rebalance_info():
    today = pd.Timestamp(datetime.now().date())
    offset = BMonthEnd()
    # 本月最后一个交易日
    month_end = offset.rollforward(today)
    
    is_rebalance_day = (today == month_end)
    days_left = (month_end - today).days
    
    return month_end.date(), is_rebalance_day, days_left

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(page_title="QuantMo 终极指挥官", page_icon="🏛️", layout="wide")

# CSS 优化：增强手机端可读性
st.markdown("""
    <style>
    .big-font { font-size: 24px !important; font-weight: bold; }
    .signal-box { padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; border: 2px solid #ddd;}
    .risk-on { background-color: #d4edda; color: #155724; border-color: #c3e6cb; }
    .risk-off { background-color: #f8d7da; color: #721c24; border-color: #f5c6cb; }
    .wait-mode { background-color: #fff3cd; color: #856404; border-color: #ffeeba; }
    /* 强制在手机上显示重要信息框 */
    .stAlert { margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 侧边栏：仅保留参数 (手机上会被折叠)
# ==========================================
st.sidebar.header("⚙️ 黄金参数")
mom_window = st.sidebar.number_input("QQQ 动量 (天)", value=95, disabled=True)
ma_window = st.sidebar.number_input("SPY 均线 (天)", value=200, disabled=True)
leverage = st.sidebar.selectbox("模拟杠杆", [1.0, 2.0, 3.0], index=1)
st.sidebar.info("手机端提示：倒计时已移至主页面顶部。")

# ==========================================
# 3. 核心逻辑
# ==========================================
@st.cache_data(ttl=3600) 
def get_data_and_signal():
    tickers = ['QQQ', 'SPY', 'SHY']
    try:
        data = yf.download(tickers, start='2000-01-01', progress=False, auto_adjust=True)['Close']
        if data.empty: return None, None
        data = data.ffill()
        
        df = data.copy()
        df['SPY_MA'] = df['SPY'].rolling(window=200).mean()
        df['QQQ_MOM'] = df['QQQ'].pct_change(95)
        df['Signal'] = ((df['SPY'] > df['SPY_MA']) & (df['QQQ_MOM'] > 0)).astype(int)
        return df, data
    except Exception as e:
        st.error(f"数据错误: {e}")
        return None, None

df, raw = get_data_and_signal()

# ==========================================
# 4. 主界面 (手机端核心区)
# ==========================================
st.title("🏛️ QuantMo 指挥官")

# 【核心修改】将倒计时直接放在标题下方，手机第一眼就能看到
next_rebal, is_today_rebal, days_left = get_rebalance_info()

if is_today_rebal:
    st.error(f"🔔 **警报：就是今天！** (本月收官日)\n请在收盘前(15:50)执行操作。")
else:
    # 使用 st.info 蓝色横幅，醒目且占地小
    st.info(f"💤 **睡觉模式** | 下次调仓: **{next_rebal}** (还有 {days_left} 天)")

if df is not None:
    latest = df.iloc[-1]
    latest_date = df.index[-1].strftime('%Y-%m-%d')
    
    is_bull = latest['SPY'] > latest['SPY_MA']
    is_mom_up = latest['QQQ_MOM'] > 0
    raw_signal_risk_on = is_bull and is_mom_up
    
    st.caption(f"数据更新: {latest_date}")
    
    # --- 指挥中心 ---
    # 手机端会自动把 col1 和 col2 变成上下排列，这里不需要改代码，Streamlit 会自动适配
    col1, col2 = st.columns([3, 2])
    
    with col1:
        if is_today_rebal:
            if raw_signal_risk_on:
                st.markdown(f"""
                    <div class='signal-box risk-on'>
                        <h1>🟢 买入 / 持有</h1>
                        <p><b>今天是调仓日</b>，市场健康。</p>
                        <p>目标: <b>200% QQQ (QLD)</b></p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class='signal-box risk-off'>
                        <h1>🔴 清仓 / 防守</h1>
                        <p><b>今天是调仓日</b>，风控触发。</p>
                        <p>目标: <b>100% 现金/SHY</b></p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            status_text = "牛市 (健康)" if raw_signal_risk_on else "熊市 (脆弱)"
            color_class = "risk-on" if raw_signal_risk_on else "risk-off"
            
            st.markdown(f"""
                <div class='signal-box wait-mode'>
                    <h1>💤 建议: 睡觉 (Wait)</h1>
                    <p>非调仓日，无视波动。</p>
                    <p>当前状态: <span class='{color_class}'><b>{status_text}</b></span></p>
                </div>
            """, unsafe_allow_html=True)

    with col2:
        st.write("📊 **核心指标**")
        spy_dist = (latest['SPY'] - latest['SPY_MA']) / latest['SPY_MA']
        mom_val = latest['QQQ_MOM']
        
        st.metric("SPY vs 200线", f"${latest['SPY']:.0f}", f"{spy_dist*100:+.1f}%")
        st.metric("QQQ 95日动量", f"${latest['QQQ']:.0f}", f"{mom_val*100:+.1f}%")

    st.markdown("---")

    # --- 曲线图 ---
    st.subheader("📈 资金曲线")
    
    backtest_df = df.copy().dropna()
    backtest_df['Daily_Ret_QQQ'] = backtest_df['QQQ'].pct_change()
    backtest_df['Daily_Ret_SHY'] = backtest_df['SHY'].pct_change()
    backtest_df['Daily_Ret_SPY'] = backtest_df['SPY'].pct_change()
    
    backtest_df['Strat_Ret'] = backtest_df['Signal'].shift(1) * (backtest_df['Daily_Ret_QQQ'] * leverage) + \
                               (1 - backtest_df['Signal'].shift(1)) * backtest_df['Daily_Ret_SHY']

    time_options = ["20年", "10年", "5年", "1年", "YTD"]
    selected_range = st.radio("时间范围:", time_options, index=0, horizontal=True)

    end_date = backtest_df.index[-1]
    if selected_range == "20年": start = end_date - pd.DateOffset(years=20)
    elif selected_range == "10年": start = end_date - pd.DateOffset(years=10)
    elif selected_range == "5年": start = end_date - pd.DateOffset(years=5)
    elif selected_range == "1年": start = end_date - pd.DateOffset(years=1)
    else: start = pd.Timestamp(f"{end_date.year}-01-01")
    
    plot_df = backtest_df[backtest_df.index >= start].copy()
    
    if not plot_df.empty:
        plot_df['Strat_Cum'] = (1 + plot_df['Strat_Ret']).cumprod()
        plot_df['SPY_Cum'] = (1 + plot_df['Daily_Ret_SPY']).cumprod()
        plot_df['Strat_Cum'] /= plot_df['Strat_Cum'].iloc[0]
        plot_df['SPY_Cum'] /= plot_df['SPY_Cum'].iloc[0]
        
        strat_perf = (plot_df['Strat_Cum'].iloc[-1] - 1) * 100
        spy_perf = (plot_df['SPY_Cum'].iloc[-1] - 1) * 100
        st.caption(f"期间收益: 策略 **{strat_
