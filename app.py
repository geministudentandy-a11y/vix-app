import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from pandas.tseries.offsets import BMonthEnd

# ==========================================
# 0. 核心参数 (黄金参数)
# ==========================================
CB_N = 5                  # 过去 N 天
CB_DROP_THRESHOLD = 0.075 # 跌幅阈值 7.5%

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(page_title="Panda Strategy (ASX Version)", page_icon="🐨", layout="wide")

st.markdown("""
    <style>
    .big-font { font-size: 24px !important; font-weight: bold; }
    .signal-box { padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; border: 2px solid #ddd;}
    .risk-on { background-color: #d4edda; color: #155724; border-color: #c3e6cb; }
    .risk-off { background-color: #f8d7da; color: #721c24; border-color: #f5c6cb; }
    .meltdown { background-color: #fff3cd; color: #856404; border-color: #ffeeba; }
    .stRadio > div {flex-direction: row;} /* 横向排列 Radio */
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 侧边栏
# ==========================================
st.sidebar.header("🐨 熊猫策略 (ASX版)")
st.sidebar.info(
    f"""
    **策略逻辑：**
    1. **进攻 (LNAS)**: SPY > 200MA & HNDQ动量 > 0
    2. **熔断 (HNDQ)**: 5天跌幅 > 7.5% (当月强制降级)
    3. **防守 (Cash)**: 信号失效
    """
)
st.sidebar.divider()
st.sidebar.number_input("SPY 观测窗口", value=CB_N, disabled=True)
st.sidebar.number_input("熔断阈值 (%)", value=CB_DROP_THRESHOLD*100, disabled=True)

# ==========================================
# 3. 数据处理 (带熔断逻辑)
# ==========================================
def get_rebalance_info():
    today = pd.Timestamp(datetime.now().date())
    offset = BMonthEnd()
    month_end = offset.rollforward(today)
    is_rebalance_day = (today == month_end)
    days_left = (month_end - today).days
    return month_end.date(), is_rebalance_day, days_left

@st.cache_data(ttl=3600) 
def get_data_and_signal():
    # 注意：底层数据依然使用 SPY/QQQ 以获取长历史数据进行模拟
    tickers = ['QQQ', 'SPY'] 
    try:
        data = yf.download(tickers, start='2000-01-01', progress=False, auto_adjust=True)['Close']
        if data.empty: return None, None
        data = data.ffill()
        df = data.copy()
        
        # --- A. 基础指标 ---
        df['SPY_MA'] = df['SPY'].rolling(window=200).mean()
        df['QQQ_MOM'] = df['QQQ'].pct_change(95)
        
        # --- B. 熔断指标 ---
        spy_rolling_max = df['SPY'].rolling(CB_N).max()
        df['SPY_Drop_N'] = (df['SPY'] / spy_rolling_max) - 1
        df['CB_Trigger'] = df['SPY_Drop_N'] < -CB_DROP_THRESHOLD

        # --- C. 构建仓位 (0=Cash, 1=HNDQ, 2=LNAS) ---
        # 1. 月初基础信号
        monthly_raw = ((df['SPY'] > df['SPY_MA']) & (df['QQQ_MOM'] > 0))
        monthly_signal = monthly_raw.resample('ME').last().shift(1)
        
        df['Month_Key'] = df.index.to_period('M')
        monthly_signal.index = monthly_signal.index.to_period('M')
        df['Base_Signal'] = df['Month_Key'].map(monthly_signal).fillna(False)
        
        # 初始：进攻(2) 或 防守(0)
        df['Position'] = np.where(df['Base_Signal'], 2, 0)
        
        # 2. 注入熔断 (修改为 1)
        bull_months = df[df['Position'] == 2]['Month_Key'].unique()
        for m in bull_months:
            mask = df['Month_Key'] == m
            month_data = df.loc[mask]
            triggers = month_data[month_data['CB_Trigger']]
            
            if not triggers.empty:
                first_trigger_date = triggers.index[0]
                # 触发日之后 -> 切 HNDQ (1)
                mask_after = (df.index > first_trigger_date) & (df['Month_Key'] == m)
                df.loc[mask_after, 'Position'] = 1
        
        return df, data
    except Exception as e:
        st.error(f"数据错误: {e}")
        return None, None

df, raw = get_data_and_signal()

# ==========================================
# 4. 主界面逻辑
# ==========================================
st.title("🐨 Panda Strategy (LNAS/HNDQ Version)")

next_rebal, is_today_rebal, days_left = get_rebalance_info()

if is_today_rebal:
    st.error(f"🔔 **醒醒！今天是调仓日！** (本月收官日)\n请在收盘前检查信号并执行操作。")
else:
    st.info(f"💤 **冬眠模式** (信号锁定中) | 下次唤醒: **{next_rebal}** (还有 {days_left} 天)")

if df is not None:
    latest = df.iloc[-1]
    latest_date = df.index[-1].strftime('%Y-%m-%d')
    current_pos = int(latest['Position']) # 0, 1, 2
    
    st.caption(f"数据日期: {latest_date} (基于美股收盘数据计算信号)")
    
    # --- 顶部状态栏 ---
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # 根据 Position 状态显示不同颜色的盒子
        if current_pos == 2: # LNAS (2x)
            st.markdown(f"""<div class='signal-box risk-on'><h1>🎋 进攻 (BUY LNAS)</h1><p>SPY趋势向上 & 动量充足</p></div>""", unsafe_allow_html=True)
        elif current_pos == 1: # HNDQ (1x Meltdown)
            st.markdown(f"""<div class='signal-box meltdown'><h1>⚠️ 熔断降级 (HOLD HNDQ)</h1><p><b>触发风控！</b> 短期避险模式</p></div>""", unsafe_allow_html=True)
        else: # Cash
            st.markdown(f"""<div class='signal-box risk-off'><h1>🛡️ 防守 (SELL -> CASH)</h1><p>空仓等待机会</p></div>""", unsafe_allow_html=True)

    with col2:
        st.write("📊 **核心指标监控**")
        spy_dist = (latest['SPY'] - latest['SPY_MA']) / latest['SPY_MA']
        mom_val = latest['QQQ_MOM']
        drop_val = latest['SPY_Drop_N']
        
        st.metric("SPY vs 200线", f"${latest['SPY']:.0f}", f"{spy_dist*100:+.1f}%")
        st.metric("HNDQ 95日动量", f"${latest['QQQ']:.0f}", f"{mom_val*100:+.1f}%")
        # 熔断监控
        delta_color = "off" if drop_val < -0.05 else "normal"
        st.metric("SPY 5日跌幅 (熔断线 -7.5%)", f"{drop_val*100:.2f}%", delta_color=delta_color)

    st.markdown("---")

    # ==========================================
    # 5. 图表与回测
    # ==========================================
    st.subheader("📈 策略净值模拟")

    # 准备回测数据
    backtest_df = df.copy().dropna()
    backtest_df['Ret_QQQ'] = backtest_df['QQQ'].pct_change()
    backtest_df['Ret_SPY'] = backtest_df['SPY'].pct_change()
    
    # 模拟澳洲 ETF: LNAS 约为 QQQ 的 2倍 (减去损耗), HNDQ 约为 QQQ 1倍
    daily_drag = 0.015 / 252
    backtest_df['Ret_LNAS_Syn'] = backtest_df['Ret_QQQ'] * 2.0 - daily_drag
    backtest_df['Ret_HNDQ_Syn'] = backtest_df['Ret_QQQ'] # 简单假设 HNDQ 紧跟 NDQ100
    backtest_df['Ret_Cash'] = 0.03 / 252

    # 计算每日策略收益
    pos_shifted = backtest_df['Position'].shift(1).fillna(0)
    conditions = [(pos_shifted == 2), (pos_shifted == 1), (pos_shifted == 0)]
    choices = [backtest_df['Ret_LNAS_Syn'], backtest_df['Ret_HNDQ_Syn'], backtest_df['Ret_Cash']]
    backtest_df['Strat_Ret'] = np.select(conditions, choices, default=0.0)

    # --- 时间选择 ---
    time_options = ["20年", "10年", "5年", "1年", "YTD"]
    selected_range = st.radio("回测范围:", time_options, index=1, horizontal=True)

    end_date = backtest_df.index[-1]
    if selected_range == "20年": start = end_date - pd.DateOffset(years=20)
    elif selected_range == "10年": start = end_date - pd.DateOffset(years=10)
    elif selected_range == "5年": start = end_date - pd.DateOffset(years=5)
    elif selected_range == "1年": start = end_date - pd.DateOffset(years=1)
    else: start = pd.Timestamp(f"{end_date.year}-01-01")
    
    plot_df = backtest_df[backtest_df.index >= start].copy()

    if not plot_df.empty:
        # 归一化
        plot_df['Strat_Cum'] = (1 + plot_df['Strat_Ret']).cumprod()
        plot_df['SPY_Cum'] = (1 + plot_df['Ret_SPY']).cumprod()
        plot_df['Strat_Cum'] /= plot_df['Strat_Cum'].iloc[0]
        plot_df['SPY_Cum'] /= plot_df['SPY_Cum'].iloc[0]

        # 累计收益显示
        strat_perf = (plot_df['Strat_Cum'].iloc[-1] - 1) * 100
        spy_perf = (plot_df['SPY_Cum'].iloc[-1] - 1) * 100
        st.caption(f"期间累计收益: 熊猫策略 **{strat_perf:+.1f}%** vs SPY基准 **{spy_perf:+.1f}%**")

        # --- 绘图 ---
        fig = go.Figure()
        # 1. 策略线
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Strat_Cum'], name='Panda Strategy', line=dict(color='#2980b9', width=2)))
        # 2. SPY 基准线
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SPY_Cum'], name='SPY Benchmark', line=dict(color='gray', dash='dot')))

        # 3. 标记点
        plot_df['Prev_Pos'] = plot_df['Position'].shift(1)
        # 买入 (0/1 -> 2)
        buy_pts = plot_df[(plot_df['Position'] == 2) & (plot_df['Prev_Pos'] != 2)]
        # 卖出 (2/1 -> 0)
        sell_pts = plot_df[(plot_df['Position'] == 0) & (plot_df['Prev_Pos'] != 0)]
        # 熔断 (2 -> 1)
        melt_pts = plot_df[(plot_df['Position'] == 1) & (plot_df['Prev_Pos'] == 2)]

        if not buy_pts.empty:
            fig.add_trace(go.Scatter(x=buy_pts.index, y=buy_pts['Strat_Cum'], mode='markers', name='Buy LNAS', marker=dict(symbol='triangle-up', size=12, color='green', line=dict(width=1, color='black'))))
        if not sell_pts.empty:
            fig.add_trace(go.Scatter(x=sell_pts.index, y=sell_pts['Strat_Cum'], mode='markers', name='Sell (Cash)', marker=dict(symbol='triangle-down', size=12, color='red', line=dict(width=1, color='black'))))
        if not melt_pts.empty:
            fig.add_trace(go.Scatter(x=melt_pts.index, y=melt_pts['Strat_Cum'], mode='markers', name='Meltdown (HNDQ)', marker=dict(symbol='x', size=10, color='orange', line=dict(width=1, color='black'))))

        is_log = selected_range not in ["1年", "YTD"]
        fig.update_layout(height=450, margin=dict(l=10, r=10, t=30, b=10), 
                          xaxis=dict(fixedrange=True), 
                          yaxis=dict(type='log' if is_log else 'linear', fixedrange=True, title='净值'), 
                          hovermode="x unified", 
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # ==========================================
        # 6. 历史交易清单 (详细表格)
        # ==========================================
        st.markdown("### 📜 交易历史 (Transaction History)")
        st.caption("仅展示发生 **仓位变化** 的时刻 (含熔断记录)。")

        trades = plot_df[plot_df['Position'] != plot_df['Prev_Pos']].copy()
        
        if not trades.empty:
            history_logs = []
            for date, row in trades.iterrows():
                curr = int(row['Position'])
                prev = int(row['Prev_Pos']) if not pd.isna(row['Prev_Pos']) else 0
                
                spy_price = row['SPY']
                spy_ma = row['SPY_MA']
                qqq_mom = row['QQQ_MOM']
                drop_val = row['SPY_Drop_N']

                spy_txt = "✅ 均线之上" if spy_price > spy_ma else f"❌ 跌破均线 ({spy_price:.0f}<{spy_ma:.0f})"
                mom_txt = "✅ 动量为正" if qqq_mom > 0 else f"❌ 动量转负 ({qqq_mom:.1%})"
                
                action_label = ""
                reason = ""
                bg_color = ""

                # 逻辑分支
                if curr == 2: # LNAS
                    action_label = "🟢 买入 (LNAS)"
                    bg_color = "background-color: #d4edda; color: #155724"
                    if prev == 1:
                        reason = "月初复位: 信号仍有效"
                    else:
                        reason = "进攻信号触发"
                        
                elif curr == 0: # Cash
                    action_label = "🔴 卖出 (Cash)"
                    bg_color = "background-color: #f8d7da; color: #721c24"
                    fail_reasons = []
                    if spy_price <= spy_ma: fail_reasons.append("趋势破位")
                    if qqq_mom <= 0: fail_reasons.append("动量消失")
                    reason = " & ".join(fail_reasons) if fail_reasons else "信号丢失"
                    
                elif curr == 1: # HNDQ
                    action_label = "⚠️ 熔断 (HNDQ)"
                    bg_color = "background-color: #fff3cd; color: #856404"
                    reason = f"SPY 暴跌 ({drop_val*100:.1f}%)"
                    spy_txt = "⚠️ 剧烈波动"

                history_logs.append({
                    "日期": date.strftime('%Y-%m-%d'),
                    "执行动作": action_label,
                    "SPY 状态": spy_txt,
                    "HNDQ 状态": mom_txt,
                    "核心原因": reason,
                    "_bg": bg_color
                })

            history_df = pd.DataFrame(history_logs).iloc[::-1]

            def highlight_row(row):
                css = history_df.loc[row.name, '_bg']
                return [css] * len(row)

            st.dataframe(
                history_df.drop(columns=['_bg']).style.apply(highlight_row, axis=1),
                use_container_width=True,
                hide_index=True,
                height=500
            )
        else:
            st.info("该时间段内无交易。")

else:
    st.info("🐨 熊猫正在抓取最新数据...")
