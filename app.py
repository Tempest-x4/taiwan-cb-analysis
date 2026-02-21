import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# 頁面設定
st.set_page_config(page_title="台灣 CB 瀏覽器", layout="wide")

# 1. 初始化資料庫
dl = DataLoader()

# 2. 獲取全市場 CB 清單
@st.cache_data(ttl=86400)
def get_all_cb_info():
    try:
        df_info = dl.taiwan_convertible_bond_info()
        df_info['bond_id'] = df_info['bond_id'].astype(str).str.strip()
        df_info['display_name'] = df_info['bond_id'] + " " + df_info['bond_name']
        return df_info
    except:
        return pd.DataFrame()

df_cb_master = get_all_cb_info()

# --- 側邊欄設定 ---
st.sidebar.header("📂 選擇 CB 標的")
if not df_cb_master.empty:
    cb_list = df_cb_master[['bond_id', 'display_name']].values.tolist()
    # 預設顯示 15821 耀勝一，若找不到則選第一個
    default_idx = next((i for i, x in enumerate(cb_list) if "15821" in x[0]), 0)
    selected_cb_pair = st.sidebar.selectbox(
        f"全市場共 {len(cb_list)} 檔",
        options=cb_list,
        index=default_idx,
        format_func=lambda x: x[1]
    )
    target_id = selected_cb_pair[0]
else:
    st.sidebar.error("資料載入失敗")
    target_id = "15821"

# --- 主畫面顯示 ---
st.title(f"📊 {selected_cb_pair[1] if not df_cb_master.empty else target_id}")

# 區塊一：CB 基本資料卡
if not df_cb_master.empty:
    detail_rows = df_cb_master[df_cb_master['bond_id'] == target_id]
    if not detail_rows.empty:
        detail = detail_rows.iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("轉換價格", f"${detail.get('conversion_price', 'N/A')}")
        c2.metric("發行金額 (千)", f"{detail.get('issue_amount', 0):,.0f}")
        c3.metric("發行日期", detail.get('issue_date', 'N/A'))
        c4.metric("到期日期", detail.get('due_date', 'N/A'))

# 區塊二：數據抓取
@st.cache_data(ttl=3600)
def fetch_basic_data(bond_id):
    start_dt = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    # 優先嘗試股票日成交接口
    try:
        df = dl.taiwan_stock_daily(stock_id=bond_id, start_date=start_dt)
        if df is None or df.empty:
            df = dl.taiwan_convertible_bond_daily(bond_id=bond_id, start_date=start_dt)
        return df
    except:
        return None

df_raw = fetch_basic_data(target_id)

st.markdown("---")

if df_raw is not None and not df_raw.empty:
    # 整理資料
    df = df_raw.copy()
    df.columns = [c.lower() for c in df.columns]
    # 自動判定成交量欄位名稱
    vol_col = 'trading_volume' if 'trading_volume' in df.columns else 'volume'
    
    # 建立子圖
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.1, 
        subplot_titles=('價格走勢', '成交張數'),
        row_heights=[0.7, 0.3]
    )

    # 價格折線圖
    fig.add_trace(
        go.Scatter(x=df['date'], y=df['close'], name='收盤價', line=dict(color='#17becf', width=2)),
        row=1, col=1
    )
    
    # 成交量長條圖
    fig.add_trace(
        go.Bar(x=df['date'], y=df[vol_col], name='成交量', marker_color='orange'),
        row=2, col=1
    )

    fig.update_layout(height=600, template="plotly_dark", showlegend=False, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("💾 查看原始交易數據"):
        st.dataframe(df.sort_values('date', ascending=False), use_container_width=True)
else:
    st.warning("⚠️ 查無此標的之交易資料。可能是該 CB 剛發行或近期無成交量。")
