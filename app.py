import streamlit as st
import akshare as ak
import datetime
import time

# --- 页面设置 ---
st.set_page_config(page_title="黄金ETF(159934) 加仓推演", page_icon="📈", layout="centered")

# --- 初始化会话状态 (记住你的默认数据) ---
if 'current_price' not in st.session_state:
    st.session_state.current_price = 10.514  # 默认现价
if 'update_time' not in st.session_state:
    st.session_state.update_time = "手动设置"

# --- 获取最新现价的函数 ---
def fetch_realtime_price(symbol="159934"):
    try:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=30)
        df = ak.fund_etf_hist_em(symbol=symbol, period="daily", 
                                 start_date=start_date.strftime("%Y%m%d"), 
                                 end_date=end_date.strftime("%Y%m%d"), adjust="qfq")
        if df is not None and not df.empty:
            latest_price = float(df.iloc[-1]['收盘'])
            latest_date = df.iloc[-1]['日期']
            return latest_price, f"{latest_date} 收盘价"
    except Exception as e:
        return None, str(e)
    return None, "获取失败"

# --- 界面构建 ---
st.title("📈 黄金 ETF (159934) 加仓风控模拟器")
st.markdown("搭配 Python 后端，一键获取最新行情，精准推演加仓风险。")

# 1. 顶部数据刷新区
st.subheader("📡 行情数据区")
col1, col2 = st.columns([2, 1])

with col1:
    # 现价输入框，绑定 session_state
    new_price = st.number_input("当前市场现价 (元)", value=st.session_state.current_price, step=0.001, format="%.3f")
    st.session_state.current_price = new_price # 同步手动修改
    st.caption(f"数据状态: {st.session_state.update_time}")

with col2:
    st.write("") # 占位对齐
    st.write("")
    # 点击按钮触发 Python 代码
    if st.button("🔄 获取最新现价", type="primary", use_container_width=True):
        with st.spinner('正在通过 AKShare 抓取数据...'):
            price, msg = fetch_realtime_price()
            if price:
                st.session_state.current_price = price
                st.session_state.update_time = msg
                st.rerun() # 强制刷新页面以显示新价格
            else:
                st.error("网络请求失败，请稍后再试。")

st.divider()

# 2. 持仓与推演区
st.subheader("⚙️ 你的持仓与加仓推演")

c1, c2 = st.columns(2)
with c1:
    cost_old = st.number_input("底仓平均成本 (元)", value=8.592, step=0.01)
with c2:
    qty_old = st.number_input("底仓持有股数 (股)", value=3776, step=100)

qty_add = st.slider("打算在当前价格加仓多少股？", min_value=0, max_value=10000, value=0, step=100)

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
    st.metric(label="加仓后新保本点", value=f"¥ {new_avg_cost:.3f}")
with r2:
    st.metric(label="利润安全垫 (可承受跌幅)", value=f"{drop_to_loss_pct:.2f}%")

# 进度条提示
if drop_to_loss_pct < 5:
    st.error("⚠️ 极度危险：安全垫极薄，稍微回调就会全盘亏损！")
elif drop_to_loss_pct < 10:
    st.warning("⚡ 提示：安全垫被大幅压缩，建议设置严格止损。")
else:
    st.success("✅ 状态健康：底仓利润足以覆盖正常回调。")
