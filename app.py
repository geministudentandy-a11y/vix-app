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
st.set_page_config(page_title="Panda Strategy", page_icon="🐼", layout="wide")

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
# 2. 侧边栏：参数展示
# ==========================================
st.sidebar.header("🐼 熊猫策略参数")
st.sidebar.info("策略逻辑：\n1. 进攻: 持有 QLD (2x QQQ)\n2. 防守: 持有 现金 (3% 利息)\n3. 调仓: 每月最后一天")
mom_window = st.sidebar.number_input("QQQ 动量 (天)", value=95, disabled=True)
ma_window = st.sidebar.number_input("SPY 均线 (天)", value=200, disabled=True)
cash_rate = st.sidebar.number_input("防御期现金年化 (%)", value=3.0, disabled=True)

# ==========================================
# 3. 核心逻辑
# ==========================================
@st.cache_data(ttl=3600) 
def get_data_and_signal():
    tickers = ['QQQ', 'SPY'] # 只需要这两个，SHY已移除，QLD通过合成计算
    try:
        data = yf.download(tickers, start='2000-01-01', progress=False, auto_adjust=True)['Close']
        if data.empty: return None, None
        data = data.ffill()
        
        df = data.copy()
        # 1. 计算信号指标
        df['SPY_MA'] = df['SPY'].rolling(window=200).mean()
        df['QQQ_MOM'] = df['QQQ'].pct_change(95)
        # 2. 生成信号 (1=进攻, 0=防守)
        df['Signal'] = ((df['SPY'] > df['SPY_MA']) & (df['QQQ_MOM'] > 0)).astype(int)
        
        return df, data
    except Exception as e:
        st.error(f"数据错误: {e}")
        return None, None

df, raw = get_data_and_signal()

# ==========================================
# 4. 主界面
# ==========================================
st.title("🐼 Panda Strategy (Original)")

# 倒计时逻辑
next_rebal, is_today_rebal, days_left = get_rebalance_info()

if is_today_rebal:
    st.error(f"🔔 **醒醒！今天是调仓日！** (本月收官日)\n请在收盘前检查信号并执行操作。")
else:
    st.info(f"💤 **冬眠模式** (Holding) | 下次唤醒: **{next_rebal}** (还有 {days_left} 天)")

if df is not None:
    latest = df.iloc[-1]
    latest_date = df.index[-1].strftime('%Y-%m-%d')
    
    is_bull = latest['SPY'] > latest['SPY_MA']
    is_mom_up = latest['QQQ_MOM'] > 0
    raw_signal_risk_on = is_bull and is_mom_up
    
    st.caption(f"数据日期: {latest_date}")
    
    # --- 指挥中心 ---
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # 如果今天是调仓日，显示明确指令
        if is_today_rebal:
            if raw_signal_risk_on:
                st.markdown(f"""
                    <div class='signal-box risk-on'>
                        <h1>🎋 进攻信号 (BUY)</h1>
                        <p><b>今天是调仓日</b>，趋势向上。</p>
                        <p>目标仓位: <b>100% QLD (或 LNAS)</b></p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class='signal-box risk-off'>
                        <h1>🛡️ 防守信号 (SELL)</h1>
                        <p><b>今天是调仓日</b>，风险较高。</p>
                        <p>目标仓位: <b>100% 现金 (Cash)</b></p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            # 平时显示当前状态
            status_text = "进攻 (QLD)" if raw_signal_risk_on else "防守 (Cash)"
            color_class = "risk-on" if raw_signal_risk_on else "risk-off"
            
            st.markdown(f"""
                <div class='signal-box wait-mode'>
                    <h1>💤 保持现状 (Hold)</h1>
                    <p>今天不是月底，不要乱动。</p>
                    <p>当前应持仓: <span class='{color_class}'><b>{status_text}</b></span></p>
                </div>
            """, unsafe_allow_html=True)

    with col2:
        st.write("📊 **核心指标监控**")
        spy_dist = (latest['SPY'] - latest['SPY_MA']) / latest['SPY_MA']
        mom_val = latest['QQQ_MOM']
        
        st.metric("SPY vs 200线", f"${latest['SPY']:.0f}", f"{spy_dist*100:+.1f}%", 
                  help="SPY 在 200日均线之上才算牛市")
        st.metric("QQQ 95日动量", f"${latest['QQQ']:.0f}", f"{mom_val*100:+.1f}%",
                  help="QQQ 过去95天收益率为正才算有动量")

    st.markdown("---")

    # --- 曲线图计算 (合成 QLD + 3% 现金) ---
    st.subheader("📈 策略净值模拟")
    
    backtest_df = df.copy().dropna()
    
    # 1. 计算 QQQ 日涨跌幅
    backtest_df['Daily_Ret_QQQ'] = backtest_df['QQQ'].pct_change()
    
    # 2. 合成 QLD 收益 (2倍 QQQ - 1.5% 年化损耗)
    daily_drag = 0.015 / 252
    backtest_df['Daily_Ret_QLD_Syn'] = backtest_df['Daily_Ret_QQQ'] * 2.0 - daily_drag
    
    # 3. 现金收益 (3% 年化固定)
    daily_cash_ret = 0.03 / 252
    
    # 4. 策略收益计算 (昨日信号决定今日持仓)
    # Signal=1 -> 持有 QLD_Syn; Signal=0 -> 持有 Cash
    backtest_df['Strat_Ret'] = backtest_df['Signal'].shift(1) * backtest_df['Daily_Ret_QLD_Syn'] + \
                               (1 - backtest_df['Signal'].shift(1)) * daily_cash_ret
    
    # 5. SPY 基准收益
    backtest_df['Daily_Ret_SPY'] = backtest_df['SPY'].pct_change()

    # 时间筛选
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
        # 计算净值曲线
        plot_df['Strat_Cum'] = (1 + plot_df['Strat_Ret']).cumprod()
        plot_df['SPY_Cum'] = (1 + plot_df['Daily_Ret_SPY']).cumprod()
        
        # 归一化
        plot_df['Strat_Cum'] /= plot_df['Strat_Cum'].iloc[0]
        plot_df['SPY_Cum'] /= plot_df['SPY_Cum'].iloc[0]
        
        strat_perf = (plot_df['Strat_Cum'].iloc[-1] - 1) * 100
        spy_perf = (plot_df['SPY_Cum'].iloc[-1] - 1) * 100
        
        st.caption(f"期间累计收益: 熊猫策略 **{strat_perf:+.1f}%** vs SPY基准 **{spy_perf:+.1f}%**")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Strat_Cum'], name='Panda Strategy', line=dict(color='#2980b9', width=2)))
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SPY_Cum'], name='SPY (Benchmark)', line=dict(color='gray', dash='dot')))
        
        is_log = selected_range not in ["1年", "YTD"]
        fig.update_layout(
            height=400, 
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(fixedrange=True), 
            yaxis=dict(type='log' if is_log else 'linear', fixedrange=True, title='净值 (Log)' if is_log else '净值'), 
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.info("🐼 熊猫正在抓取最新数据...")
