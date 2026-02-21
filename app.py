import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# 頁面設定
st.set_page_config(page_title="CB量能監控儀表板", layout="wide")
st.title("📈 台灣可轉債 (CB) 大量成交績效追蹤")

# 1. 初始化資料庫
dl = DataLoader()

# 2. 側邊欄設定
st.sidebar.header("⚙️ 策略參數")
cb_id = st.sidebar.text_input("輸入 CB 代號 (如: 15821)", value="15821")
vol_multiplier = st.sidebar.slider("成交量翻倍數 (爆量定義)", 1.5, 5.0, 2.5)
hold_days = st.sidebar.slider("買入後持有天數", 10, 120, 60)

# 3. 核心運算邏輯
@st.cache_data(ttl=3600)
def fetch_and_calc(bond_id, vol_m, hold):
    start_dt = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    
    # 改用通用接口以提高相容性
    try:
        df = dl.taiwan_stock_daily(stock_id=bond_id, start_date=start_dt)
    except Exception as e:
        st.error(f"資料抓取失敗: {e}")
        return None

    if df is None or df.empty:
        return None
    
    # 確保欄位名稱正確 (FinMind 有時回傳 Trading_Volume 有時回傳 Volume)
    df.columns = [c.lower() for c in df.columns]
    vol_col = 'trading_volume' if 'trading_volume' in df.columns else 'volume'
    
    # 計算爆量邏輯
    df['ma20_v'] = df[vol_col].rolling(20).mean()
    df['signal'] = df[vol_col] > (df['ma20_v'] * vol_m)
    
    # 計算報酬
    df['future_p'] = df['close'].shift(-hold)
    df['return'] = (df['future_p'] - df['close']) / df['close']
    return df

# 4. 執行與顯示
df = fetch_and_calc(cb_id, vol_multiplier, hold_days)

if df is not None:
    signals = df[df['signal'] == True].dropna(subset=['return'])
    
    # 儀表板指標
    c1, c2, c3 = st.columns(3)
    c1.metric("歷史爆量訊號次數", f"{len(signals)} 次")
    c2.metric(f"平均 {hold_days}日報酬率", f"{signals['return'].mean():.2%}")
    c3.metric("勝率", f"{(signals['return'] > 0).mean():.1%}" if len(signals)>0 else "0%")

    # 繪圖
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['close'], name='CB 價格'))
    fig.add_trace(go.Scatter(x=signals['date'], y=signals['close'], 
                             mode='markers', name='爆量點', 
                             marker=dict(color='red', size=10, symbol='triangle-up')))
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📋 訊號詳細明細")
    st.dataframe(signals[['date', 'close', 'future_p', 'return']].sort_values('date', ascending=False))
else:
    st.warning("⚠️ 查無資料，請確認 CB 代號是否輸入正確。")
