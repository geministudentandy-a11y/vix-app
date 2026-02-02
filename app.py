import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
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
st.set_page_config(page_title="Panda Strategy", page_icon="🐼", layout="wide")

# CSS 优化
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
# 3. 核心逻辑 (含月度锁定)
# ==========================================
@st.cache_data(ttl=3600) 
def get_data_and_signal():
    tickers = ['QQQ', 'SPY'] 
    try:
        data = yf.download(tickers, start='2000-01-01', progress=False, auto_adjust=True)['Close']
        if data.empty: return None, None
        data = data.ffill()
        
        df = data.copy()
        # 1. 计算基础指标
        df['SPY_MA'] = df['SPY'].rolling(window=200).mean()
        df['QQQ_MOM'] = df['QQQ'].pct_change(95)

        # 2. 生成原始日线信号
        raw_daily_signal = ((df['SPY'] > df['SPY_MA']) & (df['QQQ_MOM'] > 0)).astype(int)
        
        # 3. 【核心修改】按月锁定信号 (Monthly Lock)
        # 只取每个月最后一个交易日的信号，并向后填充整个月
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
st.title("🐼 Panda Strategy (Monthly Locked)")

next_rebal, is_today_rebal, days_left = get_rebalance_info()

if is_today_rebal:
    st.error(f"🔔 **醒醒！今天是调仓日！** (本月收官日)\n请在收盘前检查信号并执行操作。")
else:
    st.info(f"💤 **冬眠模式** (信号锁定中) | 下次唤醒: **{next_rebal}** (还有 {days_left} 天)")

