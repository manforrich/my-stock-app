import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser
import datetime # <--- 新增這個用來處理日期

# 1. 設定網頁標題
st.set_page_config(page_title="股票分析儀表板", layout="wide")
st.title("📈 股票分析儀表板 (自訂日期版)")

# 2. 側邊欄：設定參數
st.sidebar.header("設定參數")
stock_id = st.sidebar.text_input("輸入股票代碼", value="2330.TW")

# --- 新增功能：切換時間模式 ---
time_mode = st.sidebar.radio("選擇時間模式", ["預設區間", "自訂日期"])

start_date = None
end_date = None
selected_period = None

if time_mode == "預設區間":
    selected_period = st.sidebar.selectbox("選擇時間範圍", ["3mo", "6mo", "1y", "2y", "5y", "max"], index=2)
else:
    # 自訂日期模式
    # 預設開始日期為一年前，結束日期為今天
    default_start = datetime.date.today() - datetime.timedelta(days=365)
    start_date = st.sidebar.date_input("開始日期", default_start)
    end_date = st.sidebar.date_input("結束日期", datetime.date.today())

# --- 技術指標設定 ---
st.sidebar.subheader("技術指標")
ma_days = st.sidebar.multiselect("顯示均線 (MA)", [5, 10, 20, 60, 120, 240], default=[5, 20])
show_gaps = st.sidebar.checkbox("顯示跳空缺口 (Gaps)", value=True)

# 3. 抓取股價數據 (更新版：支援兩種模式)
def get_stock_data(ticker, mode, period=None, start=None, end=None):
    try:
        stock = yf.Ticker(ticker)
        if mode == "預設區間":
            hist = stock.history(period=period)
        else:
            # yfinance 的 end date 是不包含當天的，所以如果要包含選取的結束日，通常建議不用特別加一天，
            # 但為了確保數據完整，直接傳入日期物件即可
            hist = stock.history(start=start, end=end)
        return hist
    except Exception as e:
        return None

# 4. 抓取新聞函數
def get_google_news(query):
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    return feed.entries

# 5. 主程式邏輯
if stock_id:
    # 呼叫新的抓取函數
    df = get_stock_data(stock_id, time_mode, period=selected_period, start=start_date, end=end_date)
    
    if df is not None and not df.empty:
        # --- A. 顯示價格與成交量 ---
        col1, col2, col3, col4 = st.columns(4)
        
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        change = current_price - prev_price
        pct_change = (change / prev_price) * 100
        current_volume = df['Volume'].iloc[-1]

        col1.metric("當前股價", f"{current_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
        col2.metric("最高價 (區間)", f"{df['High'].max():.2f}") # 改名為區間
        col3.metric("最低價 (區間)", f"{df['Low'].min():.2f}") # 改名為區間
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
        fig.add_trace(go.Bar(x=df.index, 
                             y=df['Volume'], 
                             marker_color=vol_colors, 
                             name="成交量"), 
                      row=2, col=1)

        # 4. --- 缺口偵測邏輯 ---
        if show_gaps:
            gap_shapes = []
            for i in range(1, len(df)):
                curr_low = df['Low'].iloc[i]
                curr_high = df['High'].iloc[i]
                prev_high = df['High'].iloc[i-1]
                prev_low = df['Low'].iloc[i-1]
                
                curr_date = df.index[i]
                prev_date = df.index[i-1]
                
                # 跳空上漲
                if curr_low > prev_high:
                    gap_shapes.append(dict(
                        type="rect", xref="x", yref="y",
                        x0=prev_date, x1=curr_date,
                        y0=prev_high, y1=curr_low,
                        fillcolor="rgba(0, 255, 0, 0.3)", line=dict(width=0),
                    ))
                
                # 跳空下跌
                elif curr_high < prev_low:
                    gap_shapes.append(dict(
                        type="rect", xref="x", yref="y",
                        x0=prev_date, x1=curr_date,
                        y0=curr_high, y1=prev_low,
                        fillcolor="rgba(255, 0, 0, 0.3)", line=dict(width=0),
                    ))
            
            fig.update_layout(shapes=gap_shapes)

        # 設定版面
        fig.update_layout(xaxis_rangeslider_visible=False, height=600, showlegend=True)
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

        st.plotly_chart(fig, use_container_width=True)

        # --- C. 新聞 ---
        st.divider()
        st.subheader(f"📰 {stock_id} 最新新聞")
        news_items = get_google_news(stock_id)
        if news_items:
            for item in news_items[:6]:
                with st.expander(item.title):
                    st.write(f"發布時間: {item.published}")
                    st.markdown(f"[👉 點擊閱讀全文]({item.link})")
        else:
            st.info("目前找不到相關新聞")

        # --- D. 表格 ---
        with st.expander("查看數據表格"):
            st.dataframe(df.sort_index(ascending=False))

    else:
        # 錯誤處理優化：如果選的時間太短或沒開盤
        st.error("找不到數據。原因可能是：\n1. 股票代碼錯誤\n2. 選定的日期範圍內沒有交易 (例如假日)\n3. 自訂日期範圍設定錯誤 (開始日期晚於結束日期)")
