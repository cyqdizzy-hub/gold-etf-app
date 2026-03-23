import streamlit as st
import yfinance as yf
import datetime

# --- 页面设置 ---
st.set_page_config(page_title="通用加仓风控模拟器", page_icon="📈", layout="centered")

# --- 初始化会话状态 ---
if 'current_price' not in st.session_state:
    st.session_state.current_price = 10.514  # 默认现价
if 'update_time' not in st.session_state:
    st.session_state.update_time = "手动设置"
if 'target_symbol' not in st.session_state:
    st.session_state.target_symbol = "159934.SZ" # 默认标的

# --- 通用数据抓取函数 ---
def fetch_realtime_price(symbol):
    try:
        # 核心改动：这里的 symbol 变成了动态传入的变量
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if not hist.empty:
            latest_price = float(hist['Close'].iloc[-1])
            latest_date = hist.index[-1].strftime("%Y-%m-%d")
            return latest_price, f"{latest_date} 收盘价"
    except Exception as e:
        return None, str(e)
    return None, "获取失败"

# --- 界面构建 ---
st.title("📈 通用加仓风控模拟器")
st.markdown("支持 A股、美股、ETF。输入代码即可一键测算加仓风险。")

# 核心改动：增加代码输入框
st.session_state.target_symbol = st.text_input(
    "🔍 请输入标的代码 (深市加.SZ / 沪市加.SS / 美股直接输字母)", 
    value=st.session_state.target_symbol,
    help="例如：159934.SZ (黄金ETF), 510300.SS (沪深300ETF), AAPL (苹果公司)"
)

st.divider()

# 1. 顶部数据刷新区
st.subheader("📡 行情数据区")
col1, col2 = st.columns([2, 1])

with col1:
    new_price = st.number_input("当前市场现价", value=st.session_state.current_price, step=0.001, format="%.3f")
    st.session_state.current_price = new_price 
    st.caption(f"数据状态: {st.session_state.update_time}")

with col2:
    st.write("") 
    st.write("")
    if st.button("🔄 获取最新现价", type="primary", use_container_width=True):
        # 按钮按下时，把输入框里的代码传给后台函数
        with st.spinner(f'正在抓取 {st.session_state.target_symbol} 最新数据...'):
            price, msg = fetch_realtime_price(st.session_state.target_symbol)
            if price:
                st.session_state.current_price = price
                st.session_state.update_time = msg
                st.rerun() 
            else:
                st.error("❌ 获取失败，请检查代码格式是否正确（A股切记加上 .SZ 或 .SS 后缀）。")

st.divider()

# 2. 持仓与推演区
st.subheader("⚙️ 你的持仓与加仓推演")

c1, c2 = st.columns(2)
with c1:
    cost_old = st.number_input("底仓平均成本", value=8.592, step=0.01)
with c2:
    qty_old = st.number_input("底仓持有数量 (股/份)", value=3776, step=100)

qty_add = st.slider("打算在当前价格加仓多少？", min_value=0, max_value=int(qty_old * 3), value=0, step=100)

# --- 核心计算逻辑 ---
total_qty = qty_old + qty_add
current_p = st.session_state.current_price

if total_qty > 0:
    new_avg_cost = ((cost_old * qty_old) + (current_p * qty_add)) / total_qty
    drop_to_loss_pct = ((current_p - new_avg_cost) / current_p) * 100 if current_p > 0 else 0
else:
    new_avg_cost = cost_old
    drop_to_loss_pct = 0

# --- 结果展示 ---
st.subheader("📊 核心风控指标")

r1, r2 = st.columns(2)
with r1:
    st.metric(label="加仓后新保本点", value=f"{new_avg_cost:.3f}")
with r2:
    st.metric(label="利润安全垫 (可承受跌幅)", value=f"{drop_to_loss_pct:.2f}%")

# 进度条提示
if drop_to_loss_pct < 5:
    st.error("⚠️ 极度危险：安全垫极薄，稍微回调就会全盘亏损！")
elif drop_to_loss_pct < 10:
    st.warning("⚡ 提示：安全垫被大幅压缩，建议设置严格止损。")
else:
    st.success("✅ 状态健康：底仓利润足以覆盖正常回调。")
