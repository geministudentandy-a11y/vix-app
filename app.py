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
CB_DROP_THRESHOLD = 0.075 # 跌幅阈值 7.5% (根据之前的回测最优解)

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(page_title="Panda Strategy (Pro)", page_icon="🐼", layout="wide")

st.markdown("""
    <style>
    .big-font { font-size: 24px !important; font-weight: bold; }
    .signal-box { padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; border: 2px solid #ddd;}
    .risk-on { background-color: #d4edda; color: #155724; border-color: #c3e6cb; } /* QLD */
    .risk-off { background-color: #f8d7da; color: #721c24; border-color: #f5c6cb; } /* Cash */
    .meltdown { background-color: #fff3cd; color: #856404; border-color: #ffeeba; } /* QQQ (Meltdown) */
    .stAlert { margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 侧边栏
# ==========================================
st.sidebar.header("🐼 熊猫策略 (熔断增强版)")
st.sidebar.info(
    f"""
    **策略逻辑：**
    1. **进攻**: SPY > 200MA 且 QQQ动量 > 0 → 持有 **QLD**
    2. **熔断**: 若 SPY {CB_N}天跌幅 > {CB_DROP_THRESHOLD*100}% → 立即切换 **QQQ** (直到月底)
    3. **防守**: 信号失效 → 持有 **现金**
    """
)
st.sidebar.divider()
st.sidebar.caption("🛡️ 风控参数 (已锁定)")
st.sidebar.number_input("SPY 观测窗口 (天)", value=CB_N, disabled=True)
st.sidebar.number_input("熔断阈值 (%)", value=CB_DROP_THRESHOLD*100, disabled=True)
st.sidebar.number_input("现金年化回报 (%)", value=3.0, disabled=True)

# ==========================================
# 3. 核心逻辑 (数据与信号)
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
        # 计算 SPY 过去 N 天的最高价
        spy_rolling_max = df['SPY'].rolling(CB_N).max()
        # 计算回撤幅度
        df['SPY_Drop_N'] = (df['SPY'] / spy_rolling_max) - 1
        # 标记是否触发熔断 (True = 触发)
        df['CB_Trigger'] = df['SPY_Drop_N'] < -CB_DROP_THRESHOLD

        # --- C. 构建策略状态 (逐月处理) ---
        # 0 = Cash, 1 = QQQ (Meltdown), 2 = QLD (Normal Bull)
        
        # 1. 生成月初信号 (resample 到月末，然后 shift 1 作为下个月的信号)
        monthly_raw = ((df['SPY'] > df['SPY_MA']) & (df['QQQ_MOM'] > 0))
        monthly_signal = monthly_raw.resample('ME').last().shift(1) # 下个月初生效
        
        # 将月初信号映射回日线 (ffill)
        # 注意：这里需要对齐时间索引，创建一个 Position 序列
        df['Month_Key'] = df.index.to_period('M')
        monthly_signal.index = monthly_signal.index.to_period('M')
        
        # 默认持仓：根据月初信号 (True -> 2 (QLD), False -> 0 (Cash))
        df['Base_Signal'] = df['Month_Key'].map(monthly_signal).fillna(False)
        df['Position'] = np.where(df['Base_Signal'], 2, 0) # 2=QLD, 0=Cash
        
        # --- D. 注入熔断逻辑 (Intra-month Logic) ---
        # 这是一个路径依赖逻辑，我们按月循环处理 "Position == 2" 的月份
        
        # 找到所有原本持有 QLD 的月份
        bull_months = df[df['Position'] == 2]['Month_Key'].unique()
        
        for m in bull_months:
            # 获取该月的数据切片掩码
            mask = df['Month_Key'] == m
            month_data = df.loc[mask]
            
            # 检查该月是否有熔断触发
            triggers = month_data[month_data['CB_Trigger']]
            
            if not triggers.empty:
                # 找到第一个触发日
                first_trigger_date = triggers.index[0]
                
                # 触发日(含)之前持有 QLD (保持 2)
                # 触发日之后(不含) -> 切换为 QQQ (设为 1)
                # 注意：实际交易是在触发日收盘确认，次日生效，
                # 但为了回测计算简单，通常视作触发日当天依然承受了QLD的跌幅，
                # 这里的 Position = 1 代表持有 QQQ。
                
                # 将触发日之后的日子设为 1 (QQQ)
                mask_after = (df.index > first_trigger_date) & (df['Month_Key'] == m)
                df.loc[mask_after, 'Position'] = 1
        
        return df, data
    except Exception as e:
        st.error(f"数据处理错误: {e}")
        return None, None

df, raw = get_data_and_signal()

# ==========================================
# 4. 主界面：当前状态面板
# ==========================================
st.title("🐼 熊猫策略 (7.5% 熔断增强版)")

next_rebal, is_today_rebal, days_left = get_rebalance_info()

# 获取最新状态
if df is not None:
    latest = df.iloc[-1]
    latest_date = df.index[-1].strftime('%Y-%m-%d')
    current_pos = int(latest['Position']) # 0, 1, 2
    
    # 检查今天是否刚刚触发熔断
    is_just_triggered = latest['CB_Trigger']
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.caption(f"📅 数据日期: {latest_date}")
        
        if is_today_rebal:
            st.warning(f"🔔 **今天是月度调仓日！** 请在收盘前根据下月信号操作。")
            # 简单的下月预测 (仅供参考)
            next_bull = (latest['SPY'] > latest['SPY_MA']) and (latest['QQQ_MOM'] > 0)
            if next_bull:
                 st.info("🔮 下月信号预览: **进攻 (QLD)**")
            else:
                 st.info("🔮 下月信号预览: **防守 (Cash)**")

        # 状态展示卡片
        if current_pos == 2: # QLD
            st.markdown(f"""<div class='signal-box risk-on'><h1>🎋 全力进攻 (QLD)</h1><p>SPY趋势向上 | 动量充足 | 无熔断</p></div>""", unsafe_allow_html=True)
        
        elif current_pos == 1: # QQQ (Meltdown)
            st.markdown(f"""<div class='signal-box meltdown'><h1>⚠️ 熔断降级 (QQQ)</h1><p><b>熔断机制生效中</b><br>避险模式：持有 QQQ 直到月底</p></div>""", unsafe_allow_html=True)
            
        else: # Cash
            st.markdown(f"""<div class='signal-box risk-off'><h1>🛡️ 现金防守 (Cash)</h1><p>持有现金 / SHY</p></div>""", unsafe_allow_html=True)

        if is_just_triggered and current_pos != 0:
             st.error("🚨 **警报：今日触发熔断阈值！** \n建议立即将 QLD 换仓为 QQQ。")

    with col2:
        st.write("📊 **核心指标监控**")
        spy_dist = (latest['SPY'] - latest['SPY_MA']) / latest['SPY_MA']
        mom_val = latest['QQQ_MOM']
        drop_val = latest['SPY_Drop_N']
        
        st.metric("SPY vs 200线", f"${latest['SPY']:.2f}", f"{spy_dist*100:+.1f}%")
        st.metric("QQQ 95日动量", f"${latest['QQQ']:.2f}", f"{mom_val*100:+.1f}%")
        
        # 熔断仪表盘
        drop_color = "normal"
        if drop_val < -0.05: drop_color = "off" # 接近熔断显示红色
        st.metric("SPY 5日最大跌幅", f"{drop_val*100:.2f}%", f"阈值 -{CB_DROP_THRESHOLD*100}%", delta_color=drop_color)

    st.markdown("---")

    # ==========================================
    # 5. 图表：回测净值曲线
    # ==========================================
    st.subheader("📈 策略净值模拟 (含熔断演示)")
    
    # 准备回测数据
    bt_df = df.copy().dropna()
    bt_df['Ret_QQQ'] = bt_df['QQQ'].pct_change()
    bt_df['Ret_SPY'] = bt_df['SPY'].pct_change()
    
    # 合成 QLD (减去损耗)
    daily_drag = 0.015 / 252
    bt_df['Ret_QLD_Syn'] = bt_df['Ret_QQQ'] * 2.0 - daily_drag
    bt_df['Ret_Cash'] = 0.03 / 252 # 3% 年化
    
    # 计算策略收益
    # Shift 1: 昨天的 Position 决定今天的收益
    # Position: 2=QLD, 1=QQQ, 0=Cash
    pos_shifted = bt_df['Position'].shift(1).fillna(0)
    
    conditions = [
        (pos_shifted == 2), # QLD
        (pos_shifted == 1), # QQQ
        (pos_shifted == 0)  # Cash
    ]
    choices = [
        bt_df['Ret_QLD_Syn'],
        bt_df['Ret_QQQ'],
        bt_df['Ret_Cash']
    ]
    
    bt_df['Strat_Ret'] = np.select(conditions, choices, default=0.0)
    
    # 交互式时间选择
    time_tabs = st.tabs(["20年全景", "近10年", "近5年", "YTD"])
    
    def plot_perf(data_slice, key_suffix):
        if data_slice.empty: return
        
        # 计算净值
        data_slice = data_slice.copy() # Avoid SettingWithCopy
        data_slice['Strat_Cum'] = (1 + data_slice['Strat_Ret']).cumprod()
        data_slice['SPY_Cum'] = (1 + data_slice['Ret_SPY']).cumprod()
        
        # 归一化
        data_slice['Strat_Cum'] /= data_slice['Strat_Cum'].iloc[0]
        data_slice['SPY_Cum'] /= data_slice['SPY_Cum'].iloc[0]
        
        # 找出熔断点 (Position 变成 1 的日子，且前一天不是 1)
        # 注意：这里我们展示的是触发熔断的那一天
        meltdown_days = data_slice[data_slice['CB_Trigger']]
        
        # 绘图
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data_slice.index, y=data_slice['Strat_Cum'], name='Panda Strategy', line=dict(color='#2980b9', width=2)))
        fig.add_trace(go.Scatter(x=data_slice.index, y=data_slice['SPY_Cum'], name='SPY Benchmark', line=dict(color='gray', dash='dot')))
        
        # 标记熔断点
        if not meltdown_days.empty:
            fig.add_trace(go.Scatter(
                x=meltdown_days.index, 
                y=data_slice.loc[meltdown_days.index, 'Strat_Cum'],
                mode='markers',
                name='Triggered CB',
                marker=dict(symbol='x', size=8, color='red')
            ))
            
        strat_cagr = (data_slice['Strat_Cum'].iloc[-1] ** (252/len(data_slice)) - 1) * 100
        total_ret = (data_slice['Strat_Cum'].iloc[-1] - 1) * 100
        
        st.caption(f"区间收益: **{total_ret:+.1f}%** | 年化估算: **{strat_cagr:.1f}%**")
        
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0), hovermode="x unified", legend=dict(orientation="h", y=1.05))
        st.plotly_chart(fig, use_container_width=True, key=f"plot_{key_suffix}")

    end_date = bt_df.index[-1]
    
    with time_tabs[0]:
        start = end_date - pd.DateOffset(years=20)
        plot_perf(bt_df[bt_df.index >= start], "20y")
        
    with time_tabs[1]:
        start = end_date - pd.DateOffset(years=10)
        plot_perf(bt_df[bt_df.index >= start], "10y")

    with time_tabs[2]:
        start = end_date - pd.DateOffset(years=5)
        plot_perf(bt_df[bt_df.index >= start], "5y")
        
    with time_tabs[3]:
        start = pd.Timestamp(f"{end_date.year}-01-01")
        plot_perf(bt_df[bt_df.index >= start], "ytd")

    # ==========================================
    # 6. 历史熔断清单
    # ==========================================
    st.markdown("### 📜 熔断历史记录 (Recent Meltdowns)")
    st.caption(f"仅展示触发了【{CB_N}天跌幅 > {CB_DROP_THRESHOLD*100}%】的日子。这些是策略救命的关键时刻。")
    
    # 筛选熔断日
    all_triggers = df[df['CB_Trigger']].copy()
    all_triggers['Drawdown'] = all_triggers['SPY_Drop_N']
    all_triggers['Close'] = all_triggers['SPY']
    
    if not all_triggers.empty:
        # 格式化表格
        display_triggers = all_triggers[['Close', 'Drawdown']].sort_index(ascending=False)
        display_triggers['Drawdown'] = display_triggers['Drawdown'].apply(lambda x: f"{x*100:.2f}%")
        display_triggers['Close'] = display_triggers['Close'].apply(lambda x: f"${x:.2f}")
        display_triggers.index = display_triggers.index.strftime('%Y-%m-%d')
        
        st.dataframe(display_triggers.head(50), height=300, use_container_width=True)
    else:
        st.write("在选定周期内未触发熔断。")

else:
    st.info("🐼 正在初始化数据，请稍候...")
