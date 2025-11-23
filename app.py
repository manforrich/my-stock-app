import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

# 1. 設定網頁標題與版面
st.set_page_config(page_title="簡易股票分析", layout="wide")
st.title("📈 股票分析儀表板")

# 2. 側邊欄：輸入股票代碼
st.sidebar.header("設定參數")
stock_id = st.sidebar.text_input("輸入股票代碼 (例如: AAPL 或 2330.TW)", value="2330.TW")
period = st.sidebar.selectbox("選擇時間範圍", ["1mo", "3mo", "6mo", "1y", "5y", "max"])

# 3. 抓取數據函數
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
    
    if not df.empty:
        # --- 顯示即時資訊 ---
        col1, col2, col3 = st.columns(3)
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        change = current_price - prev_price
        pct_change = (change / prev_price) * 100

        col1.metric("當前股價", f"{current_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
        col2.metric("最高價 (期間)", f"{df['High'].max():.2f}")
        col3.metric("最低價 (期間)", f"{df['Low'].min():.2f}")

        # --- 繪製互動式 K 線圖 ---
        st.subheader(f"{stock_id} 股價走勢圖")
        
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                        open=df['Open'],
                        high=df['High'],
                        low=df['Low'],
                        close=df['Close'])])
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=500)
        st.plotly_chart(fig, use_container_width=True)

        # --- 顯示原始數據 ---
        with st.expander("查看歷史數據表格"):
            st.dataframe(df.sort_index(ascending=False))
            
    else:
        st.error("找不到股票數據，請確認代碼是否正確 (台股請加 .TW)")
