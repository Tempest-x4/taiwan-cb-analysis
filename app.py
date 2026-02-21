import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# 頁面設定
st.set_page_config(page_title="台灣流通 CB 觀測站", layout="wide")

# 1. 從櫃買中心 (TPEx) 抓取資料並過濾過期標的
@st.cache_data(ttl=86400)
def get_active_cb_list():
    url = "https://www.tpex.org.tw/openapi/v1/bond_issue_info_cb"
    try:
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data)
        
        # 取得今天日期
        today = datetime.now().strftime("%Y/%m/%d")
        
        # 轉換日期格式以便比較 (處理官方常見的 YYYY/MM/DD)
        # 過濾邏輯：到期日期必須大於等於今天
        df_active = df[df['到期日期'] >= today].copy()
        
        # 整理名稱並按代號排序
        df_active['display_name'] = df_active['債券代碼'] + " " + df_active['債券簡稱']
        df_active = df_active.sort_values('債券代碼')
        
        return df_active
    except Exception as e:
        st.error(f"無法連線至官方資料庫: {e}")
        return pd.DataFrame()

# 2. 抓取價格資料
@st.cache_data(ttl=3600)
def get_cb_price(cb_id):
    date_str = datetime.now().strftime("%Y%m01")
    url = f"https://www.tpex.org.tw/web/bond/tradeinfo/cb/cb_trading_details_result.php?l=zh-tw&d={date_str}&stkno={cb_id}"
    try:
        res = requests.get(url)
        raw = res.json()
        if 'aaData' in raw and raw['aaData']:
            df = pd.DataFrame(raw['aaData'], columns=[
                "日期", "成交千元", "成交張數", "最高價", "最低價", "收盤價", "漲跌", "最後買價", "最後賣價"
            ])
            df['收盤價'] = pd.to_numeric(df['收盤價'], errors='coerce')
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 主程式 ---
df_active = get_active_cb_list()

if not df_active.empty:
    # 側邊欄：僅顯示流通中的選單
    st.sidebar.header("🎯 流通標的篩選")
    cb_list = df_active[['債券代碼', 'display_name']].values.tolist()
    
    selected_cb = st.sidebar.selectbox(
        f"目前流通中 CB：{len(cb_list)} 檔",
        options=cb_list,
        format_func=lambda x: x[1],
        help="輸入代號或名稱可直接搜尋"
    )
    target_id = selected_cb[0]

    # 主畫面顯示基本資料
    st.title(f"📈 {selected_cb[1]}")
    
    info = df_active[df_active['債券代碼'] == target_id].iloc[0]
    
    # 資訊面板
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("轉換價格", f"${info['轉換價格']}")
    c2.metric("發行總額", f"{int(info['發行總額']):,} (千)")
    c3.metric("到期日期", info['到期日期'])
    
    # 計算剩餘天數
    due_dt = datetime.strptime(info['到期日期'], "%Y/%m/%d")
    days_left = (due_dt - datetime.now()).days
    c4.metric("剩餘天數", f"{max(0, days_left)} 天")

    # 價格圖表
    st.markdown("---")
    df_p = get_cb_price(target_id)
    if not df_p.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_p['日期'], y=df_p['收盤價'], name='收盤價', line=dict(color='#00ffcc', width=3)))
        fig.update_layout(title="本月價格走勢", template="plotly_dark", height=450)
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("查看成交明細"):
            st.dataframe(df_p, use_container_width=True)
    else:
        st.info("此標的本月尚無成交紀錄。")
else:
    st.warning("正在讀取櫃買中心流通標的清單，請稍候...")
