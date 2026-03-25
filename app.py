import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import hashlib
import akshare as ak  # 💡 新增：国内顶级开源数据引擎备胎
from datetime import datetime, timedelta

# --- 页面设置 ---
st.set_page_config(page_title="多因子投研风控终端 3.1", page_icon="icon.png", layout="wide")

# ==========================================
#        0. 云端多用户记忆引擎
# ==========================================
API_KEY = st.secrets["JSONBIN_KEY"]
BIN_ID = st.secrets["JSONBIN_ID"]
URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {"X-Master-Key": API_KEY, "Content-Type": "application/json"}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_all_cloud_data():
    try:
        response = requests.get(URL, headers=HEADERS)
        data = response.json().get("record", {})
        if "users" not in data: data["users"] = {}
        if "watchlists" not in data: data["watchlists"] = {}
        return data
    except Exception:
        return {"users": {}, "watchlists": {}}

def save_to_cloud(all_data):
    try:
        requests.put(URL, json=all_data, headers=HEADERS)
    except Exception as e:
        st.error(f"⚠️ 云端同步失败: {e}")

def get_category(symbol):
    symbol = str(symbol).strip().upper()
    if symbol.endswith(".SZ") or symbol.endswith(".SS"):
        if symbol.startswith("15") or symbol.startswith("51"): return "📊 国内 ETF"
        else: return "🇨🇳 A股个股"
    elif symbol.endswith(".HK"): return "🇭🇰 港股"
    elif symbol.isalpha(): return "🇺🇸 美股"
    else: return "🌍 其他标的"

# ==========================================
#        1. 登录系统 (含 Magic Link 免密)
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_user' not in st.session_state: st.session_state.current_user = ""

query_params = st.query_params
if "u" in query_params and "p" in query_params and not st.session_state.logged_in:
    magic_user = query_params["u"]
    magic_pwd = query_params["p"]
    db = load_all_cloud_data()
    if magic_user in db["users"] and db["users"][magic_user] == hash_password(magic_pwd):
        st.session_state.logged_in, st.session_state.current_user = True, magic_user

if not st.session_state.logged_in:
    st.title("🔐 多因子投研风控终端 3.1")
    tab_login, tab_register = st.tabs(["🔑 账号登录", "📝 注册新账号"])
    with tab_login:
        with st.form("login_form"):
            login_user = st.text_input("用户名")
            login_pwd = st.text_input("密码", type="password")
            if st.form_submit_button("登录", type="primary"):
                db = load_all_cloud_data()
                if login_user in db["users"] and db["users"][login_user] == hash_password(login_pwd):
                    st.session_state.logged_in, st.session_state.current_user = True, login_user
                    st.rerun()
                else: st.error("❌ 密码错误。")
    with tab_register:
        with st.form("register_form"):
            reg_user = st.text_input("设置用户名 (≥3位)")
            reg_pwd = st.text_input("设置密码 (≥6位)", type="password")
            reg_pwd_confirm = st.text_input("确认密码", type="password")
            if st.form_submit_button("注册并登录"):
                if len(reg_user) < 3 or len(reg_pwd) < 6 or reg_pwd != reg_pwd_confirm:
                    st.error("检查输入要求或确认密码！")
                else:
                    db = load_all_cloud_data()
                    if reg_user in db["users"]: st.error("❌ 用户名已被注册。")
                    else:
                        db["users"][reg_user] = hash_password(reg_pwd)
                        db["watchlists"][reg_user] = {}
                        save_to_cloud(db)
                        st.session_state.logged_in, st.session_state.current_user = True, reg_user
                        st.rerun()
    st.stop()

# ==========================================
#        2. 主程序 (侧边栏)
# ==========================================
st.sidebar.title(f"👋 {st.session_state.current_user} 的终端")
if st.sidebar.button("🚪 安全退出"):
    st.session_state.logged_in, st.session_state.current_user = False, ""
    st.rerun()
st.sidebar.divider()

if 'watchlist' not in st.session_state or st.session_state.get('last_user') != st.session_state.current_user:
    all_users_data = load_all_cloud_data()
    st.session_state.watchlist = all_users_data["watchlists"].get(st.session_state.current_user, {})
    st.session_state.last_user = st.session_state.current_user
    st.session_state.sidebar_select = ""

# 状态初始化
if 'current_price' not in st.session_state: st.session_state.current_price = 0.0
if 'df_history' not in st.session_state: st.session_state.df_history = pd.DataFrame()
if 'fundamentals' not in st.session_state: st.session_state.fundamentals = {}
if 'data_source' not in st.session_state: st.session_state.data_source = "" # 记录数据来源

if st.sidebar.button("➕ 手动输入新标的", type="primary" if st.session_state.sidebar_select == "" else "secondary", use_container_width=True):
    st.session_state.sidebar_select = ""
    st.rerun()
st.sidebar.divider()

categories_dict = {}
for sym, data in st.session_state.watchlist.items():
    cat = data.get('category', '🌍 其他标的')
    categories_dict.setdefault(cat, []).append((sym, data))

