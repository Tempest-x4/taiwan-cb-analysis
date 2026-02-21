import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# 頁面設定
st.set_page_config(page_title="台灣 CB 全市場監控", layout="wide")

# 1. 初始化資料庫
dl = DataLoader()

# 2. 獲取全市場清單 (加入 Loading 提示)
@st.cache_data(ttl=86400)
def get_cb_list():
    try:
        df_info = dl.taiwan_convertible_bond_info()
        # 排除已到期或下櫃的標的 (假設 bond_id 長度為 5 或 6 為正常)
        df_info = df_info[df_info['bond_id'].str.len() >= 5]
        df_info['display_name'] = df_info['bond_id'] + " " + df_info['bond_name']
        return df_info[['bond_id', 'display_name']].values.tolist()
    except:
        return [["15821", "15821 耀勝一"]]

cb_options = get_cb_list()

# --- 側邊欄設定 ---
st.sidebar.header("📊 全市場掃描參數")
vol_multiplier = st.sidebar.slider("成交量翻倍數 (爆量)", 1.5, 5.0, 3.0)
hold_days = st.sidebar.slider("回測持有天數", 10, 120, 60)

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 手動選取")
selected_cb_pair = st.sidebar.selectbox(
    f"目前共有 {len(cb_options)} 檔 CB",
    options=cb_options,
    format_func=lambda x: x[1]
)
target_id = selected_cb_pair[0]

# --- 核心運算邏輯 ---
@st.cache_data(ttl=3600)
def fetch_and_calc(bond_id, vol_m, hold):
    start_dt = (datetime.now() - timedelta(days=500)).strftime('%Y-%m-%d')
    try:
        df = dl.taiwan_stock_daily(stock_id=bond_id, start_date=start_dt)
        if df is None or df.empty or len(df) < 20: return None
        
        df.columns = [c.lower() for c in df.columns]
        vol_col = 'trading_volume' if 'trading_volume' in df.columns else 'volume'
        
        df['ma20_v'] = df[vol_col].rolling(20).mean()
        df['signal'] = df[vol_col] > (df['ma20_v'] * vol_m)
        df['future_p'] = df['close'].shift(-hold)
        df['return'] = (df['future_p'] - df['close']) / df['close']
        return df
    except:
        return None

# --- 主畫面：單檔分析 ---
st.title(f"📈 {selected_cb_pair[1]}")
df = fetch_and_calc(target_id, vol_multiplier, hold_days)

if df is not None:
    signals = df[df['signal'] == True].dropna(subset=['return'])
    c1, c2, c3 = st.columns(3)
    c1.metric("爆量次數", f"{len(signals)} 次")
    c2.metric("平均報酬", f"{signals['return'].mean():.2%}" if not signals.empty else "0%")
    c3.metric("勝率", f"{(signals['return'] > 0).mean():.1%}" if not signals.empty else "0%")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['close'], name='價格', line=dict(color='#17becf')))
    fig.add_trace(go.Scatter(x=signals['date'], y=signals['close'], mode='markers', name='訊號', marker=dict(color='red', size=10)))
    st.plotly_chart(fig, use_container_width=True)

# --- 全市場雷達：掃描近期訊號 ---
st.markdown("---")
st.subheader("📡 全市場爆量雷達 (掃描中...)")

if st.button("🚀 開始全市場掃描 (檢查近3日訊號)"):
    hot_picks = []
    progress_text = "掃描進度..."
    my_bar = st.progress(0, text=progress_text)
    
    total = len(cb_options)
    for idx, cb_item in enumerate(cb_options):
        # 顯示進度
        my_bar.progress((idx + 1) / total, text=f"正在掃描: {cb_item[1]}")
        
        tdf = fetch_and_calc(cb_item[0], vol_multiplier, hold_days)
        if tdf is not None and not tdf.empty:
            # 檢查最後 3 天是否有 signal 為 True
            if tdf.tail(3)['signal'].any():
                hot_picks.append(cb_item[1])
                
    my_bar.empty()
    if hot_picks:
        st.success(f"🔥 近 3 日符合【{vol_multiplier}倍爆量】的標的：")
        st.write(", ".join(hot_picks))
    else:
        st.info("近 3 日全市場無符合條件的爆量標的。")
