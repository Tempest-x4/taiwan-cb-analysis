import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# 頁面設定
st.set_page_config(page_title="台灣 CB 數據中心", layout="wide")

# 1. 初始化資料庫
dl = DataLoader()

# 2. 獲取全市場 CB 清單與詳細資訊
@st.cache_data(ttl=86400)
def get_all_cb_info():
    try:
        df_info = dl.taiwan_convertible_bond_info()
        # 整理顯示名稱
        df_info['display_name'] = df_info['bond_id'] + " " + df_info['bond_name']
        return df_info
    except:
        return pd.DataFrame()

df_cb_master = get_all_cb_info()

# --- 側邊欄設定 ---
st.sidebar.header("🎯 標的選擇")
if not df_cb_master.empty:
    cb_list = df_cb_master[['bond_id', 'display_name']].values.tolist()
    selected_cb_pair = st.sidebar.selectbox(
        f"全市場共 {len(cb_list)} 檔 CB",
        options=cb_list,
        format_func=lambda x: x[1]
    )
    target_id = selected_cb_pair[0]
else:
    st.sidebar.error("無法載入清單")
    target_id = "15821"

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 回測參數")
vol_multiplier = st.sidebar.slider("成交量翻倍數 (爆量)", 1.5, 5.0, 2.5)
hold_days = st.sidebar.slider("回測持有天數", 10, 120, 60)

# --- 主畫面區 ---
st.title(f"🔍 {selected_cb_pair[1] if not df_cb_master.empty else target_id} 綜合資訊")

# 區塊一：CB 基本參數表
st.subheader("📋 債券詳細參數")
if not df_cb_master.empty:
    detail = df_cb_master[df_cb_master['bond_id'] == target_id].iloc[0]
    
    # 用 Columns 顯示資訊卡
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("轉換價格", f"${detail.get('conversion_price', 'N/A')}")
    col2.metric("發行總額", f"{detail.get('issue_amount', 0):,.0f} (千元)")
    col3.metric("發行日期", detail.get('issue_date', 'N/A'))
    col4.metric("到期日期", detail.get('due_date', 'N/A'))
    
    # 更多詳細資訊的表格
    with st.expander("查看完整參數細節"):
        st.table(pd.DataFrame(detail).drop('display_name').rename(columns={detail.name: "參數值"}))

# 區塊二：量能績效回測
st.markdown("---")
st.subheader("📉 量能爆量回測圖")

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

df_backtest = fetch_and_calc(target_id, vol_multiplier, hold_days)

if df_backtest is not None:
    signals = df_backtest[df_backtest['signal'] == True].dropna(subset=['return'])
    
    # 績效摘要
    s_col1, s_col2, s_col3 = st.columns(3)
    s_col1.metric("爆量訊號次數", f"{len(signals)} 次")
    s_col2.metric("平均報酬", f"{signals['return'].mean():.2%}" if not signals.empty else "0%")
    s_col3.metric("策略勝率", f"{(signals['return'] > 0).mean():.1%}" if not signals.empty else "0%")
    
    # 交互式圖表
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_backtest['date'], y=df_backtest['close'], name='價格', line=dict(color='#17becf')))
    fig.add_trace(go.Scatter(x=signals['date'], y=signals['close'], 
                             mode='markers', name='大量買入點', 
                             marker=dict(color='red', size=10, symbol='star')))
    
    fig.update_layout(height=450, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("查無交易資料，可能該債券剛發行或已到期下櫃。")