for cat, items in categories_dict.items():
    st.sidebar.caption(f"**{cat}**") 
    for sym, data in items:
        col1, col2 = st.sidebar.columns([4, 1])
        btn_type = "primary" if st.session_state.sidebar_select == sym else "secondary"
        btn_label = f"{data.get('name', '')} ({sym})" if data.get('name', '') else f"📊 {sym}"
        if col1.button(btn_label, key=f"sel_{sym}", type=btn_type, use_container_width=True):
            st.session_state.sidebar_select = sym
            st.rerun()
        if col2.button("🗑️", key=f"del_{sym}"):
            del st.session_state.watchlist[sym]
            db = load_all_cloud_data()
            db["watchlists"][st.session_state.current_user] = st.session_state.watchlist
            save_to_cloud(db)
            if st.session_state.sidebar_select == sym: st.session_state.sidebar_select = ""
            st.rerun()
    st.sidebar.write("")

default_sym = st.session_state.sidebar_select if st.session_state.sidebar_select else "TSM"
default_data = st.session_state.watchlist.get(default_sym, {})
default_name = default_data.get('name', '台积电') if default_sym == "TSM" else default_data.get('name', '')
default_cost = float(default_data.get('cost', 0.0))
default_qty = int(default_data.get('qty', 0))

# ==========================================
#        3. 双引擎智能路由抓取系统
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_multi_factor_data(symbol):
    df = pd.DataFrame()
    fund_data = {"PE": None, "PEG": None, "ROE": None, "Margin": None, "52w_Change": None}
    source_name = "未获取"
    
    # 💥 引擎 1：优先尝试 Yahoo Finance (适合全球与基本面)
    try:
        yf_df = yf.download(symbol, period="1y", progress=False, threads=False)
        if yf_df is not None and len(yf_df) > 20:
            if isinstance(yf_df.columns, pd.MultiIndex): yf_df.columns = yf_df.columns.get_level_values(0)
            df = yf_df
            source_name = "Yahoo Finance Global API"
            
            # 抓取基本面
            ticker = yf.Ticker(symbol)
            info = ticker.info
            fund_data = {
                "PE": info.get('trailingPE', info.get('forwardPE', None)),
                "PEG": info.get('pegRatio', None),
                "ROE": info.get('returnOnEquity', None),
                "Margin": info.get('profitMargins', None),
                "52w_Change": info.get('52WeekChange', None)
            }
    except Exception:
        pass

    # 💥 引擎 2：灾备切换！如果 YF 失败，且是国内资产，启动 AKShare (东方财富接口)
    if df.empty and (symbol.endswith(".SZ") or symbol.endswith(".SS")):
        try:
            code = symbol.split('.')[0] # AKShare 只需要 6 位数字代码
            # 获取东财前复权日 K 线
            ak_df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if not ak_df.empty:
                # 统一数据格式
                ak_df.rename(columns={'日期':'Date', '开盘':'Open', '收盘':'Close', '最高':'High', '最低':'Low', '成交量':'Volume'}, inplace=True)
                ak_df.index = pd.to_datetime(ak_df['Date'])
                df = ak_df.tail(250) # 取最近一年
                source_name = "AKShare (东方财富数据中心)"
        except Exception:
            pass
            
    # 如果两个引擎都挂了
    if df.empty:
        return None, {}, "主备双引擎数据抓取均失败，请检查代码格式或网络状态。", ""

    # 计算技术面与多因子 (无论来自哪个引擎，统一计算)
    try:
        df['MA20'], df['MA60'] = df['Close'].rolling(window=20).mean(), df['Close'].rolling(window=60).mean()
        df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
        df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['Signal']
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        return df.iloc[-126:], fund_data, "成功", source_name
    except Exception as e:
        return None, {}, f"指标计算错误: {str(e)}", ""

def plot_candlestick(df, symbol, name):
    title = f"{name} ({symbol}) - 6个月日K线图" if name else f"{symbol} - 6个月日K线图"
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.8])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日线', line=dict(color='#ffca28', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60日线', line=dict(color='#2196f3', width=1.5)), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='#90caf9'), row=2, col=1)
    fig.update_layout(title=title, xaxis_rangeslider_visible=False, height=450, margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
    return fig

# ==========================================
#        4. UI 展示面板
# ==========================================
st.title("🛰️ 3.1 多因子投研风控终端")
ui_key = default_sym if default_sym else "new_entry"

with st.container():
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1, 1, 1.2])
    with c1: input_symbol = st.text_input("代码", value=default_sym, key=f"sym_{ui_key}")
    with c2: input_name = st.text_input("名称", value=default_name, key=f"name_{ui_key}")
    with c3: input_cost = st.number_input("底仓成本", value=default_cost, step=0.01, key=f"cost_{ui_key}")
    with c4: input_qty = st.number_input("持仓数量", value=default_qty, step=100, key=f"qty_{ui_key}")
    with c5:
        st.write("") 
        if st.button("🔄 同步全维数据", type="primary", use_container_width=True):
            if input_symbol:
                with st.spinner(f'智能路由双引擎抓取 {input_symbol} 中...'):
                    df_h, funds, msg, source = fetch_multi_factor_data(input_symbol)
                    if df_h is not None:
                        st.session_state.df_history = df_h
                        st.session_state.current_price = float(df_h.iloc[-1]['Close'])
                        st.session_state.fundamentals = funds
                        st.session_state.data_source = source # 记录当前数据来源
                    else: st.error(f"❌ {msg}")

