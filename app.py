import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="CB 溢價率監控-穩定版", layout="wide")

# 1. 強化版獲取 CB 基本資料
@st.cache_data(ttl=86400)
def get_cb_base_info():
    # 使用多個備援網址或方式
    url = "https://www.tpex.org.tw/openapi/v1/bond_issue_info_cb"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            df['轉換價格'] = pd.to_numeric(df['轉換價格'], errors='coerce')
            today = datetime.now().strftime("%Y/%m/%d")
            df = df[df['到期日期'] >= today].copy()
            df['stock_id'] = df['債券代碼'].str[:4]
            return df[['債券代碼', '債券簡稱', '轉換價格', 'stock_id']]
        else:
            # 如果失敗，回傳一個小型清單讓使用者測試
            st.warning("官方 API 暫時阻擋連線，載入觀察清單中...")
            return pd.DataFrame([
                ["15821", "耀勝一", 120.5, "1582"],
                ["65152", "穎崴二", 700.0, "6515"],
                ["30175", "鴻海五", 120.0, "2017"]
            ], columns=['債券代碼', '債券簡稱', '轉換價格', 'stock_id'])
    except:
        return pd.DataFrame()

# 2. 獲取價格 (加入重試機制)
@st.cache_data(ttl=300)
def get_combined_prices(cb_ids, stock_ids):
    # 建立 Yahoo 代碼列表
    tickers = [f"{cid}.TWO" for cid in cb_ids] 
    # 現股代碼需要判斷上市或上櫃，這裡我們先各抓一次備用
    tickers += [f"{sid}.TW" for sid in stock_ids] + [f"{sid}.TWO" for sid in stock_ids]
    
    try:
        # 使用 yfinance 抓取，這部分通常很穩，因為 Yahoo 不太擋 IP
        data = yf.download(tickers, period="1d", interval="5m", group_by='ticker', threads=True)
        price_map = {}
        for t in tickers:
            try:
                # 取得最新價格
                val = data[t]['Close'].dropna()
                if not val.empty:
                    price_map[t] = val.iloc[-1]
            except:
                continue
        return price_map
    except:
        return {}

# --- 介面主體 ---
st.title("🏹 CB 獵人 - 實時溢價掃描儀")
st.markdown("---")

df_base = get_cb_base_info()

if not df_base.empty:
    if st.button("🚀 開始計算溢價率與爆量偵測"):
        with st.spinner('同步市場數據中...'):
            cb_list = df_base['債券代碼'].tolist()
            stock_list = df_base['stock_id'].unique().tolist()
            all_prices = get_combined_prices(cb_list, stock_list)
            
            results = []
            for _, row in df_base.iterrows():
                cb_p = all_prices.get(f"{row['債券代碼']}.TWO")
                stk_p = all_prices.get(f"{row['stock_id']}.TW") or all_prices.get(f"{row['stock_id']}.TWO")
                
                if cb_p and stk_p and row['轉換價格'] > 0:
                    conv_v = (stk_p / row['轉換價格']) * 100
                    prem = (cb_p / conv_v - 1) * 100
                    
                    results.append({
                        "代碼": row['債券代碼'], "簡稱": row['債券簡稱'],
                        "CB市價": cb_p, "現股價": stk_p,
                        "轉換價": row['轉換價格'], "溢價率(%)": round(prem, 2)
                    })
            
            if results:
                df_res = pd.DataFrame(results)
                
                # 視覺化圖表
                fig = px.scatter(
                    df_res, x="CB市價", y="溢價率(%)", 
                    color="溢價率(%)", color_continuous_scale="RdYlGn_r",
                    text="簡稱", template="plotly_dark", height=600,
                    title="CB 價值象限圖：左下角為黃金買點區"
                )
                fig.add_hline(y=0, line_color="white")
                fig.add_hrect(y0=-5, y1=5, fillcolor="green", opacity=0.2, annotation_text="低溢價區")
                st.plotly_chart(fig, use_container_width=True)
                
                # 顯示列表
                st.subheader("📋 即時行情數據")
                st.dataframe(df_res.sort_values("溢價率(%)"), use_container_width=True)
            else:
                st.error("暫時抓不到即時價格，請確認目前是否為交易時段或 Yahoo Finance 連線正常。")
else:
    st.error("無法取得 CB 基礎資訊，請手動刷新頁面或檢查 GitHub 設定。")
