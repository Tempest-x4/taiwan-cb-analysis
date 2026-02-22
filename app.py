import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title="自製 CMoney CB 選股雷達", layout="wide")

# 1. 直接定義流通 CB 資料庫 (避免 API 報錯)
# 這裡放入部分核心流通標的，你可以根據需要持續增加
def get_static_cb_data():
    data = [
        {"id": "15821", "name": "耀勝一", "conv_p": 120.5, "stock": "1582"},
        {"id": "65152", "name": "穎崴二", "conv_p": 700.0, "stock": "6515"},
        {"id": "30175", "name": "鴻海五", "conv_p": 120.0, "stock": "2317"},
        {"id": "35483", "name": "兆利三", "conv_p": 240.0, "stock": "3548"},
        {"id": "24541", "name": "聯發科一", "conv_p": 1000.0, "stock": "2454"},
        {"id": "32311", "name": "緯創一", "conv_p": 110.0, "stock": "3231"},
        {"id": "23301", "name": "台積電一", "conv_p": 600.0, "stock": "2330"},
        # 這裡可以手動貼入更多 CB 資料...
    ]
    return pd.DataFrame(data)

st.title("🏹 自製 CB 價值掃描儀 (CMoney 風格)")
st.markdown("本系統模擬 **CMoney 溢價分析邏輯**，專注於找出「被低估」的可轉債。")

cb_df = get_static_cb_data()

# --- 側邊欄策略篩選 ---
st.sidebar.header("🎯 策略篩選器")
premium_limit = st.sidebar.slider("溢價率上限 (%)", -10, 30, 10)
price_limit = st.sidebar.slider("CB 價格上限", 100, 250, 120)

if st.button("📈 執行全市場掃描與視覺化"):
    with st.spinner("同步 Yahoo Finance 即時行情..."):
        # 建立查詢清單
        tickers = [f"{row['id']}.TWO" for _, row in cb_df.iterrows()]
        tickers += [f"{row['stock']}.TW" for _, row in cb_df.iterrows()]
        tickers += [f"{row['stock']}.TWO" for _, row in cb_df.iterrows()]
        
        # 一次性抓取
        prices = yf.download(tickers, period="1d", interval="5m", group_by='ticker')
        
        final_list = []
        for _, row in cb_df.iterrows():
            try:
                cb_p = prices[f"{row['id']}.TWO"]['Close'].iloc[-1]
                # 判斷現股在上市或上櫃
                stk_p = None
                if f"{row['stock']}.TW" in prices:
                    stk_p = prices[f"{row['stock']}.TW"]['Close'].dropna().iloc[-1]
                if stk_p is None and f"{row['stock']}.TWO" in prices:
                    stk_p = prices[f"{row['stock']}.TWO"]['Close'].dropna().iloc[-1]
                
                if cb_p and stk_p:
                    conv_v = (stk_p / row['conv_p']) * 100
                    premium = (cb_p / conv_v - 1) * 100
                    final_list.append({
                        "代碼": row['id'], "名稱": row['name'], 
                        "CB市價": round(cb_p, 2), "現股價": round(stk_p, 2),
                        "溢價率(%)": round(premium, 2), "轉換價值": round(conv_v, 2)
                    })
            except:
                continue
        
        if final_list:
            res_df = pd.DataFrame(final_list)
            
            # 策略過濾
            strategy_df = res_df[(res_df['溢價率(%)'] <= premium_limit) & (res_df['CB市價'] <= price_limit)]
            
            # 1. 散點圖視覺化
            st.subheader("📊 價值分佈圖 (顏色愈綠代表愈便宜)")
            fig = px.scatter(
                res_df, x="CB市價", y="溢價率(%)", color="溢價率(%)",
                text="名稱", color_continuous_scale="RdYlGn_r",
                template="plotly_dark", height=500
            )
            fig.add_hline(y=0, line_dash="dash", line_color="white")
            st.plotly_chart(fig, use_container_width=True)
            
            # 2. 策略推薦
            st.subheader(f"💎 符合策略標的 (共 {len(strategy_df)} 檔)")
            st.dataframe(strategy_df.sort_values("溢價率(%)"), use_container_width=True)
            
        else:
            st.error("目前無法獲取價格，請確認是否為開盤時間。")
