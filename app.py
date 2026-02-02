import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from pandas.tseries.offsets import BMonthEnd

# ==========================================
# 0. 辅助函数
# ==========================================
def get_rebalance_info():
    today = pd.Timestamp(datetime.now().date())
    offset = BMonthEnd()
    month_end = offset.rollforward(today)
    is_rebalance_day = (today == month_end)
    days_left = (month_end - today).days
    return month_end.date(), is_rebalance_day, days_left

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(page_title="Panda Strategy", page_icon="🐼", layout="wide")

st.markdown("""
    <style>
    .big-font { font-size: 24px !important; font-weight: bold; }
    .signal-box { padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; border: 2px solid #ddd;}
    .risk-on { background-color: #d4edda; color: #155724; border-color: #c3e6cb; }
    .risk-off { background-color: #f8d7da; color: #721c24; border-color: #f5c6cb; }
    .wait-mode { background-color: #fff3cd; color: #856404; border-color: #ffeeba; }
    .stAlert { margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 侧边栏
# ==========================================
st.sidebar.header("🐼 熊猫策略参数")
st.sidebar.info("策略逻辑：\n1. 进攻: 持有 QLD (2x QQQ)\n2. 防守: 持有 现金 (3% 利息)\n3. 调仓: 每月最后一天 (信号锁定)")
mom_window = st.sidebar.number_input("QQQ 动量 (天)", value=95, disabled=True)
ma_window = st.sidebar.number_input("SPY 均线 (天)", value=200, disabled=True)
cash_rate = st.sidebar.number_input("防御期现金年化 (%)", value=3.0, disabled=True)

# ==========================================
# 3. 核心逻辑 (数据处理)
# ==========================================
@st.cache_data(ttl=3600) 
def get_data_and_signal():
    tickers = ['QQQ', 'SPY'] 
    try:
        data = yf.download(tickers, start='2000-01-01', progress=False, auto_adjust=True)['Close']
        if data.empty: return None, None
        data = data.ffill()
        
        df = data.copy()
        # 1. 计算指标
        df['SPY_MA'] = df['SPY'].rolling(window=200).mean()
        df['QQQ_MOM'] = df['QQQ'].pct_change(95)

        # 2. 原始日线信号
        raw_daily_signal = ((df['SPY'] > df['SPY_MA']) & (df['QQQ_MOM'] > 0)).astype(int)
        
        # 3. 按月锁定信号 (Monthly Lock)
        monthly_signal = raw_daily_signal.resample('BME').last()
        df['Signal'] = monthly_signal.reindex(df.index).ffill()
        
        return df, data
    except Exception as e:
        st.error(f"数据错误: {e}")
        return None, None

df, raw = get_data_and_signal()

# ==========================================
# 4. 主界面
# ==========================================
st.title("🐼 Panda Strategy (Full History)")

next_rebal, is_today_rebal, days_left = get_rebalance_info()

if is_today_rebal:
    st.error(f"🔔 **醒醒！今天是调仓日！** (本月收官日)\n请在收盘前检查信号并执行操作。")
else:
    st.info(f"💤 **冬眠模式** (信号锁定中) | 下次唤醒: **{next_rebal}** (还有 {days_left} 天)")

if df is not None:
    latest = df.iloc[-1]
    latest_date = df.index[-1].strftime('%Y-%m-%d')
    current_signal = int(latest['Signal'])
    
    st.caption(f"数据日期: {latest_date}")
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        if is_today_rebal:
            is_bull = latest['SPY'] > latest['SPY_MA']
            is_mom_up = latest['QQQ_MOM'] > 0
            if is_bull and is_mom_up:
                st.markdown(f"""<div class='signal-box risk-on'><h1>🎋 进攻 (BUY)</h1><p>目标: <b>100% QLD</b></p></div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class='signal-box risk-off'><h1>🛡️ 防守 (SELL)</h1><p>目标: <b>100% 现金</b></p></div>""", unsafe_allow_html=True)
        else:
            status_text = "进攻 (QLD)" if current_signal == 1 else "防守 (Cash)"
            color_class = "risk-on" if current_signal == 1 else "risk-off"
            st.markdown(f"""<div class='signal-box wait-mode'><h1>💤 保持现状 (Hold)</h1><p>当前持仓: <span class='{color_class}'><b>{status_text}</b></span></p></div>""", unsafe_allow_html=True)

    with col2:
        st.write("📊 **核心指标监控**")
        spy_dist = (latest['SPY'] - latest['SPY_MA']) / latest['SPY_MA']
        mom_val = latest['QQQ_MOM']
        st.metric("SPY vs 200线", f"${latest['SPY']:.0f}", f"{spy_dist*100:+.1f}%")
        st.metric("QQQ 95日动量", f"${latest['QQQ']:.0f}", f"{mom_val*100:+.1f}%")

    st.markdown("---")

    # ==========================================
    # 5. 图表
    # ==========================================
    st.subheader("📈 策略净值模拟 (含买卖点)")
    
    backtest_df = df.copy().dropna()
    backtest_df['Daily_Ret_QQQ'] = backtest_df['QQQ'].pct_change()
    backtest_df['Daily_Ret_SPY'] = backtest_df['SPY'].pct_change()
    
    daily_drag = 0.015 / 252
    backtest_df['Daily_Ret_QLD_Syn'] = backtest_df['Daily_Ret_QQQ'] * 2.0 - daily_drag
    daily_cash_ret = 0.03 / 252
    
    backtest_df['Strat_Ret'] = (
        backtest_df['Signal'].shift(1) * backtest_df['Daily_Ret_QLD_Syn'] + 
        (1 - backtest_df['Signal'].shift(1)) * daily_cash_ret
    )

    time_options = ["20年", "10年", "5年", "1年", "YTD"]
    selected_range = st.radio("回测范围:", time_options, index=0, horizontal=True)

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
        
        plot_df['Trade_Action'] = plot_df['Signal'].diff()
        buy_points = plot_df[plot_df['Trade_Action'] == 1.0]
        sell_points = plot_df[plot_df['Trade_Action'] == -1.0]

        strat_perf = (plot_df['Strat_Cum'].iloc[-1] - 1) * 100
        spy_perf = (plot_df['SPY_Cum'].iloc[-1] - 1) * 100
        st.caption(f"期间累计收益: 熊猫 **{strat_perf:+.1f}%** vs SPY **{spy_perf:+.1f}%**")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Strat_Cum'], name='Panda Strategy', line=dict(color='#2980b9', width=2)))
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SPY_Cum'], name='SPY Benchmark', line=dict(color='gray', dash='dot')))
        
        if not buy_points.empty:
            fig.add_trace(go.Scatter(x=buy_points.index, y=buy_points['Strat_Cum'], mode='markers', name='Buy QLD', marker=dict(symbol='triangle-up', size=12, color='green', line=dict(width=1, color='black'))))
        if not sell_points.empty:
            fig.add_trace(go.Scatter(x=sell_points.index, y=sell_points['Strat_Cum'], mode='markers', name='Sell (Cash)', marker=dict(symbol='triangle-down', size=12, color='red', line=dict(width=1, color='black'))))
        
        is_log = selected_range not in ["1年", "YTD"]
        fig.update_layout(height=450, margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(fixedrange=True), yaxis=dict(type='log' if is_log else 'linear', fixedrange=True, title='净值'), hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # ==========================================
    # 6. 历史交易清单 (图下方列表)
    # ==========================================
    st.markdown("### 📜 交易历史 (Transaction History)")
    st.caption("仅展示发生 **买入/卖出** 动作的月份。请关注右侧的【操作原因】。")

    # 1. 取全历史月末数据
    monthly_all = df.resample('BME').last().copy()
    
    # 2. 计算信号跳变 (1.0=买入, -1.0=卖出)
    monthly_all['Action_Diff'] = monthly_all['Signal'].diff()
    
    # 3. 筛选有动作的记录
    transactions = monthly_all[monthly_all['Action_Diff'].abs() == 1.0].sort_index(ascending=False)
    
    history_logs = []

    for date, row in transactions.iterrows():
        action_code = row['Action_Diff']
        spy_price = row['SPY']
        spy_ma = row['SPY_MA']
        qqq_mom = row['QQQ_MOM']
        
        # --- 状态判定 ---
        # 1. SPY 状态
        spy_status = "✅ 均线之上" if (spy_price > spy_ma) else f"❌ 跌破均线 ({spy_price:.0f}<{spy_ma:.0f})"
        
        # 2. QQQ 状态
        mom_status = "✅ 动量为正" if (qqq_mom > 0) else f"❌ 动量转负 ({qqq_mom:.1%})"
        
        if action_code == 1.0:
            action_label = "🟢 买入 (QLD)"
            reason_summary = "进攻信号触发"
            bg_color = 'background-color: #d4edda; color: #155724' # 绿
        else:
            action_label = "🔴 卖出 (Cash)"
            # 判断到底是谁坏了事
            fail_reasons = []
            if spy_price <= spy_ma: fail_reasons.append("趋势破位")
            if qqq_mom <= 0: fail_reasons.append("动量消失")
            reason_summary = " & ".join(fail_reasons)
            bg_color = 'background-color: #f8d7da; color: #721c24' # 红

        history_logs.append({
            "交易时间 (月底)": date.strftime('%Y-%m-%d'),
            "执行动作": action_label,
            "SPY 状态 (200线)": spy_status,
            "QQQ 状态 (动量)": mom_status,
            "核心原因": reason_summary,
            "_bg": bg_color
        })

    history_df = pd.DataFrame(history_logs)

    if not history_df.empty:
        # 样式渲染
        def highlight_row(row):
            return [row['_bg']] * len(row) if '_bg' in row else [''] * len(row)

        st.dataframe(
            history_df.drop(columns=['_bg']).style.apply(highlight_row, axis=1),
            use_container_width=True,
            hide_index=True,
            height=600 # 列表高度
        )
    else:
        st.write("暂无历史交易记录。")

else:
    st.info("🐼 熊猫正在抓取最新数据...")
