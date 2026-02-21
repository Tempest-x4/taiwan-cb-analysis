import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# 設定網頁標題與風格
st.set_page_config(page_title="CB量能監控儀表板", layout="wide")
st.title("📈 台灣可轉債 (CB) 大量成交績效追蹤")

# 1. 初始化資料庫
dl = DataLoader()

# 2. 側邊欄參數設定
st.sidebar.header("⚙️ 策略參數")
cb_id = st.sidebar.text_input("輸入 CB 代號", value="15821")
vol_multiplier = st.sidebar.slider("成交量翻倍數 (爆量定義)", 1.5, 5.0, 2.5)
hold_days = st.sidebar.slider("買入後持有天數", 10, 120, 60)
start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

# 3. 獲取數據與運算
@st.cache_data(ttl=3600)
def fetch_and_calc(bond_id):
    df = dl.taiwan_convertible_bond_daily(bond_id=bond_id, start_date=start_date)
    if df.empty: return None
    
    # 計算爆量邏輯
    df['MA20_V'] = df['Volume'].rolling(20).mean()
    df['Signal'] = df['Volume'] > (df['MA20_V'] * vol_multiplier)
    
    # 計算 60 天後報酬
    df['Future_P'] = df['close'].shift(-hold_days)
    df['Return'] = (df['Future_P'] - df['close']) / df['close']
    return df

# 4. 顯示結果
df = fetch_and_calc(cb_id)

if df is not None:
    # 績效摘要
    signals = df[df['Signal'] == True].dropna(subset=['Return'])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("歷史爆量訊號次數", f"{len(signals)} 次")
    col2.metric("平均報酬率 (持有{hold_days}天)", f"{signals['Return'].mean():.2%}")
    col3.metric("勝率", f"{(signals['Return'] > 0).mean():.1%}")

    # --- 可視化圖表 ---
    st.subheader(f"📊 {cb_id} 價格走勢與爆量訊號")
    fig = go.Figure()
    # 價格線
    fig.add_trace(go.Scatter(x=df['date'], y=df['close'], name='CB 價格', line=dict(color='#1f77b4')))
    # 爆量點
    fig.add_trace(go.Scatter(x=signals['date'], y=signals['close'], 
                             mode='markers', name='爆量買入點', 
                             marker=dict(color='red', size=10, symbol='triangle-up')))
    
    fig.update_layout(height=500, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # 顯示詳細資料
    st.subheader("📋 訊號詳細明細")
    st.dataframe(signals[['date', 'close', 'Future_P', 'Return']].sort_values('date', ascending=False))
else:
    st.error(f"⚠️ 找不到代號 {cb_id} 的資料，請確認代號是否正確（例如：15821）。")
