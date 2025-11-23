import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots # <--- 新增這個用來畫子圖
import feedparser

# 1. 設定網頁標題
st.set_page_config(page_title="股票分析儀表板", layout="wide")
st.title("📈 股票分析儀表板 (含成交量)")

# 2. 側邊欄
st.sidebar.header("設定參數")
stock_id = st.sidebar.text_input("輸入股票代碼", value="2330.TW")
period = st.sidebar.selectbox("選擇時間範圍", ["1mo", "3mo", "6mo", "1y", "5y", "max"])
st.sidebar.subheader("技術指標")
ma_days = st.sidebar.multiselect(
    "選擇移動平均線 (MA)", 
    [5, 10, 20, 60, 120, 240], 
    default=[5, 20] # 預設顯示 5日(週線) 和 20日(月線)
)
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
        # --- A. 顯示價格與成交量資訊 (改成 4 欄) ---
        col1, col2, col3, col4 = st.columns(4)
        
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        change = current_price - prev_price
        pct_change = (change / prev_price) * 100
        current_volume = df['Volume'].iloc[-1] # 抓取最新成交量

        col1.metric("當前股價", f"{current_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
        col2.metric("最高價", f"{df['High'].max():.2f}")
        col3.metric("最低價", f"{df['Low'].min():.2f}")
        # 使用 f"{current_volume:,}" 讓數字每三位加一個逗號，比較好讀
        col4.metric("最新成交量", f"{current_volume:,}")

        # --- B. 畫圖 (K線圖 + 成交量) ---
        st.subheader(f"📊 {stock_id} 價量走勢圖")
        
        # 建立子圖表 (2 行 1 列)，設定高度比例 (K線佔 70%, 成交量佔 20%)
        fig = make_subplots(rows=2, cols=1, 
                            shared_xaxes=True, 
                            vertical_spacing=0.05, 
                            row_heights=[0.7, 0.3])

        # 1. 繪製 K 線圖 (放在第 1 列)
        fig.add_trace(go.Candlestick(x=df.index,
                                     open=df['Open'], high=df['High'],
                                     low=df['Low'], close=df['Close'],
                                     name="股價"), 
                      row=1, col=1)

        # 2. 繪製成交量圖 (放在第 2 列)
        # 設定顏色：收盤 >= 開盤 (漲) 用綠色，跌用紅色 (這是國際通用色，若要台股紅漲綠跌可自行互換顏色字串)
        colors = ['green' if row['Close'] >= row['Open'] else 'red' for index, row in df.iterrows()]
        
        fig.add_trace(go.Bar(x=df.index, 
                             y=df['Volume'], 
                             marker_color=colors,
                             name="成交量"), 
                      row=2, col=1)

        # 設定圖表版面
        fig.update_layout(
            xaxis_rangeslider_visible=False, # 隱藏原本自帶的下方拉桿
            height=600, # 設定圖表總高度
            showlegend=False # 隱藏圖例說明以保持乾淨
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # --- C. Google 新聞區塊 ---
        st.divider()
        st.subheader(f"📰 {stock_id} 最新新聞 (來源: Google News)")

        news_items = get_google_news(stock_id)
        if news_items:
            for item in news_items[:6]: # 顯示前 6 則
                with st.expander(item.title):
                    st.write(f"發布時間: {item.published}")
                    st.markdown(f"[👉 點擊閱讀全文]({item.link})")
        else:
            st.info("目前找不到相關新聞")

        # --- D. 歷史數據表格 ---
        with st.expander("查看詳細歷史數據"):
            st.dataframe(df.sort_index(ascending=False))

    else:
        st.error("找不到股票數據，請確認代碼是否正確 (台股請加 .TW)")
