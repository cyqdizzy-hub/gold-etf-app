import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 页面设置 ---
st.set_page_config(page_title="通用投资决策仪表盘", page_icon="📈", layout="wide")

# --- 0. 智能分类引擎 ---
def get_category(symbol):
    symbol = str(symbol).strip().upper()
    if symbol.endswith(".SZ") or symbol.endswith(".SS"):
        if symbol.startswith("15") or symbol.startswith("51"):
            return "📊 国内 ETF"
        else:
            return "🇨🇳 A股个股"
    elif symbol.endswith(".HK"):
        return "🇭🇰 港股"
    elif symbol.isalpha():
        return "🇺🇸 美股"
    else:
        return "🌍 其他标的"

# --- 1. 初始化会话状态 ---
if 'current_price' not in st.session_state:
    st.session_state.current_price = 0.0
if 'df_history' not in st.session_state:
    st.session_state.df_history = pd.DataFrame()

# 初始底仓数据
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = {
        "159934.SZ": {"name": "黄金ETF", "cost": 8.592, "qty": 3776, "category": "📊 国内 ETF"}, 
        "513100.SS": {"name": "纳指100", "cost": 1.200, "qty": 1000, "category": "📊 国内 ETF"},
        "AAPL": {"name": "苹果公司", "cost": 150.0, "qty": 50, "category": "🇺🇸 美股"}
    }

if 'sidebar_select' not in st.session_state:
    st.session_state.sidebar_select = "159934.SZ"

# --- 2. 侧边栏：分类导航列表 ---
st.sidebar.title("⭐ 我的自选库")

if st.sidebar.button("➕ 手动输入新标的", type="primary" if st.session_state.sidebar_select == "" else "secondary", use_container_width=True):
    st.session_state.sidebar_select = ""
    st.rerun()

st.sidebar.divider()

categories_dict = {}
for sym, data in st.session_state.watchlist.items():
    cat = data.get('category', '🌍 其他标的')
    if cat not in categories_dict:
        categories_dict[cat] = []
    categories_dict[cat].append((sym, data))

for cat, items in categories_dict.items():
    st.sidebar.caption(f"**{cat}**") 
    for sym, data in items:
        col1, col2 = st.sidebar.columns([4, 1])
        btn_type = "primary" if st.session_state.sidebar_select == sym else "secondary"
        
        display_name = data.get('name', '')
        btn_label = f"{display_name} ({sym})" if display_name else f"📊 {sym}"
        
        if col1.button(btn_label, key=f"sel_{sym}", type=btn_type, use_container_width=True):
            st.session_state.sidebar_select = sym
            st.rerun()
            
        if col2.button("🗑️", key=f"del_{sym}", help=f"删除 {sym}"):
            del st.session_state.watchlist[sym]
            if st.session_state.sidebar_select == sym:
                st.session_state.sidebar_select = ""
            st.rerun()
    st.sidebar.write("")

# 获取当前选中项的默认值
if st.session_state.sidebar_select and st.session_state.sidebar_select in st.session_state.watchlist:
    default_sym = st.session_state.sidebar_select
    default_data = st.session_state.watchlist[default_sym]
    default_name = default_data.get('name', '')
    default_cost = float(default_data.get('cost', 0.0))
    default_qty = int(default_data.get('qty', 0))
else:
    default_sym = ""
    default_name = ""
    default_cost = 0.0
    default_qty = 0

# --- 3. 数据抓取与指标计算函数 ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data_and_calc_ind(symbol):
    try:
        df = yf.download(symbol, period="1y", progress=False, threads=False)
        if df is None or len(df) == 0:
            return None, "获取数据失败，请检查代码格式是否正确。"
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        return df.iloc[-126:], "成功"
    except Exception as e:
        return None, str(e)

# --- 4. K 线图绘制函数 ---
def plot_candlestick(df, symbol, name):
    title = f"{name} ({symbol}) - 6个月日K线图" if name else f"{symbol} - 6个月日K线图"
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.8], subplot_titles=(title, '成交量'))
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日线', line=dict(color='#ffca28', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60日线', line=dict(color='#2196f3', width=1.5)), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='#90caf9'), row=2, col=1)
    fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# ==========================================
#                  主界面构建
# ==========================================
st.title("📈 通用投资决策仪表盘")

# 💡 核心修复：给输入框生成专属的动态 Key
# 这样每次切换侧边栏标的，输入框就会瞬间刷新为后台记忆的值
ui_key = default_sym if default_sym else "new_entry"

