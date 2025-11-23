import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# 1. 設定網頁標題與版面
st.set_page_config(page_title="簡易股票分析", layout="wide")
st.title("📈 股票分析儀表板")

# 2. 側邊欄：輸入股票代碼
st.sidebar.header("設定參數")
stock_id = st.sidebar.text_input("輸入股票代碼 (例如: NVDA, AAPL, 2330.TW)", value="2330.TW")
period = st.sidebar.selectbox("選擇時間範圍", ["1mo", "3mo", "6mo", "1y", "5y", "max"])

# 3. 抓取數據函數 (包含歷史股價與新聞)
def get_stock_data(ticker, period):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        return stock, hist
    except Exception as e:
        return None, None

# 4. 執行分析
if stock_id:
    stock_info, df = get_stock_data(stock_id, period)
    
    if df is not None and not df.empty:
        # --- 區塊 A: 顯示即時資訊 ---
        col1, col2, col3 = st.columns(3)
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        change = current_price - prev_price
        pct_change = (change / prev_price) * 100

        col1.metric("當前股價", f"{current_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
        col2.metric("最高價 (期間)", f"{df['High'].max():.2f}")
        col3.metric("最低價 (期間)", f"{df['Low'].min():.2f}")

        # --- 區塊 B: 繪製互動式 K 線圖 ---
        st.subheader(f"📊 {stock_id} 股價走勢")
        
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                        open=df['Open'],
                        high=df['High'],
                        low=df['Low'],
                        close=df['Close'])])
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=500)
        st.plotly_chart(fig, use_container_width=True)

        # --- 區塊 C: 新聞專區 (新增的功能) ---
        st.divider() # 畫一條分隔線
        st.subheader(f"📰 {stock_id} 最新新聞")

        try:
            news_list = stock_info.news
            if news_list:
                for item in news_list:
                    # 使用 Expander 收折新聞，讓版面比較乾淨
                    with st.expander(f"{item['title']} ({item['publisher']})"):
                        # 處理發布時間
                        if 'providerPublishTime' in item:
                            date_str = datetime.fromtimestamp(item['providerPublishTime']).strftime('%Y-%m-%d %H:%M')
                            st.caption(f"發布時間: {date_str}")
                        
                        # 新聞連結
                        st.markdown(f"[點擊閱讀全文]({item['link']})")
                        
                        # (選做) 如果有圖片連結也可以顯示，但為了版面簡潔先省略
            else:
                st.info("目前暫無該個股的特定新聞資料 (Yahoo Finance 限制)")
        except Exception as e:
            st.error(f"讀取新聞時發生錯誤: {e}")

        # --- 區塊 D: 原始數據 ---
        with st.expander("查看歷史股價表格"):
            st.dataframe(df.sort_index(ascending=False))
            
    else:
        st.error("找不到股票數據，請確認代碼是否正確 (台股請加 .TW)")
