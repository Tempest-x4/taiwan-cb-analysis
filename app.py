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
    # 預設顯示 15821 耀勝一
    default_idx = next((i for i, x in enumerate(cb_list) if "15821" in x[0]), 0)
    selected_cb_pair = st.sidebar.selectbox(
        f"全市場共 {len(cb_list)} 檔",
        options=cb_list,
        index=default_idx,
        format_func=lambda x: x[1]
    )
    target_id = selected_cb_pair[0]
else:
    st.sidebar.error("資料載入失敗，請重新整理")
    target_id = "15821"

# --- 主畫面顯示 ---
st.title(f"📊 {selected_cb_pair[1] if not df_cb_master.empty else target_id}")

# 區塊一：CB 基本資料表格
if not df_cb_master.empty:
    detail_rows = df_cb_master[df_cb_master['bond_id'] == target_id]
    if not detail_rows.empty:
        detail = detail_rows.iloc[0]
        
        # 建立四個資訊欄位
        c1, c2, c3, c4 = st.columns(4)
        c1.write("**轉換價格**")
        c1.info(f"${detail.get('conversion_price', 'N/A')}")
        
        c2.write("**發行金額**")
        c2.info(f"{detail.get('issue_amount', 0):,.0f}")
        
        c3.write("**發行日期**")
        c3.info(detail.get('issue_date', 'N/A'))
        
        c4.write("**到期日期**")
        c4.info(detail.get('due_date', 'N/A'))

# 區塊二：價格與成交量圖表
@st.cache_data(ttl=3600)
def fetch_basic_data(bond_id):
    start_dt = (datetime.now() - timedelta(days=1000)).strftime('%Y-%m-%d')
    # 嘗試抓取日成交資料
    df = dl.taiwan_stock_daily(stock_id=bond_id, start_date=start_dt)
    if df is None or df.empty:
        df = dl.taiwan_convertible_bond_daily(bond_id=bond_id, start_date=start_dt)
    return df

df_raw = fetch_basic_data(target_id)

st.markdown("---")

if df_raw is not None and not df_raw.empty:
    # 整理欄位
    df = df_raw.copy()
    df.columns = [c.lower() for c in df.columns]
    vol_col = 'trading_volume' if 'trading_volume' in df.columns else 'volume'
    
    # 建立子圖：上方價格，下方成交量
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                       vertical_spacing=0.1, subplot_titles=(f'{target_id} 價格走勢', '成交量'),
                       row_width=[0.3, 0.7])

    # 價格線
    fig.add_trace(go.Scatter(x=df['date'], y=df['close'], name='收盤價', line=dict(color='#17becf', width=2)), row=1, col1)
    
    # 成交量長條圖
    fig.add_trace(go.Bar(x=df['date'], y=df[vol_col], name='成交量', marker_color='orange', opacity=0.7), row=2, col1)

    fig.update_layout(height=600, template="plotly_dark", showlegend=False, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    
    # 顯示原始資料表供查驗
    with st.expander("查看原始交易數據清單"):
        st.dataframe(df.sort_values('date', ascending=False), use_container_width=True)
else:
    st.warning(f"目前代號 {target_id} 在資料庫中查無近期交易紀錄。")
