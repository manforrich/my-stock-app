import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser
import datetime

# 1. 設定網頁標題
st.set_page_config(page_title="股票分析儀表板", layout="wide")
st.title("📈 股票分析儀表板 (籌碼密集區版)")

# 2. 側邊欄：設定參數
st.sidebar.header("設定參數")
stock_id = st.sidebar.text_input("輸入股票代碼", value="2330.TW")

# --- 時間模式切換 ---
time_mode = st.sidebar.radio("選擇時間模式", ["預設區間", "自訂日期"])

start_date = None
end_date = None
selected_period = None

if time_mode == "預設區間":
    selected_period = st.sidebar.selectbox("選擇時間範圍", ["3mo", "6mo", "1y", "2y", "5y", "max"], index=2)
else:
    default_start = datetime.date.today() - datetime.timedelta(days=365)
    start_date = st.sidebar.date_input("開始日期", default_start)
    end_date = st.sidebar.date_input("結束日期", datetime.date.today())

# --- 技術指標設定 ---
st.sidebar.subheader("技術指標")
ma_days = st.sidebar.multiselect("顯示均線 (MA)", [5, 10, 20, 60, 120, 240], default=[5, 20])
show_bb = st.sidebar.checkbox("顯示布林通道 (Bollinger Bands)", value=False)
show_vp = st.sidebar.checkbox("顯示成交量分佈 (Volume Profile)", value=True) # <--- 新增成交密集區開關
show_gaps = st.sidebar.checkbox("顯示跳空缺口 (Gaps)", value=True)

# 3. 抓取股價數據
def get_stock_data(ticker, mode, period=None, start=None, end=None):
    try:
        stock = yf.Ticker(ticker)
        if mode == "預設區間":
            hist = stock.history(period=period)
        else:
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
        col2.metric("最高價 (區間)", f"{df['High'].max():.2f}")
        col3.metric("最低價 (區間)", f"{df['Low'].min():.2f}")
        col4.metric("最新成交量", f"{current_volume:,}")

        # --- B. 畫圖 ---
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
        
        # --- Volume Profile (成交密集區) 邏輯 ---
        if show_vp:
            # 建立一個隱藏的 X 軸 (xaxis2) 給 Volume Profile 使用
            # 我們設定 range 為倒過來，讓柱狀圖靠右邊顯示
            # nbinsy 是將價格切成幾等份，通常 50-100 之間效果最好
            fig.add_trace(go.Histogram(
                y=df['Close'], 
                x=df['Volume'], # 用成交量作為權重
                histfunc='sum', # 加總成交量
                orientation='h', # 水平方向
                nbinsy=50,       # 切成 50 個價格區間
                name="籌碼分佈",
                xaxis='x2',      # 指定使用第二個 X 軸
                marker=dict(color='rgba(0, 0, 0, 0.2)'), # 灰色半透明
                hoverinfo='none' # 滑鼠移上去不顯示資訊，避免干擾 K 線
            ), row=1, col=1)

            # 設定第二個 X 軸的樣式 (隱藏刻度，並設定範圍)
            fig.update_layout(
                xaxis2=dict(
                    overlaying='x',  # 疊加在原本的 x 軸上
                    side='top',      # 標籤放在上面(雖然我們設為隱藏)
                    showgrid=False,  # 不顯示網格
                    visible=False,   # 隱藏軸線
                    # 關鍵設定：range=[最大量的4倍, 0]
                    # 這會讓柱狀圖只佔畫面的 1/4 (右邊)，且從右向左長出來
                    range=[df['Volume'].sum()/2, 0] 
                )
            )

        # 2. 均線
        colors = ['orange', 'blue', 'purple', 'black', 'green', 'red']
        for i, days in enumerate(ma_days):
            ma_name = f"MA{days}"
            df[ma_name] = df['Close'].rolling(window=days).mean()
            fig.add_trace(go.Scatter(x=df.index, y=df[ma_name], mode='lines', name=ma_name,
                                     line=dict(width=1.5, color=colors[i % len(colors)])),
                          row=1, col=1)

        # 3. 布林通道
        if show_bb:
            bb_period = 20
            std_dev = 2
            df['BB_Mid'] = df['Close'].rolling(window=bb_period).mean()
            df['BB_Std'] = df['Close'].rolling(window=bb_period).std()
            df['BB_Upper'] = df['BB_Mid'] + (std_dev * df['BB_Std'])
            df['BB_Lower'] = df['BB_Mid'] - (std_dev * df['BB_Std'])
            
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'],
                                     line=dict(color='rgba(0, 100, 255, 0.3)', width=1),
                                     mode='lines', name='BB 下軌', showlegend=False),
                          row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'],
                                     line=dict(color='rgba(0, 100, 255, 0.3)', width=1),
                                     mode='lines', fill='tonexty', 
                                     fillcolor='rgba(0, 100, 255, 0.1)', name='布林通道'),
                          row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Mid'],
                                     line=dict(color='rgba(0, 100, 255, 0.6)', width=1, dash='dash'),
                                     mode='lines', name='BB 中軌'),
                          row=1, col=1)

        # 4. 成交量
        vol_colors = ['green' if row['Close'] >= row['Open'] else 'red' for index, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, name="成交量"), 
                      row=2, col=1)

        # 5. 缺口偵測
        if show_gaps:
            gap_shapes = []
            for i in range(1, len(df)):
                curr_low = df['Low'].iloc[i]
                curr_high = df['High'].iloc[i]
                prev_high = df['High'].iloc[i-1]
                prev_low = df['Low'].iloc[i-1]
                curr_date = df.index[i]
                prev_date = df.index[i-1]
                
                if curr_low > prev_high:
                    gap_shapes.append(dict(type="rect", xref="x", yref="y",
                        x0=prev_date, x1=curr_date, y0=prev_high, y1=curr_low,
                        fillcolor="rgba(0, 255, 0, 0.3)", line=dict(width=0)))
                elif curr_high < prev_low:
                    gap_shapes.append(dict(type="rect", xref="x", yref="y",
                        x0=prev_date, x1=curr_date, y0=curr_high, y1=prev_low,
                        fillcolor="rgba(255, 0, 0, 0.3)", line=dict(width=0)))
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
        st.error("找不到數據，請檢查代碼或日期範圍。")
