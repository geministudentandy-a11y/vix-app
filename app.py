import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import requests
import altair as alt
import json
from github import Github

# ==========================================
# 1. 页面配置 & 云端同步系统
# ==========================================
st.set_page_config(page_title="VixBooster ASX", page_icon="☁️", layout="wide")
st.title("☁️ VixBooster (全平台云同步版)")

# --- GitHub 云存储函数 ---
def load_data_from_github():
    """从 GitHub 读取 portfolio.json"""
    try:
        # 必须确保 Streamlit Secrets 里配置了 GITHUB_TOKEN
        if "GITHUB_TOKEN" not in st.secrets:
            return {"hgbl": 0, "ggus": 0, "cash": 300000.0, "cnn_manual": 50}
            
        token = st.secrets["GITHUB_TOKEN"]
        g = Github(token)
        repo = g.get_user().get_repo("vix-app") 
        try:
            contents = repo.get_contents("portfolio.json")
            data = json.loads(contents.decoded_content.decode())
            return data
        except:
            return {"hgbl": 0, "ggus": 0, "cash": 300000.0, "cnn_manual": 50}
    except Exception as e:
        # 静默失败，返回默认值，防止影响主程序
        print(f"云端读取错误: {e}")
        return {"hgbl": 0, "ggus": 0, "cash": 300000.0, "cnn_manual": 50}

def save_data_to_github(hgbl, ggus, cash, cnn):
    """保存数据到 GitHub"""
    try:
        token = st.secrets["GITHUB_TOKEN"]
        g = Github(token)
        repo = g.get_user().get_repo("vix-app")
        
        data = {
            "hgbl": hgbl, 
            "ggus": ggus, 
            "cash": cash,
            "cnn_manual": cnn
        }
        content = json.dumps(data, indent=2)
        
        try:
            file = repo.get_contents("portfolio.json")
            repo.update_file(file.path, "Update portfolio", content, file.sha)
        except:
            repo.create_file("portfolio.json", "Init portfolio", content)
            
        st.toast("✅ 数据已同步到云端！", icon="☁️")
        return True
    except Exception as e:
        st.error(f"保存失败: {e}")
        return False

# --- 初始化数据 ---
if 'data_loaded' not in st.session_state:
    with st.spinner('正在从云端拉取您的资产数据...'):
        cloud_data = load_data_from_github()
        st.session_state.my_hgbl = cloud_data.get('hgbl', 0)
        st.session_state.my_ggus = cloud_data.get('ggus', 0)
        st.session_state.my_cash = cloud_data.get('cash', 300000.0)
        st.session_state.cnn_manual = cloud_data.get('cnn_manual', 50)
        st.session_state.data_loaded = True

# ==========================================
# 2. 侧边栏：输入 (带保存按钮)
# ==========================================
with st.sidebar:
    st.header("☁️ 云端资产库")
    st.caption("修改后点击保存，手机/电脑即可同步。")
    
    new_hgbl = st.number_input("HGBL 持仓", min_value=0, step=100, value=st.session_state.my_hgbl)
    new_ggus = st.number_input("GGUS 持仓", min_value=0, step=100, value=st.session_state.my_ggus)
    new_cash = st.number_input("可用现金", min_value=0.0, step=1000.0, value=float(st.session_state.my_cash))
    
    st.markdown("---")
    use_manual_cnn = st.checkbox("手动修正 CNN", value=False)
    new_cnn = st.session_state.cnn_manual
    if use_manual_cnn:
        new_cnn = st.number_input("输入 CNN 指数", 0, 100, st.session_state.cnn_manual)
    
    if st.button("💾 保存并同步", type="primary"):
        success = save_data_to_github(new_hgbl, new_ggus, new_cash, new_cnn)
        if success:
            st.session_state.my_hgbl = new_hgbl
            st.session_state.my_ggus = new_ggus
            st.session_state.my_cash = new_cash
            st.session_state.cnn_manual = new_cnn
            st.rerun()

# ==========================================
# 3. 策略参数
# ==========================================
SMA_PERIOD = 200
RSI_PERIOD = 14
RSI_BULL_ENTER = 70
RSI_BEAR_ENTER = 40
RSI_EXIT_PROFIT = 80
RSI_BEAR_EXIT = 35
VIX_LEVEL_1 = 20
VIX_LEVEL_2 = 30

TARGET_PCT_BASE = 0.20
TARGET_PCT_BOOST_1 = 0.40
TARGET_PCT_BOOST_2 = 0.60

# ==========================================
# 4. 数据获取
# ==========================================
@st.cache_data(ttl=3600)
def get_market_data():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=450)
    
    spy = yf.download("SPY", start=start_date, end=end_date, progress=False)
    vix = yf.download("^VIX", start=start_date, end=end_date, progress=False)
    
    try:
        tickers = yf.download(["HGBL.AX", "GGUS.AX"], period="5d", progress=False)['Close']
        p_hgbl = tickers['HGBL.AX'].dropna().iloc[-1]
        p_ggus = tickers['GGUS.AX'].dropna().iloc[-1]
    except:
        p_hgbl = 0
        p_ggus = 0
    
    if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
    if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)
    
    return spy, vix, p_hgbl, p_ggus

@st.cache_data(ttl=600)
def get_cnn_index():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            return int(r.json()['fear_and_greed']['score']), r.json()['fear_and_greed']['rating']
    except:
        pass
    return None, None

