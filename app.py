import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import hashlib
import akshare as ak
from datetime import datetime, timedelta
import os
import base64

# --- 页面设置 (极宽布局) ---
st.set_page_config(page_title="FactorX (灵犀终端)", page_icon="🛰️", layout="wide", initial_sidebar_state="expanded")

# ==========================================
#        🎨 深度 UI 美化 (CSS 注入)
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {background-color: transparent !important;}
        [data-testid="stAppDeployButton"] {display: none;}
        
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        div[data-testid="metric-container"] {
            background-color: rgba(130, 130, 130, 0.05);
            border: 1px solid rgba(130, 130, 130, 0.2);
            padding: 15px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        }
        div[data-testid="metric-container"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        }
        .stButton > button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 10px rgba(0,0,0,0.15);
        }
        .login-header {
            text-align: center;
            margin-bottom: 20px;
        }
        .news-link {
            text-decoration: none;
            color: #1E88E5;
            font-weight: 500;
            transition: color 0.2s;
        }
        .news-link:hover {
            text-decoration: underline;
            color: #0D47A1;
        }
        .report-btn {
            display: inline-block;
            padding: 10px 15px;
            margin-top: 10px;
            background-color: #f0f2f6;
            color: #31333F;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            border: 1px solid #dcdcdc;
            transition: all 0.2s;
        }
        .report-btn:hover {
            background-color: #e0e2e6;
            color: #1E88E5;
            border-color: #1E88E5;
        }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ==========================================