with st.container():
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1, 1, 1.2])
    
    with c1: 
        input_symbol = st.text_input("🔍 标的代码", value=default_sym, key=f"sym_{ui_key}", help="深市:.SZ, 沪市:.SS, 美股直接输")
    with c2: 
        input_name = st.text_input("🏷️ 标的名称(选填)", value=default_name, key=f"name_{ui_key}", placeholder="如: 黄金ETF")
    with c3: 
        input_cost = st.number_input("底仓成本", value=default_cost, step=0.01, key=f"cost_{ui_key}")
    with c4: 
        input_qty = st.number_input("持仓数量", value=default_qty, step=100, key=f"qty_{ui_key}")
    
    with c5:
        st.write("") 
        if st.button("🔄 同步K线与现价", type="primary", use_container_width=True):
            if input_symbol:
                with st.spinner(f'正在同步 {input_symbol} ...'):
                    df_h, msg = fetch_data_and_calc_ind(input_symbol)
                    if df_h is not None:
                        st.session_state.df_history = df_h
                        st.session_state.current_price = float(df_h.iloc[-1]['Close'])
                    else:
                        st.error(f"❌ 获取失败：{msg}")

# --- 保存自选动作 ---
if st.button("💾 将当前标的保存/更新至左侧分类列表"):
    if input_symbol:
        auto_category = get_category(input_symbol)
        
        st.session_state.watchlist[input_symbol] = {
            "name": input_name, 
            "cost": input_cost, 
            "qty": input_qty,
            "category": auto_category 
        }
        st.session_state.sidebar_select = input_symbol 
        st.success(f"✅ {input_name or input_symbol} 已成功保存，底仓成本和数量已更新！")
        st.rerun() 

st.divider()

# 2. 中部：K 线图展示
if not st.session_state.df_history.empty and st.session_state.current_price > 0:
    fig_k = plot_candlestick(st.session_state.df_history, input_symbol, input_name)
    st.plotly_chart(fig_k, use_container_width=True)
else:
    st.info("💡 请在上方确认代码后，点击“同步K线与现价”。")

st.divider()

# 3. 底部：加仓推演 
if not st.session_state.df_history.empty and st.session_state.current_price > 0:
    col_calc, col_adv = st.columns([1, 1.2], gap="large")
    
    with col_calc:
        st.subheader("⚙️ 动态加仓推演")
        st.metric("最新现价", f"¥ {st.session_state.current_price:.3f}")
        
        # 滑块的最大值自动根据你的持仓动态调整
        qty_add = st.slider("计划加仓数量", min_value=0, max_value=int(max(input_qty * 2, 1000)), value=0, step=100, key=f"slider_{ui_key}")
        
        total_qty = input_qty + qty_add
        current_p = st.session_state.current_price
        
        if total_qty > 0:
            new_cost = ((input_cost * input_qty) + (current_p * qty_add)) / total_qty
            safe_cushion = ((current_p - new_cost) / current_p) * 100 if current_p > 0 else 0
        else:
            new_cost, safe_cushion = input_cost, 0

        r1, r2 = st.columns(2)
        r1.metric("加仓后新保本点", f"{new_cost:.3f}", f"成本抬升 {new_cost-input_cost:.3f}" if qty_add > 0 else None, delta_color="inverse")
        r2.metric("利润安全垫", f"{safe_cushion:.2f}%")

    with col_adv:
        st.subheader("🤖 智能决策建议")
        df = st.session_state.df_history
        ma20, ma60 = df.iloc[-1]['MA20'], df.iloc[-1]['MA60']
        
        if current_p > ma60 and ma20 > ma60:
            st.success("📈 **多头趋势**：价格站上60日均线。")
            if 0 < (current_p - ma20)/ma20 < 0.02:
                st.success("🎯 **绝佳买点**：已回调至20日线附近，支撑较强。")
            elif (current_p - ma20)/ma20 >= 0.02:
                st.warning("⏳ **注意追高**：偏离20日线较远，建议等待回调。")
        elif current_p < ma60:
            st.error("📉 **空头/调整趋势**：已跌破60日生命线，严禁盲目加仓，等待企稳。")
        else:
            st.info("⚖️ **震荡整理**：趋势不清晰，多看少动。")
            
        if qty_add > 0:
            st.markdown("---")
            st.markdown(f"**🛡️ 本次加仓防守线：** 若跌破 20日线 ({ma20:.3f}) 平掉新仓；若跌破新成本线 ({new_cost:.3f}) 彻底清仓保本。")