if df is not None:
    latest = df.iloc[-1]
    latest_date = df.index[-1].strftime('%Y-%m-%d')
    
    # 这里的信号已经是 ffill 过的，直接取就是当前生效的信号
    current_signal = int(latest['Signal'])
    
    st.caption(f"数据日期: {latest_date}")
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        if is_today_rebal:
            # 调仓日：看最新的实时指标判断
            # 注意：调仓日我们要看"今天收盘"的原始信号，而不是昨天的锁定信号
            is_bull = latest['SPY'] > latest['SPY_MA']
            is_mom_up = latest['QQQ_MOM'] > 0
            live_signal = is_bull and is_mom_up
            
            if live_signal:
                st.markdown(f"""
                    <div class='signal-box risk-on'>
                        <h1>🎋 进攻信号 (BUY)</h1>
                        <p><b>今天是调仓日</b>，趋势向上。</p>
                        <p>目标仓位: <b>100% QLD</b></p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class='signal-box risk-off'>
                        <h1>🛡️ 防守信号 (SELL)</h1>
                        <p><b>今天是调仓日</b>，风险较高。</p>
                        <p>目标仓位: <b>100% 现金</b></p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            # 非调仓日：显示当前锁定的持仓
            status_text = "进攻 (QLD)" if current_signal == 1 else "防守 (Cash)"
            color_class = "risk-on" if current_signal == 1 else "risk-off"
            
            st.markdown(f"""
                <div class='signal-box wait-mode'>
                    <h1>💤 保持现状 (Hold)</h1>
                    <p>当前处于信号锁定周期。</p>
                    <p>当前持仓: <span class='{color_class}'><b>{status_text}</b></span></p>
                </div>
            """, unsafe_allow_html=True)

    with col2:
        st.write("📊 **核心指标监控**")
        spy_dist = (latest['SPY'] - latest['SPY_MA']) / latest['SPY_MA']
        mom_val = latest['QQQ_MOM']
        
        st.metric("SPY vs 200线", f"${latest['SPY']:.0f}", f"{spy_dist*100:+.1f}%")
        st.metric("QQQ 95日动量", f"${latest['QQQ']:.0f}", f"{mom_val*100:+.1f}%")

    st.markdown("---")

    # ==========================================
    # 5. 交互式图表 (带买卖点标记)
    # ==========================================
    st.subheader("📈 策略净值模拟 (含买卖点)")
    
    backtest_df = df.copy().dropna()
    
    # 1. 收益计算
    backtest_df['Daily_Ret_QQQ'] = backtest_df['QQQ'].pct_change()
    backtest_df['Daily_Ret_SPY'] = backtest_df['SPY'].pct_change()
    
    daily_drag = 0.015 / 252
    backtest_df['Daily_Ret_QLD_Syn'] = backtest_df['Daily_Ret_QQQ'] * 2.0 - daily_drag
    daily_cash_ret = 0.03 / 252
    
    # 策略收益
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
        
        # 归一化
        plot_df['Strat_Cum'] /= plot_df['Strat_Cum'].iloc[0]
        plot_df['SPY_Cum'] /= plot_df['SPY_Cum'].iloc[0]
        
        # --- 寻找买卖点 (Plotly Markers) ---
        plot_df['Trade_Action'] = plot_df['Signal'].diff()
        buy_points = plot_df[plot_df['Trade_Action'] == 1.0]
        sell_points = plot_df[plot_df['Trade_Action'] == -1.0]

        strat_perf = (plot_df['Strat_Cum'].iloc[-1] - 1) * 100
        spy_perf = (plot_df['SPY_Cum'].iloc[-1] - 1) * 100
        st.caption(f"期间累计收益: 熊猫 **{strat_perf:+.1f}%** vs SPY **{spy_perf:+.1f}%**")

        fig = go.Figure()
        
        # 1. 策略线
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Strat_Cum'], name='Panda Strategy', line=dict(color='#2980b9', width=2)))
        # 2. 基准线
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SPY_Cum'], name='SPY Benchmark', line=dict(color='gray', dash='dot')))
        
        # 3. 买入点 (绿色三角)
        if not buy_points.empty:
            fig.add_trace(go.Scatter(
                x=buy_points.index, y=buy_points['Strat_Cum'],
                mode='markers', name='Buy QLD',
                marker=dict(symbol='triangle-up', size=12, color='green', line=dict(width=1, color='black'))
            ))
            
        # 4. 卖出点 (红色三角)
        if not sell_points.empty:
            fig.add_trace(go.Scatter(
                x=sell_points.index, y=sell_points['Strat_Cum'],
                mode='markers', name='Sell (Cash)',
                marker=dict(symbol='triangle-down', size=12, color='red', line=dict(width=1, color='black'))
            ))
        
        is_log = selected_range not in ["1年", "YTD"]
        fig.update_layout(
            height=450, 
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(fixedrange=True), 
            yaxis=dict(type='log' if is_log else 'linear', fixedrange=True, title='净值'), 
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # ==========================================
    # 6. 交易日志审计 (Audit Log)
    # ==========================================
    st.markdown("---")
    st.subheader("📋 交易信号审计 (Audit Log)")
    st.caption("最近13个月的月末信号检查记录 (每月锁定)。")

    # 提取月末数据
    monthly_audit = df.resample('BME').last().iloc[-13:].copy()
    
    audit_logs = []

    for i in range(1, len(monthly_audit)):
        curr_date = monthly_audit.index[i]
        curr_row = monthly_audit.iloc[i]
        prev_row = monthly_audit.iloc[i-1]
        
        spy_price = curr_row['SPY']
        spy_ma = curr_row['SPY_MA']
        qqq_mom = curr_row['QQQ_MOM']
        
        curr_signal = int(curr_row['Signal'])
        prev_signal = int(prev_row['Signal'])
        
        if curr_signal == 1 and prev_signal == 0:
            action = "🟢 买入 (QLD)"
        elif curr_signal == 0 and prev_signal == 1:
            action = "🔴 卖出 (Cash)"
        elif curr_signal == 1 and prev_signal == 1:
            action = "🔒 锁仓 (Hold)"
        else:
            action = "🛡️ 空仓 (Wait)"

        reason_spy = "✅ SPY > 200线" if (spy_price > spy_ma) else f"❌ SPY破位 ({spy_price:.0f}<{spy_ma:.0f})"
        reason_mom = "✅ QQQ动量正" if (qqq_mom > 0) else f"❌ QQQ动量负 ({qqq_mom:.1%})"

        audit_logs.append({
            "日期": curr_date.strftime('%Y-%m-%d'),
            "动作": action,
            "SPY状态": reason_spy,
            "QQQ状态": reason_mom,
            "当前持仓": "QLD" if curr_signal else "Cash"
        })

    audit_df = pd.DataFrame(audit_logs).sort_values("日期", ascending=False)

    def highlight_action(val):
        color = ''
        if '买入' in val: color = 'background-color: #d4edda; color: #155724'
        elif '卖出' in val: color = 'background-color: #f8d7da; color: #721c24'
        elif '锁仓' in val: color = 'background-color: #e2e3e5'
        elif '空仓' in val: color = 'color: #856404'
        return color

    st.dataframe(
        audit_df.style.map(highlight_action, subset=['动作']),
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("🐼 熊猫正在抓取最新数据...")
