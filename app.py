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
st.set_page_config(page_title="Panda Strategy Pro", page_icon="🐼", layout="wide")

st.markdown("""
    <style>
    .big-font { font-size: 24px !important; font-weight: bold; }
    .signal-box { padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; border: 2px solid #ddd;}
    .risk-on { background-color: #d4edda; color: #155724; border-color: #c3e6cb; }
    .risk-off { background-color: #f8d7da; color: #721c24; border-color: #f5c6cb; }
    .meltdown { background-color: #fff3cd; color: #856404; border-color: #ffeeba; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据处理与策略逻辑
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
        # 下载数据
        data = yf.download(tickers, start='2000-01-01', progress=False, auto_adjust=True)['Close']
        if data.empty: return None, None
        data = data.ffill()
        df = data.copy()
        
        # --- A. 计算指标 ---
        df['SPY_MA'] = df['SPY'].rolling(window=200).mean()
        df['QQQ_MOM'] = df['QQQ'].pct_change(95)
        
        # --- B. 熔断指标 ---
        spy_rolling_max = df['SPY'].rolling(CB_N).max()
        df['SPY_Drop_N'] = (df['SPY'] / spy_rolling_max) - 1
        df['CB_Trigger'] = df['SPY_Drop_N'] < -CB_DROP_THRESHOLD

        # --- C. 构建策略状态 (0=Cash, 1=QQQ, 2=QLD) ---
        # 1. 月初基础信号
        monthly_raw = ((df['SPY'] > df['SPY_MA']) & (df['QQQ_MOM'] > 0))
        monthly_signal = monthly_raw.resample('ME').last().shift(1) # 下月生效
        
        df['Month_Key'] = df.index.to_period('M')
        monthly_signal.index = monthly_signal.index.to_period('M')
        df['Base_Signal'] = df['Month_Key'].map(monthly_signal).fillna(False)
        df['Position'] = np.where(df['Base_Signal'], 2, 0) # 默认为 2(QLD) 或 0(Cash)
        
        # 2. 注入熔断逻辑 (修正仓位)
        bull_months = df[df['Position'] == 2]['Month_Key'].unique()
        for m in bull_months:
            mask = df['Month_Key'] == m
            month_data = df.loc[mask]
            triggers = month_data[month_data['CB_Trigger']]
            
            if not triggers.empty:
                first_trigger_date = triggers.index[0]
                # 触发日之后(不含) -> 切换为 QQQ (1)
                mask_after = (df.index > first_trigger_date) & (df['Month_Key'] == m)
                df.loc[mask_after, 'Position'] = 1
        
        return df, data
    except Exception as e:
        st.error(f"数据处理错误: {e}")
        return None, None

df, raw = get_data_and_signal()

# ==========================================
# 3. 辅助绘制函数 (图表+表格)
# ==========================================
def render_analysis_tab(full_df, start_date, key_suffix):
    """渲染单个时间选项卡的内容：净值图 + 对应的交易记录表"""
    
    # 1. 数据切片
    df_slice = full_df[full_df.index >= start_date].copy()
    if df_slice.empty:
        st.warning("该时间段无数据。")
        return

    # --- A. 绘制净值图 ---
    # 计算每日收益
    df_slice['Ret_QQQ'] = df_slice['QQQ'].pct_change()
    df_slice['Ret_SPY'] = df_slice['SPY'].pct_change()
    daily_drag = 0.015 / 252
    df_slice['Ret_QLD_Syn'] = df_slice['Ret_QQQ'] * 2.0 - daily_drag
    df_slice['Ret_Cash'] = 0.03 / 252 

    # 根据昨日持仓计算今日策略收益
    pos_shifted = df_slice['Position'].shift(1).fillna(0)
    conditions = [(pos_shifted == 2), (pos_shifted == 1), (pos_shifted == 0)]
    choices = [df_slice['Ret_QLD_Syn'], df_slice['Ret_QQQ'], df_slice['Ret_Cash']]
    df_slice['Strat_Ret'] = np.select(conditions, choices, default=0.0)

    # 净值归一化
    df_slice['Strat_Cum'] = (1 + df_slice['Strat_Ret']).cumprod()
    df_slice['SPY_Cum'] = (1 + df_slice['Ret_SPY']).cumprod()
    df_slice['Strat_Cum'] /= df_slice['Strat_Cum'].iloc[0]
    df_slice['SPY_Cum'] /= df_slice['SPY_Cum'].iloc[0]

    # 绘图
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['Strat_Cum'], name='Panda Strategy', line=dict(color='#2980b9', width=2)))
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['SPY_Cum'], name='SPY Benchmark', line=dict(color='gray', dash='dot')))
    
    # 标记熔断点 (Position 变为 1 的点)
    # 逻辑：今天 Pos=1 且 昨天 Pos=2，说明是熔断切换的第一天
    meltdowns = df_slice[(df_slice['Position'] == 1) & (df_slice['Position'].shift(1) == 2)]
    if not meltdowns.empty:
        fig.add_trace(go.Scatter(x=meltdowns.index, y=df_slice.loc[meltdowns.index, 'Strat_Cum'], mode='markers', name='熔断触发', marker=dict(symbol='x', size=8, color='red')))

    total_ret = (df_slice['Strat_Cum'].iloc[-1] - 1) * 100
    try:
        cagr = (df_slice['Strat_Cum'].iloc[-1] ** (252/len(df_slice)) - 1) * 100
    except:
        cagr = 0.0
    
    st.caption(f"📈 区间收益: **{total_ret:+.1f}%** | 年化: **{cagr:.1f}%**")
    fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified", legend=dict(orientation="h", y=1.05))
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{key_suffix}")

    # --- B. 生成交易记录表 (在该时间段内) ---
    st.markdown("#### 📜 交易明细 (Transaction Log)")
    
    # 找出仓位变化的日期
    # Position: 2=QLD, 1=QQQ, 0=Cash
    df_slice['Prev_Pos'] = df_slice['Position'].shift(1).fillna(df_slice['Position'].iloc[0])
    trades = df_slice[df_slice['Position'] != df_slice['Prev_Pos']].copy()
    
    if not trades.empty:
        records = []
        for date, row in trades.iterrows():
            curr = int(row['Position'])
            prev = int(row['Prev_Pos'])
            price_spy = row['SPY']
            
            # 动作判断逻辑
            action_type = ""
            desc = ""
            color = ""
            
            if prev == 0 and curr == 2:
                action_type = "🟢 买入"
                desc = "进攻信号确认 (Cash -> QLD)"
                color = "#d4edda" # Green
            elif prev == 2 and curr == 0:
                action_type = "🔴 卖出"
                desc = "趋势转弱/动量消失 (QLD -> Cash)"
                color = "#f8d7da" # Red
            elif prev == 2 and curr == 1:
                action_type = "⚠️ 熔断"
                desc = f"触发跌幅阈值 (QLD -> QQQ)"
                color = "#fff3cd" # Yellow
            elif prev == 1 and curr == 2:
                action_type = "🔄 复位"
                desc = "月初重置为进攻 (QQQ -> QLD)"
                color = "#d1ecf1" # Blue
            elif prev == 1 and curr == 0:
                action_type = "🔴 卖出"
                desc = "月初转为防守 (QQQ -> Cash)"
                color = "#f8d7da" # Red
            
            records.append({
                "日期": date.strftime('%Y-%m-%d'),
                "动作": action_type,
                "详情": desc,
                "SPY价格": f"${price_spy:.2f}",
                "_bg": f"background-color: {color}"
            })
            
        # 倒序显示，最近的在最上面
        record_df = pd.DataFrame(records).iloc[::-1]
        
        # 样式渲染函数
        def highlight_row(row):
            return [row['_bg']] * len(row)

        st.dataframe(
            record_df.drop(columns=['_bg']).style.apply(highlight_row, axis=1),
            use_container_width=True,
            height=300,
            hide_index=True
        )
    else:
        st.info("在此选定时间段内无仓位调整。")

# ==========================================
# 4. 主界面布局
# ==========================================
st.title("🐼 熊猫策略 (7.5% 熔断版)")

next_rebal, is_today_rebal, days_left = get_rebalance_info()

if df is not None:
    latest = df.iloc[-1]
    current_pos = int(latest['Position'])
    
    # --- 顶部状态栏 ---
    col1, col2 = st.columns([3, 2])
    with col1:
        if is_today_rebal:
            st.warning(f"🔔 **调仓日提醒**")
        
        # 状态卡片
        if current_pos == 2:
            st.markdown(f"""<div class='signal-box risk-on'><h1>🎋 全力进攻 (QLD)</h1><p>SPY趋势向上 | 动量充足</p></div>""", unsafe_allow_html=True)
        elif current_pos == 1:
            st.markdown(f"""<div class='signal-box meltdown'><h1>⚠️ 熔断降级 (QQQ)</h1><p>避险模式生效中 | 持有QQQ至月底</p></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class='signal-box risk-off'><h1>🛡️ 现金防守 (Cash)</h1><p>空仓等待机会</p></div>""", unsafe_allow_html=True)

    with col2:
        st.write("**核心指标**")
        st.metric("SPY 5日跌幅", f"{latest['SPY_Drop_N']*100:.2f}%", f"阈值 -{CB_DROP_THRESHOLD*100}%", 
                  delta_color="off" if latest['SPY_Drop_N'] < -0.05 else "normal")
        st.metric("当前策略仓位", ["现金 (Cash)", "QQQ (熔断态)", "QLD (进攻态)"][current_pos])

    st.divider()

    # --- 选项卡与内容渲染 ---
    # 增加 "近1年" 选项
    tabs = st.tabs(["20年全景", "近10年", "近5年", "近1年", "YTD"])
    
    end_date = df.index[-1]
    
    with tabs[0]: # 20年
        start = end_date - pd.DateOffset(years=20)
        render_analysis_tab(df, start, "20y")
        
    with tabs[1]: # 10年
        start = end_date - pd.DateOffset(years=10)
        render_analysis_tab(df, start, "10y")
        
    with tabs[2]: # 5年
        start = end_date - pd.DateOffset(years=5)
        render_analysis_tab(df, start, "5y")
        
    with tabs[3]: # 1年 (新增)
        start = end_date - pd.DateOffset(years=1)
        render_analysis_tab(df, start, "1y")

    with tabs[4]: # YTD
        start = pd.Timestamp(f"{end_date.year}-01-01")
        render_analysis_tab(df, start, "ytd")

else:
    st.info("数据正在加载中...")
