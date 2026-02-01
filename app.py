import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 1. 页面配置与样式
# ==========================================
st.set_page_config(
    page_title="QuantMo 动量策略指挥官",
    page_icon="🚀",
    layout="wide"
)

# 自定义 CSS 让界面更专业
st.markdown("""
    <style>
    .big-font { font-size: 24px !important; font-weight: bold; }
    .signal-box { padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .risk-on { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .risk-off { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 侧边栏：参数设置
# ==========================================
st.sidebar.header("⚙️ 策略参数设置")
mom_window = st.sidebar.number_input("QQQ 动量窗口 (天)", min_value=10, max_value=200, value=95)
ma_window = st.sidebar.number_input("SPY 均线窗口 (天)", min_value=50, max_value=300, value=200)
leverage = st.sidebar.selectbox("杠杆倍数 (模拟)", [1.0, 2.0, 3.0], index=1)

st.sidebar.markdown("---")
st.sidebar.info("数据来源: Yahoo Finance\n延迟: 约 15 分钟")

# ==========================================
# 3. 核心逻辑函数
# ==========================================
@st.cache_data(ttl=3600) # 缓存数据1小时，避免频繁请求
def get_data_and_signal(mom_win, ma_win):
    tickers = ['QQQ', 'SPY', 'SHY']
    #以此为起点，拉取足够长的数据以计算MA
    start_date = (datetime.now() - timedelta(days=ma_win * 2 + 500)).strftime('%Y-%m-%d')
    
    try:
        data = yf.download(tickers, start=start_date, progress=False, auto_adjust=True)['Close']
        if data.empty:
            return None, None
        
        # 填充数据
        data = data.ffill()
        
        # 计算指标
        df = data.copy()
        df['SPY_MA'] = df['SPY'].rolling(window=ma_win).mean()
        df['QQQ_MOM'] = df['QQQ'].pct_change(mom_win)
        
        # 生成每日信号 (1=Risk On, 0=Risk Off)
        df['Signal'] = ((df['SPY'] > df['SPY_MA']) & (df['QQQ_MOM'] > 0)).astype(int)
        
        return df, data
    except Exception as e:
        st.error(f"数据获取失败: {e}")
        return None, None

# ==========================================
# 4. 主界面逻辑
# ==========================================
st.title("🚀 QuantMo 动量择时指挥官")
st.markdown("策略核心: **SPY > 200日均线** (大势) + **QQQ 95日动量 > 0** (进攻)")

df, raw_data = get_data_and_signal(mom_window, ma_window)

if df is not None:
    # 获取最新数据
    latest = df.iloc[-1]
    latest_date = df.index[-1].strftime('%Y-%m-%d')
    
    # 信号判定
    is_bull = latest['SPY'] > latest['SPY_MA']
    is_mom_up = latest['QQQ_MOM'] > 0
    is_risk_on = is_bull and is_mom_up
    
    # --- 第一部分：作战指令 (The Action) ---
    st.subheader(f"📅 状态更新: {latest_date}")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if is_risk_on:
            st.markdown(f"""
                <div class='signal-box risk-on'>
                    <h1>🚀 全力进攻 (RISK ON)</h1>
                    <h3>建议持仓: QLD (2倍 QQQ) 或 TQQQ (激进)</h3>
                    <p>当前美股处于牛市且科技股动量强劲</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class='signal-box risk-off'>
                    <h1>🛡️ 空仓防守 (RISK OFF)</h1>
                    <h3>建议持仓: SHY (短债) 或 SGOV (现金)</h3>
                    <p>趋势破坏或动量不足，请持有现金等待机会</p>
                </div>
            """, unsafe_allow_html=True)

    with col2:
        st.metric(
            label="SPY vs 200均线",
            value=f"${latest['SPY']:.2f}",
            delta=f"{(latest['SPY'] - latest['SPY_MA']):.2f} ({'牛市' if is_bull else '熊市'})",
            delta_color="normal"
        )
        st.progress(min(1.0, max(0.0, 0.5 + (latest['SPY'] - latest['SPY_MA'])/latest['SPY_MA'] * 5))) # 简单的可视化条

    with col3:
        st.metric(
            label=f"QQQ {mom_window}日动量",
            value=f"${latest['QQQ']:.2f}",
            delta=f"{latest['QQQ_MOM']*100:.2f}%",
            delta_color="normal"
        )
        # 动量进度条
        st.progress(min(1.0, max(0.0, 0.5 + latest['QQQ_MOM'] * 2)))

    st.markdown("---")

    # --- 第二部分：历史回测可视化 (The Proof) ---
    st.subheader("📈 策略净值曲线 (实时模拟)")
    
    # 快速计算净值
    backtest_df = df.copy().dropna()
    backtest_df['Daily_Ret_QQQ'] = backtest_df['QQQ'].pct_change()
    backtest_df['Daily_Ret_SHY'] = backtest_df['SHY'].pct_change()
    backtest_df['Daily_Ret_SPY'] = backtest_df['SPY'].pct_change()
    
    # 策略收益计算 (昨天的信号决定今天的持仓)
    # 如果 Signal=1, 收益 = QQQ涨跌 * 杠杆; 否则 = SHY涨跌
    backtest_df['Strat_Ret'] = backtest_df['Signal'].shift(1) * (backtest_df['Daily_Ret_QQQ'] * leverage) + \
                               (1 - backtest_df['Signal'].shift(1)) * backtest_df['Daily_Ret_SHY']
    
    # 累计净值
    backtest_df['Strat_Cum'] = (1 + backtest_df['Strat_Ret']).cumprod()
    backtest_df['SPY_Cum'] = (1 + backtest_df['Daily_Ret_SPY']).cumprod()
    
    # 绘图
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Strat_Cum'], mode='lines', name=f'策略 ({leverage}x QQQ)', line=dict(color='blue', width=2)))
    fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['SPY_Cum'], mode='lines', name='SPY 基准', line=dict(color='gray', dash='dot')))
    
    fig.update_layout(title="资金增长曲线 (2000 - 至今)", xaxis_title="年份", yaxis_title="净值 (对数坐标)", yaxis_type="log", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # --- 第三部分：最近信号记录 ---
    st.subheader("📝 最近 10 天信号记录")
    recent_data = df[['SPY', 'SPY_MA', 'QQQ', 'QQQ_MOM', 'Signal']].tail(10).sort_index(ascending=False)
    
    # 格式化显示
    def format_signal(val):
        return "🟢 进攻" if val == 1 else "🔴 防守"
    
    recent_data['指令'] = recent_data['Signal'].apply(format_signal)
    recent_data['QQQ_MOM'] = (recent_data['QQQ_MOM'] * 100).map('{:,.2f}%'.format)
    recent_data['SPY状态'] = recent_data.apply(lambda x: "牛" if x['SPY'] > x['SPY_MA'] else "熊", axis=1)
    
    st.table(recent_data[['指令', 'SPY状态', 'QQQ_MOM']])

else:
    st.warning("正在初始化数据，请稍候...")
