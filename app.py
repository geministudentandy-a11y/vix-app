import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import altair as alt
import json
from github import Github

# ==========================================
# 1. 页面配置 & 云端同步
# ==========================================
st.set_page_config(page_title="VixBooster ASX", page_icon="⚡", layout="wide")
st.title("⚡ VixBooster (信号增强版)")

# --- GitHub 云存储函数 ---
def load_data_from_github():
    try:
        if "GITHUB_TOKEN" not in st.secrets:
            return {"hgbl": 0, "ggus": 0, "cash": 300000.0}
        token = st.secrets["GITHUB_TOKEN"]
        g = Github(token)
        repo = g.get_user().get_repo("vix-app") 
        try:
            contents = repo.get_contents("portfolio.json")
            data = json.loads(contents.decoded_content.decode())
            return data
        except:
            return {"hgbl": 0, "ggus": 0, "cash": 300000.0}
    except:
        return {"hgbl": 0, "ggus": 0, "cash": 300000.0}

def save_data_to_github(hgbl, ggus, cash):
    try:
        token = st.secrets["GITHUB_TOKEN"]
        g = Github(token)
        repo = g.get_user().get_repo("vix-app")
        data = {"hgbl": hgbl, "ggus": ggus, "cash": cash}
        content = json.dumps(data, indent=2)
        try:
            file = repo.get_contents("portfolio.json")
            repo.update_file(file.path, "Update portfolio", content, file.sha)
        except:
            repo.create_file("portfolio.json", "Init portfolio", content)
        st.toast("✅ 云端同步成功！", icon="☁️")
        return True
    except Exception as e:
        st.error(f"保存失败: {e}")
        return False

# 初始化
if 'data_loaded' not in st.session_state:
    with st.spinner('正在从云端拉取数据...'):
        cloud_data = load_data_from_github()
        st.session_state.my_hgbl = cloud_data.get('hgbl', 0)
        st.session_state.my_ggus = cloud_data.get('ggus', 0)
        st.session_state.my_cash = cloud_data.get('cash', 300000.0)
        st.session_state.data_loaded = True

# ==========================================
# 2. 侧边栏：资产与参数
# ==========================================
with st.sidebar:
    st.header("☁️ 云端资产库")
    new_hgbl = st.number_input("HGBL 持仓", min_value=0, step=100, value=st.session_state.my_hgbl)
    new_ggus = st.number_input("GGUS 持仓", min_value=0, step=100, value=st.session_state.my_ggus)
    new_cash = st.number_input("可用现金", min_value=0.0, step=1000.0, value=float(st.session_state.my_cash))
    
    if st.button("💾 保存并同步", type="primary"):
        if save_data_to_github(new_hgbl, new_ggus, new_cash):
            st.session_state.my_hgbl = new_hgbl
            st.session_state.my_ggus = new_ggus
            st.session_state.my_cash = new_cash
            st.rerun()

    st.markdown("---")
    st.header("⚙️ 核心参数")
    st.info("""
    **🟢 买入标准**
    * **牛市**: RSI < 70
    * **熊市**: RSI < 40 + VIX > 33
    
    **🔴 卖出标准**
    * **止盈**: RSI > 80
    * **止损**: 熊市 + RSI > 35
    
    **🔥 VIX 仓位**
    * **> 20**: 40% 仓位
    * **> 30**: 60% 仓位
    """)

# ==========================================
# 3. 策略逻辑
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

def calculate_strategy(spy, vix):
    spy['SMA200'] = ta.sma(spy['Close'], length=SMA_PERIOD)
    spy['RSI'] = ta.rsi(spy['Close'], length=RSI_PERIOD)
    
    curr_price = spy['Close'].iloc[-1]
    curr_sma = spy['SMA200'].iloc[-1]
    curr_rsi = spy['RSI'].iloc[-1]
    curr_vix = vix['Close'].iloc[-1]
    is_bull = curr_price > curr_sma
    
    # 策略判断
