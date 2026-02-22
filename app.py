import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="CB 溢價率即時監控", layout="wide")

# 1. 獲取櫃買中心流通 CB 基本資料
@st.cache_data(ttl=86400)
def get_cb_base_info():
    url = "https://www.tpex.org.tw/openapi/v1/bond_issue_info_cb"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        df = pd.DataFrame(res.json())
        df['轉換價格'] = pd.to_numeric(df['轉換價格'], errors='coerce')
        today = datetime.now().strftime("%Y/%m/%d")
        df = df[df['到期日期'] >= today].copy()
        # 自動建立標的股票代碼 (取前四碼)
        df['stock_id'] = df['債券代碼'].str[:4]
        return df[['債券代碼', '債券簡稱', '轉換價格', 'stock_id']]
    except:
        return pd.DataFrame()

# 2. 獲取即時價格 (CB + 現股)
@st.cache_data(ttl=300)
def get_combined_prices(cb_ids, stock_ids):
    tickers = [f"{cid}.TWO" for cid in cb_ids] + [f"{sid}.TW" for sid in stock_ids] + [f"{sid}.TWO" for sid in stock_ids]
    try:
        data = yf.download(tickers, period="1d", interval="5m", group_by='ticker', threads=True)
        price_map = {}
        for t in tickers:
            try:
                # 取得最後一筆收盤價
                price_map[t] = data[t]['Close'].dropna().iloc[-1]
            except:
                price_map[t] = None
        return price_map
    except:
        return {}

# --- 主介面 ---
st.title("🏹 全自動 CB 溢價率掃描儀")
st.write("同時監控 **CB 市價** 與 **現股價格**，尋找「低溢價」的獲利機會。")

df_base = get_cb_base_info()

if not df_base.empty:
    if st.button("🚀 開始計算全市場溢價率"):
        with st.spinner('正在同步 600+ 筆報價資料...'):
            cb_list = df_base['債券代碼'].tolist()
            stock_list = df_base['stock_id'].unique().tolist()
            
            all_prices = get_combined_prices(cb_list, stock_list)
            
            # 建立計算清單
            results = []
            for _, row in df_base.iterrows():
                cb_p = all_prices.get(f"{row['債券代碼']}.TWO")
                # 現股可能在上市(.TW)或上櫃(.TWO)
                stk_p = all_prices.get(f"{row['stock_id']}.TW") or all_prices.get(f"{row['stock_id']}.TWO")
                
                if cb_p and stk_p and row['轉換價格'] > 0:
                    # 轉換價值 = (現股價格 / 轉換價格) * 100
                    conv_value = (stk_p / row['轉換價格']) * 100
                    # 溢價率 = (CB價格 / 轉換價值 - 1) * 100
                    premium = (cb_p / conv_value - 1) * 100
                    
                    results.append({
                        "代碼": row['債券代碼'],
                        "簡稱": row['債券簡稱'],
                        "CB市價": cb_p,
                        "現股價": stk_p,
                        "轉換價": row['轉換價格'],
                        "轉換價值": round(conv_value, 2),
                        "溢價率(%)": round(premium, 2)
                    })
            
            df_res = pd.DataFrame(results)

            # --- 視覺化圖表 ---
            st.subheader("📊 CB 溢價分佈與買點分析")
            
            # 建立選股象限圖
            fig = px.scatter(
                df_res, x="CB市價", y="溢價率(%)",
                color="溢價率(%)", 
                color_continuous_scale="RdYlGn_r", # 綠色代表低溢價
                hover_name="簡稱",
                hover_data=["現股價", "轉換價值"],
                text="簡稱",
                template="plotly_dark",
                height=600
            )
            # 畫出 15% 溢價參考線
            fig.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="高溢價風險區")
            fig.add_hline(y=0, line_dash="solid", line_color="white", annotation_text="平價線")
            st.plotly_chart(fig, use_container_width=True)

            # --- 篩選與清單 ---
            st.subheader("💎 優質標的清單 (低溢價優先)")
            st.write("建議關注：**CB市價 < 115** 且 **溢價率 < 5%** 的標的。")
            
            # 增加自動排序與美化顯示
            st.dataframe(
                df_res.sort_values("溢價率(%)"),
                column_config={
                    "溢價率(%)": st.column_config.ProgressColumn(min_value=-10, max_value=50, format="%.2f%%"),
                    "CB市價": st.column_config.NumberColumn(format="$%.1f"),
                    "現股價": st.column_config.NumberColumn(format="$%.1f")
                },
                use_container_width=True
            )
else:
    st.error("清單讀取失敗")