#        🖼️ 智能 Logo 渲染模块
# ==========================================
def render_logo(width=80, center=False):
    if os.path.exists("icon.png"):
        if center:
            with open("icon.png", "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            html_code = f"""
            <div style="display: flex; justify-content: center; margin-bottom: 15px;">
                <img src="data:image/png;base64,{encoded_string}" 
                     style="width: {width}px; height: {width}px; border-radius: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.3);">
            </div>
            """
            st.markdown(html_code, unsafe_allow_html=True)
        else:
            st.image("icon.png", width=width)
    else:
        if center:
            st.markdown("<h1 style='text-align: center;'>🛰️</h1>", unsafe_allow_html=True)

# ==========================================
#        0. 云端多用户记忆引擎
# ==========================================
API_KEY = st.secrets.get("JSONBIN_KEY", "")
BIN_ID = st.secrets.get("JSONBIN_ID", "")
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
#        1. 登录系统 
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
    spacer1, login_col, spacer3 = st.columns([1, 1.5, 1])
    with login_col:
        st.write("<br><br>", unsafe_allow_html=True)
        render_logo(width=100, center=True)
        st.markdown("<h2 class='login-header'>FactorX 灵犀终端</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>多因子量化投研与动态风控工作站</p>", unsafe_allow_html=True)
        
        tab_login, tab_register = st.tabs(["🔑 身份接入", "📝 申请密钥"])
        with tab_login:
            with st.form("login_form"):
                login_user = st.text_input("终端标识 (用户名)")
                login_pwd = st.text_input("安全密钥 (密码)", type="password")
                if st.form_submit_button("安全接入", type="primary", use_container_width=True):
                    db = load_all_cloud_data()
                    if login_user in db["users"] and db["users"][login_user] == hash_password(login_pwd):
                        st.session_state.logged_in, st.session_state.current_user = True, login_user
                        st.rerun()
                    else: st.error("❌ 密钥校验失败。")
        with tab_register:
            with st.form("register_form"):
                reg_user = st.text_input("设置终端标识 (≥3位)")
                reg_pwd = st.text_input("设置安全密钥 (≥6位)", type="password")
                reg_pwd_confirm = st.text_input("确认密钥", type="password")
                if st.form_submit_button("注册并初始化空间", use_container_width=True):
                    if len(reg_user) < 3 or len(reg_pwd) < 6 or reg_pwd != reg_pwd_confirm:
                        st.error("检查输入要求或确认密钥一致性！")
                    else:
                        db = load_all_cloud_data()
                        if reg_user in db["users"]: st.error("❌ 标识已被占用。")
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
render_logo(width=60, center=False)
st.sidebar.title(f"👋 {st.session_state.current_user}")
st.sidebar.caption("FactorX Workspace Active 🟢")

if st.sidebar.button("🚪 断开连接", use_container_width=True):
    st.session_state.logged_in, st.session_state.current_user = False, ""
    st.rerun()
st.sidebar.divider()

if 'watchlist' not in st.session_state or st.session_state.get('last_user') != st.session_state.current_user:
    all_users_data = load_all_cloud_data()
    st.session_state.watchlist = all_users_data["watchlists"].get(st.session_state.current_user, {})
    st.session_state.last_user = st.session_state.current_user
    st.session_state.sidebar_select = ""

if 'current_price' not in st.session_state: st.session_state.current_price = 0.0
if 'df_history' not in st.session_state: st.session_state.df_history = pd.DataFrame()
if 'fundamentals' not in st.session_state: st.session_state.fundamentals = {}
if 'data_source' not in st.session_state: st.session_state.data_source = ""
if 'news_data' not in st.session_state: st.session_state.news_data = [] 
if 'macro_news' not in st.session_state: st.session_state.macro_news = [] # 新增：宏观电报存储
if 'report_link' not in st.session_state: st.session_state.report_link = "" # 新增：智能研报链接

if st.sidebar.button("➕ 载入新监测标的", type="primary" if st.session_state.sidebar_select == "" else "secondary", use_container_width=True):
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
#        3. 全息引擎：数据 + 因子 + 宏观情报抓取
# ==========================================
@st.cache_data(ttl=600, show_spinner=False) # 缓存缩短到10分钟，保证财联社电报实时性
def fetch_multi_factor_data(symbol):
    df = pd.DataFrame()
    fund_data = {"PE": None, "PEG": None, "ROE": None, "Margin": None, "52w_Change": None}
    source_name = "未获取"
    news_list = []
    macro_list = []
    report_url = ""
    
    is_a_share = symbol.endswith(".SZ") or symbol.endswith(".SS")
    base_code = symbol.split('.')[0] if is_a_share else symbol

    # 💡 核心升级 1：生成智能研报底层直达链接
    if is_a_share:
        report_url = f"https://so.eastmoney.com/Yanbao/s?keyword={base_code}"
    else:
        report_url = f"https://seekingalpha.com/symbol/{base_code.upper()}"

    # 💡 核心升级 2：抓取 7x24小时全市场宏观电报 (财联社)
    try:
        cls_df = ak.stock_zh_a_alerts_cls()
        if not cls_df.empty:
            for idx, row in cls_df.head(6).iterrows():
                # 过滤掉过短的无用通知
                if len(str(row.get('内容', ''))) > 15:
                    macro_list.append({
                        "time": str(row.get('时间', ''))[-8:],
                        "content": str(row.get('内容', ''))[:80] + "..."
                    })
    except Exception:
        pass

    # --- 尝试获取海外数据 & Yahoo 英文个股新闻 ---
    try:
        ticker = yf.Ticker(symbol)
        yf_df = ticker.history(period="1y") 
        if yf_df is not None and len(yf_df) > 20:
            df = yf_df
            source_name = "Yahoo Finance Global API"
            info = ticker.info
            fund_data = {
                "PE": info.get('trailingPE', info.get('forwardPE', None)),
                "PEG": info.get('pegRatio', None),
                "ROE": info.get('returnOnEquity', None),
                "Margin": info.get('profitMargins', None),
                "52w_Change": info.get('52WeekChange', None)
            }
            yf_news = ticker.news
            if yf_news and not is_a_share: # A股不用外媒新闻
                for item in yf_news[:6]:
                    pub_time = datetime.fromtimestamp(item.get('providerPublishTime', 0)).strftime('%m-%d %H:%M')
                    news_list.append({
                        "title": item.get('title', '无标题资讯'),
                        "publisher": item.get('publisher', 'Global Media'),
                        "link": item.get('link', '#'),
                        "time": pub_time
                    })
    except Exception:
        pass

    # --- 灾备与A股增强：强制拉取东财数据 & 东财中文资讯 ---
    if df.empty and is_a_share:
        try:
            ak_df = ak.stock_zh_a_hist(symbol=base_code, period="daily", adjust="qfq")
            if not ak_df.empty:
                ak_df.rename(columns={'日期':'Date', '开盘':'Open', '收盘':'Close', '最高':'High', '最低':'Low', '成交量':'Volume'}, inplace=True)
                ak_df.index = pd.to_datetime(ak_df['Date'])
                df = ak_df.tail(250)
                source_name = "AKShare (东方财富底层数据)"
        except Exception:
            pass
            
    if is_a_share:
        try:
            ak_news = ak.stock_news_em(symbol=base_code)
            if not ak_news.empty:
                news_list = [] 
                for idx, row in ak_news.head(6).iterrows():
                    news_list.append({
                        "title": row.get('新闻标题', 'A股关联资讯'),
                        "publisher": row.get('文章来源', '东方财富'),
                        "link": row.get('新闻链接', '#'),
                        "time": row.get('发布时间', '')[-14:-3] # 截取精简时间
                    })
        except Exception:
            pass

    if df.empty:
        return None, {}, "数据抓取失败，请检查代码。", "", [], [], ""

    # --- 计算技术面指标 ---
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

        return df.iloc[-126:], fund_data, "成功", source_name, news_list, macro_list, report_url
    except Exception as e:
        return None, {}, f"指标计算错误: {str(e)}", "", [], [], ""

def plot_candlestick(df, symbol, name):
    title = f"{name} ({symbol}) - 6个月日K线图" if name else f"{symbol} - 6个月日K线图"
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.8])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日线', line=dict(color='#ffca28', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60日线', line=dict(color='#2196f3', width=1.5)), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='#90caf9'), row=2, col=1)
    fig.update_layout(
        title=title, xaxis_rangeslider_visible=False, height=480, margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# ==========================================
#        4. UI 展示面板与多维扫描
# ==========================================
st.title("🛰️ FactorX 核心指挥舱")
ui_key = default_sym if default_sym else "new_entry"

with st.container():
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1, 1, 1.2])
    with c1: input_symbol = st.text_input("代码", value=default_sym, key=f"sym_{ui_key}", help="深市:.SZ, 沪市:.SS, 美股直接输")
    with c2: input_name = st.text_input("名称", value=default_name, key=f"name_{ui_key}")
    with c3: input_cost = st.number_input("底仓成本", value=default_cost, step=0.01, key=f"cost_{ui_key}")
    with c4: input_qty = st.number_input("持仓数量", value=default_qty, step=100, key=f"qty_{ui_key}")
    with c5:
        st.write("") 
        if st.button("🔄 启动灵犀多维扫描", type="primary", use_container_width=True):
            if input_symbol:
                with st.spinner(f'FactorX 引擎正在深度解析与聚合情报...'):
                    df_h, funds, msg, source, news, macro, report = fetch_multi_factor_data(input_symbol)
                    if df_h is not None:
                        st.session_state.df_history = df_h
                        st.session_state.current_price = float(df_h.iloc[-1]['Close'])
                        st.session_state.fundamentals = funds
                        st.session_state.data_source = source
                        st.session_state.news_data = news 
                        st.session_state.macro_news = macro
                        st.session_state.report_link = report
                    else: st.error(f"❌ {msg}")

if st.button("💾 将标的写入 FactorX 云端矩阵"):
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
    
    st.caption(f"**📡 FactorX 数据链：** 已成功接驳 `{st.session_state.data_source}`")
    
    col_chart, col_risk = st.columns([2.2, 1], gap="large")
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
            st.info(f"**💡 灵犀铁律：** 若跌破新成本线 {new_cost:.2f}，立即执行止损保本程序。")

    st.markdown("<br>### 📊 多因子全息体检报告", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    df = st.session_state.df_history
    fund = st.session_state.fundamentals
    
    ma20, ma60 = df.iloc[-1]['MA20'], df.iloc[-1]['MA60']
    rsi = df.iloc[-1]['RSI']
    pe = fund.get('PE')
    roe = fund.get('ROE')
    
    with f1:
        st.info("🧠 **资金与情绪面**")
        st.write(f"**RSI (14日):** {rsi:.1f}")
        if rsi > 70: st.error("🔥 情绪狂热 (超买)，警惕砸盘。")
        elif rsi < 30: st.success("🧊 情绪冰点 (超卖)，随时反弹。")
        else: st.write("⚖️ 资金博弈中性。")
        vol, vol_ma5 = df.iloc[-1]['Volume'], df.iloc[-1]['Vol_MA5']
        if vol > vol_ma5 * 1.8: st.write("⚡ 监测到剧烈放量异动！")
        else: st.write("🌊 资金池水位平稳。")

    with f2:
        st.success("💼 **深度基本面**")
        st.write(f"**ROE:** {f'{roe*100:.1f}%' if roe else '未知'}")
        if roe and roe > 0.15: st.caption("🏆 卓越的印钞能力 (ROE>15%)")
        pe_str = f"{pe:.1f}" if pe else '未知'
        st.write(f"**动态市盈率 (PE):** {pe_str}")
        if pe and pe < 15: st.caption("💎 估值处于安全水域")
        elif pe and pe > 40: st.caption("⚠️ 估值溢价较高")

    with f3:
        st.warning("🏛️ **趋势与宏观对比**")
        if current_p > ma60 and ma20 > ma60: st.write("📈 **中期趋势：** 多头右侧通道。")
        elif current_p < ma60: st.write("📉 **中期趋势：** 空头破位深水区。")
        else: st.write("⚖️ **中期趋势：** 震荡不明。")
        w52 = fund.get('52w_Change')
        st.write(f"**近一年涨跌幅:** {f'{w52*100:.1f}%' if w52 else '未知'}")
        if w52 and w52 > 0.2: st.caption("🚀 过去一年跑赢大盘。")

    st.markdown("---")
    
    # ==========================================
    # 💡 核心升级：诊断 + 多维情报聚合局
    # ==========================================
    col_diag, col_news = st.columns([1.5, 1.2], gap="large")
    
    with col_diag:
        st.markdown("### 📝 FactorX 综合诊断指令")
        score = 0
        reasons = []

        if current_p > ma60 and ma20 > ma60:
            score += 1
            reasons.append("✔ **趋势因子：** 价格稳居生命线，多头通道。")
        elif current_p < ma60:
            score -= 1
            reasons.append("❌ **趋势因子：** 跌破生命线，中线资金流出。")

        if pe is not None:
            if pe < 20 and (roe is not None and roe > 0.10):
                score += 1
                reasons.append("✔ **价值因子：** 估值较低且盈利强劲。")
            elif pe > 40:
                score -= 1
                reasons.append("❌ **价值因子：** 动态市盈率偏高，存在杀估值风险。")

        if rsi > 70:
            score -= 1
            reasons.append("❌ **情绪因子：** RSI超买，散户FOMO严重。")
        elif rsi < 30:
            score += 1
            reasons.append("✔ **情绪因子：** RSI极度冰点，做空动能衰竭。")
        
        if score >= 2:
            st.success("🟢 **核心指令：强烈看多 (Strong Buy)**")
            st.write("多维因子共振向好，建议积极配置或持有。")
        elif score == 1:
            st.info("🟡 **核心指令：谨慎乐观 (Cautious Optimism)**")
            st.write("整体偏向多头，可适度建仓，严守防守线。")
        elif score <= -1:
            st.error("🔴 **核心指令：防范风险 (Risk Warning / Sell)**")
            st.write("技术破位或估值透支，建议规避，切忌接飞刀。")
        else:
            st.warning("⚪ **核心指令：中性观望 (Neutral)**")
            st.write("多空交织，缺乏明确驱动力，多看少动。")

        with st.expander("🔍 展开量化评分逻辑", expanded=False):
            for reason in reasons:
                st.markdown(reason)

    # 💡 终极情报局：选项卡分类展示
    with col_news:
        st.markdown("### 📰 灵犀情报局")
        tab_stock, tab_macro, tab_report = st.tabs(["🎯 个股异动", "🌍 宏观电报", "📑 深度研报"])
        
        with tab_stock:
            if st.session_state.news_data:
                for item in st.session_state.news_data:
                    st.markdown(f"""
                    <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed rgba(130,130,130,0.3);">
                        <a href="{item['link']}" target="_blank" class="news-link" style="font-size: 13px;">{item['title']}</a>
                        <div style="font-size: 11px; color: gray; margin-top: 2px;">⏱️ {item['time']} | 🗞️ {item['publisher']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("暂未嗅探到关联资讯。")

        with tab_macro:
            if st.session_state.macro_news:
                st.caption("⚡ 财联社 7x24小时全市场快讯")
                for item in st.session_state.macro_news:
                    st.markdown(f"""
                    <div style="margin-bottom: 8px; font-size: 13px;">
                        <span style="color: #E53935; font-weight: bold;">{item['time']}</span> - {item['content']}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("宏观电报接口暂未响应。")

        with tab_report:
            st.markdown("<p style='font-size: 13px; color: gray;'>由于商业版权限制，API无法直接抓取PDF研报实体。但 FactorX 已为您生成智能底层穿透链接，点击即可查阅各家券商/机构对该资产的最新深度研报。</p>", unsafe_allow_html=True)
            if st.session_state.report_link:
                st.markdown(f"""
                <a href="{st.session_state.report_link}" target="_blank" class="report-btn">
                    🔗 前往查阅 [{input_symbol}] 深度机构研报库
                </a>
                """, unsafe_allow_html=True)

else:
    st.info("💡 请在上方确认代码后，点击“启动灵犀多维扫描”。")
