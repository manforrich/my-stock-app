import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import feedparser
from datetime import datetime, timedelta
import urllib.parse

# --- 1. 網頁設定 ---
st.set_page_config(page_title="台股分析儀表板 Pro", layout="wide")
st.title("📈 台股個股分析儀表板 Pro")

# --- 2. 預設的股票清單 ---
stock_categories = {
    "🔍 自行輸入代號": {},
    "🏆 熱門權值股": {
        "2330 台積電": "2330",
        "2317 鴻海": "2317",
        "2454 聯發科": "2454",
        "2308 台達電": "2308",
        "2382 廣達": "2382"
    },
    "🤖 AI 概念股": {
        "3231 緯創": "3231",
        "2376 技嘉": "2376",
        "2356 英業達": "2356",
        "6669 緯穎": "6669",
        "3017 奇鋐": "3017"
    },
    "🚢 航運股": {
        "2603 長榮": "2603",
        "2609 陽明": "2609",
        "2615 萬海": "2615",
        "2618 長榮航": "2618",
        "2610 華航": "2610"
    },
    "💰 金融股": {
        "2881 富邦金": "2881",
        "2882 國泰金": "2882",
        "2891 中信金": "2891",
        "2886 兆豐金": "2886",
        "2884 玉山金": "2884"
    },
    "📊 熱門 ETF": {
        "0050 元大台灣50": "0050",
        "0056 元大高股息": "0056",
        "00878 國泰永續高股息": "00878",
        "00929 復華台灣科技優息": "00929",
        "00940 元大台灣價值高息": "00940"
    }
}

# --- 3. 側邊欄設定 ---
st.sidebar.header("選股設定")
selected_category = st.sidebar.selectbox("1️⃣ 選擇產業類別", list(stock_categories.keys()))

stock_name_for_news = ""

if selected_category == "🔍 自行輸入代號":
    stock_input = st.sidebar.text_input("輸入台股代號 (如 2330)", "2330")
    target_stock = stock_input
    stock_name_for_news = stock_input
else:
    category_stocks = stock_categories[selected_category]
    selected_stock_name = st.sidebar.selectbox("2️⃣ 選擇個股", list(category_stocks.keys()))
    target_stock = category_stocks[selected_stock_name]
    
    if " " in selected_stock_name:
        stock_name_for_news = selected_stock_name.split(" ")[1]
    else:
        stock_name_for_news = target_stock

days = st.sidebar.slider("📅 觀察天數", 30, 730, 180)

# --- 4. 數據處理函數 ---
if not target_stock.endswith(".TW") and not target_stock.endswith(".TWO"):
    ticker = target_stock + ".TW"
else:
    ticker = target_stock

@st.cache_data
def get_data(ticker, days):
    start_date = datetime.now() - timedelta(days=days)
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date)
        
        if df.empty and ticker.endswith(".TW"):
            ticker_two = ticker.replace(".TW", ".TWO")
            stock_two = yf.Ticker(ticker_two)
            df = stock_two.history(start=start_date)
        
        df.columns = [c.capitalize() for c in df.columns]
        df.index = pd.to_datetime(df.index)
        
        if df.empty:
            return None
        return df
    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def get_google_news(query):
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    try:
        feed = feedparser.parse(rss_url)
        return feed.entries[:6]
    except Exception as e:
        return []

# --- 5. 畫面呈現 ---
with st.spinner('正在分析股價與搜尋新聞...'):
    data = get_data(ticker, days)

if data is not None and not data.empty:
    try:
        latest_data = data.iloc[-1]
        prev_data = data.iloc[-2]
        current_price = latest_data['Close']
        change = current_price - prev_data['Close']
        change_pct = (change / prev_data['Close']) * 100
        
        col1, col2, col3 = st.columns(3)
        col1.metric("股票代號", target_stock)
        col2.metric("收盤價", f"{current_price:.2f}", f"{change:.2f} ({change_pct:.2f}%)")
        col3.metric("成交量", f"{int(latest_data['Volume']/1000):,} 張")

        # --- 繪圖區 ---
        st.subheader(f"📈 {target_stock} 股價走勢")
        
        data['MA5'] = data['Close'].rolling(window=5).mean()
        data['MA20'] = data['Close'].rolling(window=20).mean()

        # 建立雙層圖表 (上層K線，下層成交量)
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            subplot_titles=(f'{target_stock} 股價', '成交量'),
            row_width=[0.2, 0.7]
        )

        # K線
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name='K線'
        ), row=1, col=1)

        # 均線
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA5'], mode='lines', name='5日均線', line=dict(color='orange', width=1)
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA20'], mode='lines', name='20日均線', line=dict(color='purple', width=1)
        ), row=1, col=1)

        # 成交量
        volume_colors = ['red' if row['Close'] >= row['Open'] else 'green' for i, row in data.iterrows()]
        fig.add_trace(go.Bar(
            x=data.index, y=data['Volume'], name='成交量', marker_color=volume_colors
        ), row=2, col=1)

        fig.update_layout(
            xaxis_rangeslider_visible=False, 
            height=600, 
            template="plotly_dark", 
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📊 查看詳細歷史數據"):
            st.dataframe(data.sort_index(ascending=False).style.format("{:.2f}"))

        # --- 新聞區 ---
        st.divider()
        st.subheader(f"📰 {stock_name_for_news} 最新相關新聞")
        news_list = get_google_news(stock_name_for_news)
        
        if news_list:
            news_cols = st.columns(2)
            for i, news in enumerate(news_list):
                with news_cols[i % 2]:
                    st.info(f"**[{news.title}]({news.link})**\n\n🕒 {news.published[5:16]}")
        else:
            st.write("目前找不到相關新聞。")
            
    except Exception as e:
        st.error(f"畫面處理錯誤: {e}")
else:
    st.warning(f"找不到代號 {target_stock} 的資料。")