if st.button("💾 更新至专属空间"):
    if input_symbol:
        st.session_state.watchlist[input_symbol] = {
            "name": input_name, "cost": input_cost, "qty": input_qty, "category": get_category(input_symbol) 
        }
        db = load_all_cloud_data()
        db["watchlists"][st.session_state.current_user] = st.session_state.watchlist
        save_to_cloud(db)
        st.session_state.sidebar_select = input_symbol 
        st.rerun() 

st.divider()

if not st.session_state.df_history.empty and st.session_state.current_price > 0:
    
    # 💡 显著展示数据来源水印
    st.caption(f"**📡 底层数据信源：** 已通过智能路由接入 `{st.session_state.data_source}`")
    
    # 顶部：K线与风控推演
    col_chart, col_risk = st.columns([2, 1], gap="medium")
    with col_chart:
        st.plotly_chart(plot_candlestick(st.session_state.df_history, input_symbol, input_name), use_container_width=True)
    with col_risk:
        st.subheader("🛡️ 加仓风控推演")
        st.metric("最新现价", f"¥ {st.session_state.current_price:.3f}")
        qty_add = st.slider("计划加仓数量", min_value=0, max_value=int(max(input_qty * 2, 1000)), value=0, step=100, key=f"slider_{ui_key}")
        total_qty = input_qty + qty_add
        current_p = st.session_state.current_price
        new_cost = ((input_cost * input_qty) + (current_p * qty_add)) / total_qty if total_qty > 0 else input_cost
        safe_cushion = ((current_p - new_cost) / current_p) * 100 if current_p > 0 and total_qty > 0 else 0
        
        st.metric("新保本点", f"{new_cost:.3f}", f"成本变化 {new_cost-input_cost:.3f}" if qty_add>0 else None, delta_color="inverse")
        st.metric("利润安全垫", f"{safe_cushion:.2f}%")
        if qty_add > 0:
            st.caption(f"**铁律：** 若跌破新成本线 {new_cost:.2f}，立即止损保本。")

    st.markdown("### 📊 多因子全息体检报告")
    f1, f2, f3 = st.columns(3)
    df = st.session_state.df_history
    fund = st.session_state.fundamentals
    
    with f1:
        st.info("🧠 **资金与情绪面 (Momentum)**")
        rsi = df.iloc[-1]['RSI']
        st.write(f"**RSI (14日):** {rsi:.1f}")
        if rsi > 70: st.error("🔥 情绪极度狂热 (超买区域)，警惕砸盘。")
        elif rsi < 30: st.success("🧊 情绪极度冰点 (超卖区域)，随时可能反弹。")
        else: st.write("⚖️ 情绪中性。")
        
        vol, vol_ma5 = df.iloc[-1]['Volume'], df.iloc[-1]['Vol_MA5']
        if vol > vol_ma5 * 1.8: st.write("⚡ **今日量能：** 剧烈放量异动！")
        elif vol < vol_ma5 * 0.6: st.write("💤 **今日量能：** 极致缩量观望。")
        else: st.write("🌊 **今日量能：** 资金平稳交投。")

    with f2:
        st.success("💼 **深度基本面 (Fundamentals)**")
        roe = fund.get('ROE')
        margin = fund.get('Margin')
        pe = fund.get('PE')
        
        st.write(f"**ROE (净资产收益率):** {f'{roe*100:.1f}%' if roe else '未知'}")
        if roe and roe > 0.15: st.caption("🏆 卓越的赚钱机器 (ROE>15%)")
        
        st.write(f"**净利润率:** {f'{margin*100:.1f}%' if margin else '未知'}")
        
        pe_str = f"{pe:.1f}" if pe else '未知'
        st.write(f"**动态市盈率 (PE):** {pe_str}")
        if pe and pe < 15: st.caption("💎 估值处于安全水域")
        elif pe and pe > 40: st.caption("⚠️ 估值溢价较高，需极高增速消化")

    with f3:
        st.warning("🏛️ **趋势与宏观对比 (Macro Trend)**")
        ma20, ma60 = df.iloc[-1]['MA20'], df.iloc[-1]['MA60']
        if current_p > ma60 and ma20 > ma60: st.write("📈 **中期趋势：** 稳健多头排列。")
        elif current_p < ma60: st.write("📉 **中期趋势：** 空头破位，深水区。")
        else: st.write("⚖️ **中期趋势：** 震荡方向不明。")
        
        w52 = fund.get('52w_Change')
        st.write(f"**近一年涨跌幅 (Beta):** {f'{w52*100:.1f}%' if w52 else '未知'}")
        if w52 and w52 > 0.2: st.caption("🚀 过去一年显著跑赢多数大盘指数。")
        elif w52 and w52 < -0.1: st.caption("⚓ 过去一年走势弱于全球宏观大盘。")
else:
    st.info("💡 请在上方确认代码后，点击“同步全维数据”。")
