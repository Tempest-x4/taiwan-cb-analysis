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
@st.cache_data(ttl=86400) # 每天更新一次清單即可
def get_cb_list():
    try:
        # 獲取 CB 基本資訊
        df_info = dl.taiwan_convertible_bond_info()
        # 整理成 "代號 名稱" 的格式方便閱讀
        df_info['display_name'] = df_info['bond_id'] + " " + df_info['bond_name']
        return df_info[['bond_id', 'display_name']].values.tolist()
    except:
        # 若 API 故障，提供預設清單
        return [["15821", "15821 耀勝一"], ["30175", "30175 鴻海五"], ["2330", "2330 台積電(示範)"]]

cb_options = get_cb_list()

# --- 側邊欄設定 ---
st.sidebar.header("📊 台灣 CB 總表")
# 將清單放入選取框
selected_cb_pair = st.sidebar.selectbox(
    "請點擊選取標的",
    options=cb_options,
    format_func=lambda x: x[1] # 顯示 "代號 名稱"
)
target_id = selected_cb_pair[0]

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 策略參數")
vol_multiplier = st.sidebar.slider("成交量翻
