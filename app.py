import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import hashlib
import akshare as ak
from datetime import datetime, timedelta

# --- 页面设置 ---
st.set_page_config(page_title="多因子投研风控终端 3.3", page_icon="icon.png", layout="wide")

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
    st.title("🔐 多因子投研风控终端 3.3")
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

if 'current_price' not in st.session_state: st.session_state.current_price = 0.0
if 'df_history' not in st.session_state: st.session_state.df_history = pd.DataFrame()
if 'fundamentals' not in st.session_state: st.session_state.fundamentals = {}
if 'data_source' not in st.session_state: st.session_state.data_source = ""

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
    
    try:
        yf_df = yf.download(symbol, period="1y", progress=False, threads=False)
        if yf_df is not None and len(yf_df) > 20:
            if isinstance(yf_df.columns, pd.MultiIndex): yf_df.columns = yf_df.columns.get_level_values(0)
            df = yf_df
            source_name = "Yahoo Finance Global API"
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

    if df.empty and (symbol.endswith(".SZ") or symbol.endswith(".SS")):
        try:
            code = symbol.split('.')[0]
            ak_df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if not ak_df.empty:
                ak_df.rename(columns={'日期':'Date', '开盘':'Open', '收盘':'Close', '最高':'High', '最低':'Low', '成交量':'Volume'}, inplace=True)
                ak_df.index = pd.to_datetime(ak_df['Date'])
                df = ak_df.tail(250)
                source_name = "AKShare (东方财富数据中心)"
        except Exception:
            pass
            
    if df.empty:
        return None, {}, "主备双引擎数据抓取均失败，请检查代码或网络。", ""

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
#        4. UI 展示面板与智能打分
# ==========================================
st.title("🛰️ 3.3 多因子投研风控终端")
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
                        st.session_state.data_source = source
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
    
    st.caption(f"**📡 底层数据信源：** 已通过智能路由接入 `{st.session_state.data_source}`")
    
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
    
    ma20, ma60 = df.iloc[-1]['MA20'], df.iloc[-1]['MA60']
    rsi = df.iloc[-1]['RSI']
    pe = fund.get('PE')
    roe = fund.get('ROE')
    
    with f1:
        st.info("🧠 **资金与情绪面**")
        st.write(f"**RSI (14日):** {rsi:.1f}")
        if rsi > 70: st.error("🔥 情绪狂热 (超买)，警惕砸盘。")
        elif rsi < 30: st.success("🧊 情绪冰点 (超卖)，随时反弹。")
        else: st.write("⚖️ 情绪中性。")
        vol, vol_ma5 = df.iloc[-1]['Volume'], df.iloc[-1]['Vol_MA5']
        if vol > vol_ma5 * 1.8: st.write("⚡ 今日剧烈放量异动！")
        elif vol < vol_ma5 * 0.6: st.write("💤 今日极致缩量观望。")
        else: st.write("🌊 资金平稳交投。")

    with f2:
        st.success("💼 **深度基本面**")
        margin = fund.get('Margin')
        st.write(f"**ROE:** {f'{roe*100:.1f}%' if roe else '未知'}")
        if roe and roe > 0.15: st.caption("🏆 卓越的赚钱机器 (ROE>15%)")
        pe_str = f"{pe:.1f}" if pe else '未知'
        st.write(f"**动态市盈率 (PE):** {pe_str}")
        if pe and pe < 15: st.caption("💎 估值处于安全水域")
        elif pe and pe > 40: st.caption("⚠️ 估值溢价较高")

    with f3:
        st.warning("🏛️ **趋势与宏观对比**")
        if current_p > ma60 and ma20 > ma60: st.write("📈 **中期趋势：** 多头排列。")
        elif current_p < ma60: st.write("📉 **中期趋势：** 空头破位。")
        else: st.write("⚖️ **中期趋势：** 震荡不明。")
        w52 = fund.get('52w_Change')
        st.write(f"**近一年涨跌幅:** {f'{w52*100:.1f}%' if w52 else '未知'}")
        if w52 and w52 > 0.2: st.caption("🚀 过去一年显著跑赢大盘。")
        elif w52 and w52 < -0.1: st.caption("⚓ 过去一年走势弱于大盘。")

    st.markdown("---")
    st.markdown("### 📝 综合诊断结论与操作建议")
    
    score = 0
    reasons = []

    if current_p > ma60 and ma20 > ma60:
        score += 1
        reasons.append("✔ **趋势面向好：** 价格稳居60日生命线及20日均线上方，处于多头通道。")
    elif current_p < ma60:
        score -= 1
        reasons.append("❌ **趋势面走弱：** 价格已跌破60日生命线，中线资金呈流出态势。")
    else:
        reasons.append("➖ **趋势面纠结：** 均线系统方向未明，处于震荡整理期。")

    if pe is not None:
        if pe < 20 and (roe is not None and roe > 0.10):
            score += 1
            reasons.append("✔ **基本面优秀：** 估值较低（PE<20）且盈利能力强劲（ROE>10%），具备长线配置价值。")
        elif pe > 40:
            score -= 1
            reasons.append("❌ **基本面高估：** 动态市盈率偏高，短期存在杀估值的泡沫破裂风险。")

    if rsi > 70:
        score -= 1
        reasons.append("❌ **情绪面过热：** RSI指标进入超买区，短期散户FOMO情绪严重，随时面临回调。")
    elif rsi < 30:
        score += 1
        reasons.append("✔ **情绪面超卖：** RSI指标极度冰点，做空动能衰竭，具备技术性反弹条件。")
    
    if score >= 2:
        st.success("🟢 **核心结论：强烈看多 (Strong Buy / Hold)**")
        st.write("多维因子产生共振向好，建议积极配置或坚定持有底仓。")
    elif score == 1:
        st.info("🟡 **核心结论：谨慎乐观 (Cautious Optimism)**")
        st.write("整体偏向多头，基本面或趋势有亮点，可逢低适度建仓，但需注意防守。")
    elif score == 0:
        st.warning("⚪ **核心结论：中性观望 (Neutral)**")
        st.write("多空因素交织，缺乏明确的单边驱动力，建议多看少动，等待方向明朗。")
    else:
        st.error("🔴 **核心结论：防范风险 (Risk Warning / Sell)**")
        st.write("技术面破位或估值严重透支，建议减仓规避或耐心等待真正的企稳信号，切忌盲目接飞刀。")

    with st.expander("🔍 点击查看详细评分理由", expanded=True):
        for reason in reasons:
            st.markdown(reason)

    # ==========================================
    # 💡 新增：投研模型说明与数据字典
    # ==========================================
    st.markdown("---")
    with st.expander("📖 投研模型说明与数据来源 (Methodology & Sources)", expanded=False):
        st.markdown("""
        #### 1. 资金与情绪面 (Momentum & Sentiment)
        * **数据来源：** K线衍生计算 (Yahoo Finance / AKShare)
        * **逻辑依据：** * **RSI (相对强弱指数)：** 采用14日周期计算。`RSI > 70` 被视为市场极度贪婪（超买区），系统予以扣分（-1）；`RSI < 30` 被视为市场极度恐慌（超卖区），具备反弹势能，系统予以加分（+1）。
            * **量能异动：** 对比当日成交量与过去5日平均成交量（Vol_MA5）。若超出均量 1.8 倍，视为资金强介入/强出逃预警。
        
        #### 2. 深度基本面 (Fundamentals)
        * **数据来源：** Yahoo Finance API 公司财报数据底层接口 (`trailingPE`, `returnOnEquity` 等)
        * **逻辑依据：** * **PE (动态市盈率)：** 衡量回本周期。若 `PE < 20` 且 `ROE > 10%`，代表公司既便宜又能赚钱，符合价值投资审美，系统加分（+1）。若 `PE > 40`，除非有极高成长性消化，否则视为泡沫风险，系统扣分（-1）。
            * **ROE (净资产收益率)：** 巴菲特最看重的指标。`ROE > 15%` 判定为优质资产。*(注：部分 A 股或宽基 ETF 无直接财报接口，此项不参与打分。)*

        #### 3. 趋势与宏观对比 (Macro Trend)
        * **数据来源：** 日K线移动平均计算，及52周价格对比。
        * **逻辑依据：** * **双均线趋势：** 20日线为短期防守位，60日线为牛熊生命线。若现价站稳双线（`现价 > MA60` 且 `MA20 > MA60`），视为右侧交易的绝对多头，系统加分（+1）；跌破 MA60 则视为趋势走坏，系统扣分（-1）。
            
        > **⚠️ 免责声明：** 本系统评级机制由固定量化因子（趋势、估值、情绪）赋予机械权重计算得出。结论仅作为交易时的防冲动“交叉验证”参考工具，**绝不构成任何实质性的买卖及投资理财建议**。交易决策需结合当时宏观政策及个人风险承受能力独立做出。
        """)

else:
    st.info("💡 请在上方确认代码后，点击“同步全维数据”。")
