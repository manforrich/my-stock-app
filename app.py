import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser

# 1. 設定網頁標題
st.set_page_config(page_title="股票分析儀表板", layout="wide")
st.title("📈 股票分析儀表板 (含缺口偵測)")

# 2. 側邊欄：設定參數
st.sidebar.header("設定參數")
stock_id = st.sidebar.text_input("輸入股票代碼", value="2330.TW")
period = st.sidebar.selectbox("選擇時間範圍", ["3mo", "6mo", "1y", "2y", "5y"])

# --- 技術指標設定 ---
st.sidebar.subheader("技術指標")
ma_days = st.sidebar.multiselect("顯示均線 (MA)", [5, 10, 20, 60, 120, 240], default=[5, 20])
show_gaps = st.sidebar.checkbox("顯示跳空缺口 (Gaps)", value=True) # <--- 新增這個開關

# 3. 抓取股價數據
def get_stock_data(ticker, period):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        return hist
    except Exception:
        return None

# 4. 抓取新聞函數
def get_google_news(query):
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    return feed.entries

# 5. 主程式邏輯
if stock_id:
    df = get_stock_data(stock_id, period)
    
    if df is not None and not df.empty:
        # --- A. 顯示價格與成交量 ---
        col1, col2, col3, col4 = st.columns(4)
        
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        change = current_price - prev_price
        pct_change = (change / prev_price) * 100
        current_volume = df['Volume'].iloc[-1]

        col1.metric("當前股價", f"{current_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
        col2.metric("最高價", f"{df['High'].max():.2f}")
        col3.metric("最低價", f"{df['Low'].min():.2f}")
        col4.metric("最新成交量", f"{current_volume:,}")

        # --- B. 畫圖 (K線 + 均線 + 成交量 + 缺口) ---
        st.subheader(f"📊 {stock_id} 走勢圖")
        
        fig = make_subplots(rows=2, cols=1, 
                            shared_xaxes=True, 
                            vertical_spacing=0.05, 
                            row_heights=[0.7, 0.3])

        # 1. K 線圖
        fig.add_trace(go.Candlestick(x=df.index,
                                     open=df['Open'], high=df['High'],
                                     low=df['Low'], close=df['Close'],
                                     name="K線"), 
                      row=1, col=1)

        # 2. 均線
        colors = ['orange', 'blue', 'purple', 'black', 'green', 'red']
        for i, days in enumerate(ma_days):
            ma_name = f"MA{days}"
            df[ma_name] = df['Close'].rolling(window=days).mean()
            fig.add_trace(go.Scatter(x=df.index, y=df[ma_name], mode='lines', name=ma_name,
                                     line=dict(width=1.5, color=colors[i % len(colors)])),
                          row=1, col=1)

        # 3. 成交量
        vol_colors = ['green' if row['Close'] >= row['Open'] else 'red' for index, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_
