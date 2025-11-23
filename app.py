import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import feedparser  # <--- 新增這個套件是用來抓 Google 新聞的

# 1. 設定網頁標題
st.set_page_config(page_title="股票分析儀表板", layout="wide")
st.title("📈 股票分析儀表板 (Google News 版)")

# 2. 側邊欄
st.sidebar.header("設定參數")
# 預設加入台積電，方便測試
stock_id = st.sidebar.text_input("輸入股票代碼", value="2330.TW")
period = st.sidebar.selectbox("選擇時間範圍", ["1Month", "3Month", "6Month", "1Year", "5Year"])

# 3. 抓取股價數據 (用 yfinance)
def get_stock_data(ticker, period):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        return hist
    except Exception:
        return None

# 4. 抓取新聞函數 (改用 Google News RSS)
def get_google_news(query):
    # Google News RSS 網址格式
    # 我們把股票代碼放進去搜尋，如果是台股，建議搜尋代碼即可
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    # 解析 RSS
    feed = feedparser.parse(rss_url)
    return feed.entries

# 5. 主程式邏輯
if stock_id:
    # --- 抓股價 ---
    df = get_stock_data(stock_id, period)
    
    if df is not None and not df.empty:
        # A. 顯示價格資訊
        col1, col2, col3 = st.columns(3)
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        change = current_price - prev_price
        pct_change = (change / prev_price) * 100

        col1.metric("當前股價", f"{current_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
        col2.metric("最高價", f"{df['High'].max():.2f}")
        col3.metric("最低價", f"{df['Low'].min():.2f}")

        # B. 畫 K 線圖
        st.subheader(f"📊 {stock_id} 股價走勢")
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                        open=df['Open'], high=df['High'],
                        low=df['Low'], close=df['Close'])])
        fig.update_layout(xaxis_rangeslider_visible=False, height=500)
        st.plotly_chart(fig, use_container_width=True)

        # C. Google 新聞區塊
        st.divider()
        st.subheader(f"📰 {stock_id} 最新新聞 (來源: Google News)")

        # 呼叫上面寫好的新聞函數
        news_items = get_google_news(stock_id)

        if news_items:
            # 只顯示前 10 則新聞
            for item in news_items[:10]:
                with st.expander(item.title):
                    st.write(f"發布時間: {item.published}")
                    st.markdown(f"[👉 點擊閱讀全文]({item.link})")
        else:
            st.info("目前找不到相關新聞")

        # D. 歷史數據表格
        with st.expander("查看歷史股價數據"):
            st.dataframe(df.sort_index(ascending=False))

    else:
        st.error("找不到股票數據，請確認代碼是否正確 (台股請加 .TW)")
