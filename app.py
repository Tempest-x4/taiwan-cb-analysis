import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# 頁面設定
st.set_page_config(page_title="台灣官方 CB 觀測站", layout="wide")

# 1. 從櫃買中心 (TPEx) 抓取所有 CB 基本資料
@st.cache_data(ttl=86400)
def get_tpex_cb_list():
    # 櫃買中心所有債券基本資料 API
    url = "https://www.tpex.org.tw/openapi/v1/bond_issue_info_cb"
    try:
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data)
        # 整理名稱
        df['display_name'] = df['債券代碼'] + " " + df['債券簡稱']
        return df
    except:
        st.error("官方基本資料介接失敗，請稍後再試")
        return pd.DataFrame()

# 2. 抓取單檔 CB 歷史成交資訊 (以月為單位)
@st.cache_data(ttl=3600)
def get_cb_price_history(cb_id):
    # 使用證交所/櫃買通用格式
    now = datetime.now()
    date_str = now.strftime("%Y%m01")
    url = f"https://www.tpex.org.tw/web/bond/tradeinfo/cb/cb_trading_details_result.php?l=zh-tw&d={date_str}&stkno={cb_id}"
    try:
        res = requests.get(url)
        raw_data = res.json()
        # 提取交易明細
        if 'aaData' in raw_data:
            df = pd.DataFrame(raw_data['aaData'], columns=[
                "日期", "成交千元", "成交張數", "最高價", "最低價", "收盤價", "漲跌", "最後買價", "最後賣價"
            ])
            # 轉換數值
            df['收盤價'] = pd.to_numeric(df['收盤價'], errors='coerce')
            df['成交張數'] = pd.to_numeric(df['成交張數'].str.replace(',', ''), errors='coerce')
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 側邊欄：標的選單 ---
df_master = get_tpex_cb_list()

st.sidebar.header("🏛️ 官方數據源：櫃買中心")
if not df_master.empty:
    cb_options = df_master[['債券代碼', 'display_name']].values.tolist()
    selected_cb = st.sidebar.selectbox(
        "請選擇可轉債標的",
        options=cb_options,
        format_func=lambda x: x[1]
    )
    target_id = selected_cb[0]
else:
    target_id = st.sidebar.text_input("手動輸入 CB 代碼", value="15821")

# --- 主畫面 ---
st.title(f"🔍 {selected_cb[1] if not df_master.empty else target_id} 實時概況")

if not df_master.empty:
    info = df_master[df_master['債券代碼'] == target_id].iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("轉換價格", f"${info['轉換價格']}")
    c2.metric("發行日期", info['發行日期'])
    c3.metric("到期日期", info['到期日期'])
    c4.metric("發行總額", f"{int(info['發行總額']):,} (千)")

# 顯示價格走勢
st.markdown("---")
st.subheader("📅 本月成交紀錄 (官方即時數據)")
df_price = get_cb_price_history(target_id)

if not df_price.empty:
    # 簡單圖表
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_price['日期'], y=df_price['收盤價'], name='收盤價', line=dict(color='#00ffcc')))
    fig.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(df_price, use_container_width=True)
else:
    st.warning("本月暫無成交紀錄，或該標的非透過櫃買中心系統交易。")
