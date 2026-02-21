import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# 頁面設定
st.set_page_config(page_title="台灣 CB 量能監控儀表板", layout="wide")

# 1. 初始化資料庫
dl = DataLoader()

# 2. 自動抓取全市場 CB 清單
@st.cache_data(ttl=86400)
def get_cb_list():
    try:
        df_info = dl.taiwan_convertible_bond_info()
        df_info['display_name'] = df_info['bond_id'] + " " + df_info['bond_name']
        return df_info[['bond_id', 'display_name']].values.tolist()
    except:
        return [["15821", "15821 耀勝一"]]

cb_options = get_cb_list()

# --- 側邊欄設定 ---
st.sidebar.header("📊 參數設定")
vol_multiplier = st.sidebar.slider("成交量翻倍數", 1.5, 5.0, 2.5)
hold_days = st.sidebar.slider("買入後持有天數", 10, 120, 60)

st.sidebar.markdown("---")
st.sidebar.header("🔍 選取標的")
selected_cb_pair = st.sidebar.selectbox(
    "請選擇 CB 進行回測",
    options=cb_options,
    format_func=lambda x: x[1]
)
target_id = selected_cb_pair[0]

# --- 核心運算邏輯 ---
@st.cache_data(ttl=3600)
def fetch_and_calc(bond_id, vol_m, hold):
    start_dt = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    try:
        df = dl.taiwan_stock_daily(stock_id=bond_id, start_date=start_dt)
        if df is None or df.empty: return None
        df.columns = [c.lower() for c in df.columns]
        vol_col = 'trading_volume' if 'trading_volume' in df.columns else 'volume'
        df['ma20_v'] = df[vol_col].rolling(20).mean()
        df['signal'] = df[vol_col] > (df['ma20_v'] * vol_m)
        df['future_p'] = df['close'].shift(-hold)
        df['return'] = (df['future_p'] - df['close']) / df['close']
        return df
    except:
        return None

# --- 主畫面顯示 ---
st.title(f"📈 {selected_cb_pair[1]} 績效追蹤")

df = fetch_and_calc(target_id, vol_multiplier, hold_days)

if df is not None:
    # 績效指標
    signals = df[df['signal'] == True].dropna(subset=['return'])
    c1, c2, c3 = st.columns(3)
    avg_ret = signals['return'].mean() if not signals.empty else 0
    win_rate = (signals['return'] > 0).mean() if not signals.empty else 0
    
    c1.metric("歷史爆量次數", f"{len(signals)} 次")
    c2.metric(f"平均 {hold_days}日報酬", f"{avg_ret:.2%}")
    c3.metric("策略勝率", f"{win_rate:.1%}")

    # 繪圖
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['close'], name='價格走勢', line=dict(color='#17becf')))
    fig.add_trace(go.Scatter(x=signals['date'], y=signals['close'], 
                             mode='markers', name='大量買入訊號', 
                             marker=dict(color='red', size=12, symbol='star')))
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # --- 今日爆量雷達 (最近3日有訊號的 CB) ---
    st.markdown("---")
    st.subheader("📡 近期爆量雷達 (找出潛在機會)")
    st.info("系統會檢查前 30 檔熱門 CB 中，最近 3 天內是否出現爆量買入點。")
    
    hot_picks = []
    # 掃描部分標的作為範例 (為了網頁速度)
    for cb_item in cb_options[:30]:
        test_df = fetch_and_calc(cb_item[0], vol_multiplier, hold_days)
        if test_df is not None and not test_df.empty:
            last_3_days = test_df.tail(3)
            if last_3_days['signal'].any():
                hot_picks.append(cb_item[1])
    
    if hot_picks:
        st.success(f"🔥 近 3 日出現訊號的標的：{', '.join(hot_picks)}")
    else:
        st.write("目前近期無新訊號出現。")

else:
    st.warning("無法取得資料，可能代號已失效。")
