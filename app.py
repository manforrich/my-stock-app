import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. 網頁設定 ---
st.set_page_config(page_title="台股分析儀表板", layout="wide")
st.title("📈 台股個股分析儀表板")

# --- 2. 側邊欄：輸入股票代號 ---
st.sidebar.header("查詢設定")
stock_id = st.sidebar.text_input("輸入台股代號 (例如 2330)", "2330")
days = st.sidebar.slider("觀察天數", 30, 365, 180)

# 處理台股代號 (Yahoo Finance 需要加上 .TW 或 .TWO)
if not stock_id.endswith(".TW") and not stock_id.endswith(".TWO"):
    ticker = stock_id + ".TW"
else:
    ticker = stock_id

# --- 3. 抓取數據 ---
@st.cache_data
def get_data(ticker, days):
    start_date = datetime.now() - timedelta(days=days)
    try:
        df = yf.download(ticker, start=start_date)
        return df
    except Exception as e:
        return None

data = get_data(ticker, days)

# --- 4. 顯示內容 ---
if data is not None and not data.empty:
    # 取得最新股價資訊
    stock_info = yf.Ticker(ticker).info
    current_price = data['Close'].iloc[-1]
    prev_price = data['Close'].iloc[-2]
    change = current_price - prev_price
    change_pct = (change / prev_price) * 100
    
    # 顯示頂部數據卡片
    col1, col2, col3 = st.columns(3)
    col1.metric("股票名稱", stock_info.get('longName', stock_id))
    col2.metric("最新收盤價", f"{float(current_price):.2f}", f"{float(change):.2f} ({float(change_pct):.2f}%)")
    col3.metric("成交量", f"{int(data['Volume'].iloc[-1]):,}")

    # --- 繪製 K 線圖 (Candlestick) ---
    st.subheader(f"{stock_id} 股價走勢圖")
    fig = go.Figure(data=[go.Candlestick(x=data.index,
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'],
                    name='K線')])
    
    fig.update_layout(xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)

    # --- 顯示歷史數據表格 ---
    with st.expander("查看詳細歷史數據"):
        st.dataframe(data.sort_index(ascending=False))

else:
    st.error("找不到該股票數據，請確認代號是否正確 (例如 2330)。")