def calculate_strategy(spy, vix, cnn_val, cnn_rating):
    spy['SMA200'] = ta.sma(spy['Close'], length=SMA_PERIOD)
    spy['RSI'] = ta.rsi(spy['Close'], length=RSI_PERIOD)
    
    curr_price = spy['Close'].iloc[-1]
    curr_sma = spy['SMA200'].iloc[-1]
    curr_rsi = spy['RSI'].iloc[-1]
    curr_vix = vix['Close'].iloc[-1]
    is_bull = curr_price > curr_sma
    
    target_pct = 0.0
    signal_name = "观望"
    reason = "无操作"
    
    if not is_bull:
        if curr_rsi > RSI_BEAR_EXIT:
            target_pct = 0.0
            signal_name = "🛡️ 红色警报"
            reason = "熊市反弹结束，清空进攻仓位。"
        elif curr_rsi < RSI_BEAR_ENTER and curr_vix > 33:
            target_pct = TARGET_PCT_BASE
            signal_name = "💎 钻石坑"
            reason = "极度恐慌，抢反弹。"
        else:
            target_pct = 0.0
            signal_name = "🛡️ 熊市防御"
            reason = "熊市回避。"
    elif curr_rsi > RSI_EXIT_PROFIT:
        target_pct = TARGET_PCT_BASE
        signal_name = "💰 止盈减仓"
        reason = "RSI过热，获利了结。"
    elif is_bull:
        if curr_rsi < RSI_BULL_ENTER:
            if curr_vix > VIX_LEVEL_2:
                target_pct = TARGET_PCT_BOOST_2
                signal_name = "🚀 强力进攻 (60%)"
                reason = "VIX极高，重仓机会。"
            elif curr_vix > VIX_LEVEL_1:
                target_pct = TARGET_PCT_BOOST_1
                signal_name = "⚔️ 加力进攻 (40%)"
                reason = "VIX较高，加仓机会。"
            else:
                target_pct = TARGET_PCT_BASE
                signal_name = "🔫 常规进攻 (20%)"
                reason = "牛市常态持有。"
        else:
            target_pct = 0.0
            signal_name = "☕ 暂时休息"
            reason = "短期过热，暂不持仓。"

    return locals()

# ==========================================
# 5. 主程序 UI
# ==========================================
if st.button('🔄 刷新市场信号'):
    st.cache_data.clear()
    st.rerun()

with st.spinner('正在同步全球市场...'):
    spy, vix, p_hgbl, p_ggus = get_market_data()
    
    auto_cnn, auto_rating = get_cnn_index()
    if use_manual_cnn:
        cnn_val = st.session_state.cnn_manual
        cnn_rating = "Manual"
    else:
        cnn_val = auto_cnn if auto_cnn else st.session_state.cnn_manual
        cnn_rating = auto_rating if auto_rating else "Fetch Failed"

    res = calculate_strategy(spy, vix, cnn_val, cnn_rating)

    h_qty = st.session_state.my_hgbl
    g_qty = st.session_state.my_ggus
    cash = st.session_state.my_cash
    
    total_assets = (h_qty * p_hgbl) + (g_qty * p_ggus) + cash
    target_val = total_assets * res['target_pct']
    curr_val = g_qty * p_ggus
    diff = target_val - curr_val
    
    action_text = "✅ 仓位完美 (Hold)"
    trade_qty = 0
    trade_amt = 0
    
    if abs(diff) > 1000:
        if diff > 0:
            trade_qty = int(diff / p_ggus) if p_ggus > 0 else 0
            trade_amt = diff
            action_text = f"🔵 买入 {trade_qty} 股 GGUS"
        else:
            trade_qty = int(abs(diff) / p_ggus) if p_ggus > 0 else 0
            trade_amt = abs(diff)
            action_text = f"🔴 卖出 {trade_qty} 股 GGUS"

# 显示结果
if "买入" in action_text:
    st.success(f"### {action_text}\n**金额: ${trade_amt:,.0f}** | 原因: {res['reason']}")
elif "卖出" in action_text:
    st.warning(f"### {action_text}\n**金额: ${trade_amt:,.0f}** | 原因: {res['reason']}")
else:
    st.info(f"### {action_text}\n原因: {res['reason']}")

st.markdown("---")

c1, c2, c3, c4 = st.columns(4)
c1.metric("总资产 (AUD)", f"${total_assets:,.0f}")
c2.metric("GGUS 仓位", f"{curr_val/total_assets*100:.1f}%", f"目标 {res['target_pct']*100:.0f}%")
c3.metric("RSI (SPY)", f"{res['curr_rsi']:.1f}", f"买点 < {RSI_BULL_ENTER}")
c4.metric("CNN 贪婪", f"{cnn_val:.0f}", cnn_rating)

st.caption(f"参考价格: HGBL ${p_hgbl:.2f} | GGUS ${p_ggus:.2f}")

st.markdown("---")
st.markdown("#### 📊 信号源 (SPY)")

# 修复了这里的画图代码
chart_data = spy.tail(120).reset_index()
if 'Date' not in chart_data.columns: chart_data = chart_data.rename(columns={'index': 'Date'})

line = alt.Chart(chart_data).mark_line().encode(
    x=alt.X('Date', title='日期'),
    y=alt.Y('Close', scale=alt.Scale(zero=False), title='价格 (USD)'), # 这里修好了
    tooltip=['Date', 'Close']
).interactive()

st.altair_chart(line, use_container_width=True)
