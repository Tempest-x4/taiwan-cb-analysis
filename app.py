import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime
import requests

st.set_page_config(page_title="CB 獵人 - 雲端穩定版", layout="wide")

# 1. 建立備援清單 (如果官方掛掉，至少這些熱門股可以動)
DEFAULT_CB = [
    {"id": "15821", "name": "耀勝一", "conv_p": 120.5, "stock": "1582"},
    {"id": "30175", "鴻海五": 120.0, "stock": "2317"},
    {"id": "62231", "name": "旺矽一", "conv_p": 250.0, "stock": "6223"},
    {"id": "35483", "name": "兆利三", "conv_p": 240.0, "stock": "3548"}
]

@st.cache_data(ttl=86400)
def get_cb_list():
    url = "https://www.tpex.org.tw/openapi/v1/bond_issue_info_cb"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            df['轉換價格'] = pd.to_numeric(df['轉換價格'], errors='coerce')
            df['stock_id'] = df['債券代碼'].str[:4]
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 主畫面 ---
st.title("🏹 CB 獵人：全自動即時掃描儀")

# 獲取清單
df_raw = get_cb_list()

# 如果官方 API 失敗，使用手動定義的熱門清單
if df_raw.empty:
    st.warning("⚠️ 官方資料庫連線超時，目前使用【熱門監控清單】模式運行。")
    df_active = pd.DataFrame([
        ["15821", "耀勝一", 120.5, "1582"],
        ["30175", "鴻海五", 130.0, "2317"],
        ["65152", "穎崴二", 750.0, "6515"],
        ["35483", "兆利三", 244.5, "3548"],
        ["80541", "安國一", 135.0, "8054"]
    ], columns=['債券代碼', '債券簡稱', '轉換價格', 'stock_id'])
else:
    df_active = df_raw[['債券代碼', '債券簡稱', '轉換價格', 'stock_id']].copy()

# --- 核心運算 ---
if st.button("🚀 執行即時溢價率分析"):
    with st.spinner("正在與市場同步數據..."):
        # 準備代號 (CB 使用 .TWO, 現股嘗試 .TW 與 .TWO)
        cb_ids = [f"{i}.TWO" for i in df_active['債券代碼']]
        stk_ids = [f"{i}.TW" for i in df_active['stock_id']] + [f"{i}.TWO" for i in df_active['stock_id']]
        
        # 批次下載
        all_data = yf.download(cb_ids + stk_ids, period="1d", interval="5m", group_by='ticker')
        
        results = []
        for _, row in df_active.iterrows():
            try:
                # 抓取 CB 價格
                cb_price = all_data[f"{row['債券代碼']}.TWO"]['Close'].iloc[-1]
                # 抓取現股價格 (優先找上市 .TW，找不到找上櫃 .TWO)
                stk_price = None
                if f"{row['stock_id']}.TW" in all_data:
                    stk_price = all_data[f"{row['stock_id']}.TW"]['Close'].dropna().iloc[-1]
                if stk_price is None and f"{row['stock_id']}.TWO" in all_data:
                    stk_price = all_data[f"{row['stock_id']}.TWO"]['Close'].dropna().iloc[-1]
                
                if cb_price and stk_price:
                    conv_value = (stk_price / row['轉換價格']) * 100
                    premium = (cb_price / conv_value - 1) * 100
                    results.append({
                        "代碼": row['債券代碼'], "簡稱": row['債券簡稱'],
                        "CB市價": round(cb_price, 2), "現股價": round(stk_price, 2),
                        "溢價率(%)": round(premium, 2), "轉換價值": round(conv_value, 2)
                    })
            except:
                continue
        
        if results:
            df_res = pd.DataFrame(results)
            
            # 圖表展示
            fig = px.scatter(
                df_res, x="CB市價", y="溢價率(%)", 
                color="溢價率(%)", color_continuous_scale="RdYlGn_r",
                hover_name="簡稱", text="簡稱", template="plotly_dark", height=600,
                title="CB 價值象限圖（左下角為黃金區：保本+低溢價）"
            )
            fig.add_hline(y=0, line_color="white", annotation_text="平價線")
            fig.add_hrect(y0=-5, y1=5, fillcolor="green", opacity=0.2, annotation_text="甜點區")
            st.plotly_chart(fig, use_container_width=True)
            
            # 清單展示
            st.subheader("📋 掃描結果詳細清單")
            st.dataframe(df_res.sort_values("溢價率(%)"), use_container_width=True)
        else:
            st.error("❌ 抓不到即時價格。請確認目前是否為交易日 09:00 - 14:00。")
