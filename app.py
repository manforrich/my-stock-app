import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import feedparser
from datetime import datetime, timedelta
import urllib.parse

# --- 1. 網頁設定 ---
st.set_page_config(page_title="台股分析儀表板 Ultimate", layout="wide")
st.title("📈 台股個股分析儀表板 Ultimate")

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

# --- 3. 側邊欄設定 (新增回測參數) ---
st.sidebar.header("選股設定")
selected_category = st.sidebar.selectbox("1️⃣ 選擇產業類別", list(stock_categories.keys()))

if selected_category == "🔍 自行輸入代號":
    stock_input = st.sidebar.text_input("輸入台股代號 (如 2330)", "2330")
    target_stock = stock_input
    stock_name_for_news = stock_input
else:
    category_stocks = stock_categories[selected_category]
    selected_stock_name = st.sidebar.selectbox("2️⃣ 選擇個股", list(category_stocks.keys()))
    target_stock = category_stocks[selected_stock_name]
    
    stock_name_for_news = selected_stock_name.split(" ")[1] if " " in selected_stock_name else target_stock

days = st.sidebar.slider("📅 觀察天數", 30, 730, 365) # 預設改為一年

st.sidebar.markdown("---")
st.sidebar.header("🤖 回測策略參數")
initial_capital = st.sidebar.number_input("起始資金 (NT$)", min_value=100000, value=1000000, step=10000)
st.sidebar.caption("策略：碰 MA 買入 / 跌破 MA 減碼/出場")

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
        
        # --- 新增 MA10 和 MA60 計算 ---
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean() # 新增 MA10
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean() # 新增季線 MA60
        
        if df.empty:
            return None
        return df.dropna(subset=['MA60']) # 確保從有季線資料的地方開始回測
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

# --- 5. 回測引擎 (Backtesting Logic) ---

def run_backtest(df, initial_capital):
    capital = initial_capital
    shares = 0
    trade_log = []
    
    # 初始化投資組合價值 (為了繪圖)
    df['Portfolio_Value'] = initial_capital
    df['Shares_Held'] = 0
    df['Cash'] = initial_capital
    
    # 從有 MA60 資料的第二天開始回測
    for i in range(1, len(df)):
        date = df.index[i]
        price = df['Close'].iloc[i]
        
        # 前一日的資料 (用於判斷是否發生穿越/跌破)
        prev_close = df['Close'].iloc[i-1]
        prev_ma5 = df['MA5'].iloc[i-1]
        prev_ma10 = df['MA10'].iloc[i-1]
        prev_ma20 = df['MA20'].iloc[i-1]
        prev_ma60 = df['MA60'].iloc[i-1]
        
        # 當日均線
        current_ma5 = df['MA5'].iloc[i]
        current_ma10 = df['MA10'].iloc[i]
        current_ma20 = df['MA20'].iloc[i]
        current_ma60 = df['MA60'].iloc[i]
        
        # 總資產現值 (當日開盤前)
        current_portfolio_value = capital + shares * price
        
        # --- 賣出/出場邏輯 (優先判斷) ---
        
        # 1. 跌破季線 (MA60) 則全部出場
        if shares > 0 and prev_close > prev_ma60 and price < current_ma60:
            amount_to_sell = shares
            cash_gain = amount_to_sell * price
            capital += cash_gain
            shares -= amount_to_sell
            trade_log.append({'Date': date, 'Price': price, 'Action': 'EXIT ALL', 'Shares': amount_to_sell, 'Value': amount_to_sell * price, 'Capital_After': capital})
            
        # 2. 跌破月線 (MA20) 則減碼 50%
        elif shares > 0 and prev_close > prev_ma20 and price < current_ma20:
            amount_to_sell = shares * 0.5
            amount_to_sell = int(amount_to_sell / 1000) * 1000 # 台灣單位為張 (1000 股)
            if amount_to_sell > 0:
                cash_gain = amount_to_sell * price
                capital += cash_gain
                shares -= amount_to_sell
                trade_log.append({'Date': date, 'Price': price, 'Action': 'SELL 50%', 'Shares': amount_to_sell, 'Value': amount_to_sell * price, 'Capital_After': capital})

        # --- 買入/加碼邏輯 ---

        # 3. 碰觸 (穿越) 10日線 則加碼 10%
        elif capital > 0 and prev_close < prev_ma10 and price >= current_ma10:
            investment_amount = current_portfolio_value * 0.10
            shares_to_buy = int(investment_amount / price / 1000) * 1000
            
            # 確保有足夠的現金，且買入單位不為零
            if shares_to_buy > 0 and capital >= shares_to_buy * price:
                capital -= shares_to_buy * price
                shares += shares_to_buy
                trade_log.append({'Date': date, 'Price': price, 'Action': 'BUY 10% (MA10)', 'Shares': shares_to_buy, 'Value': shares_to_buy * price, 'Capital_After': capital})

        # 4. 碰觸 (穿越) 5日線 則加碼 5%
        elif capital > 0 and prev_close < prev_ma5 and price >= current_ma5:
            investment_amount = current_portfolio_value * 0.05
            shares_to_buy = int(investment_amount / price / 1000) * 1000
            
            if shares_to_buy > 0 and capital >= shares_to_buy * price:
                capital -= shares_to_buy * price
                shares += shares_to_buy
                trade_log.append({'Date': date, 'Price': price, 'Action': 'BUY 5% (MA5)', 'Shares': shares_to_buy, 'Value': shares_to_buy * price, 'Capital_After': capital})
                
        # 紀錄每日資產狀態
        df.loc[date, 'Portfolio_Value'] = capital + shares * price
        df.loc[date, 'Shares_Held'] = shares
        df.loc[date, 'Cash'] = capital
        
    # 回測結束，清算剩餘持股
    if shares > 0:
        final_price = df['Close'].iloc[-1]
        cash_gain = shares * final_price
        capital += cash_gain
        shares = 0
        trade_log.append({'Date': df.index[-1], 'Price': final_price, 'Action': 'Final Liquidation', 'Shares': amount_to_sell, 'Value': cash_gain, 'Capital_After': capital})
    
    return capital, trade_log, df

# --- 6. 畫面呈現 ---

with st.spinner('正在分析股價、回測策略與搜尋新聞...'):
    data = get_data(ticker, days)

if data is not None and not data.empty:
    
    # 執行回測並取得結果
    final_capital, trade_log, data = run_backtest(data.copy(), initial_capital)
    
    try:
        # 頂部指標
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("股票代號", target_stock)
        col2.metric("起始資金", f"NT$ {initial_capital:,}")
        
        final_return = (final_capital - initial_capital) / initial_capital * 100
        col3.metric("最終資產", f"NT$ {final_capital:,.0f}", f"{final_return:,.2f}%")
        
        # 計算買入持有策略的回報 (Buy and Hold Benchmark)
        if initial_capital > 0:
            benchmark_return = (data['Close'].iloc[-1] / data['Close'].iloc[0] - 1) * 100
            col4.metric("買入持有回報 (Buy & Hold)", f"{benchmark_return:,.2f}%")

        st.markdown("---")
        
        # --- A. 繪圖區 (新增投資組合價值線) ---
        st.subheader(f"📈 {target_stock} 股價走勢與策略回測圖")
        
        fig = make_subplots(
            rows=3, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            subplot_titles=(f'{target_stock} 股價', '投資組合價值', '成交量'),
            row_width=[0.2, 0.3, 0.5] # 股價佔 50%，價值佔 30%，成交量佔 20%
        )

        # K線 (Row 1)
        fig.add_trace(go.Candlestick(
            x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='K線'
        ), row=1, col=1)

        # 均線 (Row 1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MA5'], mode='lines', name='MA5', line=dict(color='orange', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MA10'], mode='lines', name='MA10', line=dict(color='yellow', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], mode='lines', name='MA20', line=dict(color='purple', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MA60'], mode='lines', name='MA60 (季)', line=dict(color='green', width=1)), row=1, col=1)

        # 投資組合價值線 (Row 2)
        fig.add_trace(go.Scatter(
            x=data.index, y=data['Portfolio_Value'], mode='lines', name='組合價值', line=dict(color='#1E90FF', width=2)
        ), row=2, col=1)
        
        # 成交量 (Row 3)
        volume_colors = ['red' if row['Close'] >= row['Open'] else 'green' for i, row in data.iterrows()]
        fig.add_trace(go.Bar(
            x=data.index, y=data['Volume'], name='成交量', marker_color=volume_colors
        ), row=3, col=1)

        fig.update_layout(
            xaxis_rangeslider_visible=False, 
            height=800, 
            template="plotly_dark", 
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=True,
            xaxis3_title="日期" # 調整最下方的X軸標題
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- B. 交易紀錄 ---
        st.subheader("📋 交易紀錄 (Trade Log)")
        if trade_log:
             df_trades = pd.DataFrame(trade_log)
             st.dataframe(df_trades.sort_values(by='Date', ascending=False).style.format({"Price": "NT$ {:,.2f}", "Value": "NT$ {:,.0f}", "Capital_After": "NT$ {:,.0f}"}))
        else:
             st.info("回測期間內，沒有觸發任何交易訊號。")

        # --- C. 詳細數據與新聞 ---
        with st.expander("📊 查看詳細歷史數據"):
            st.dataframe(data.sort_index(ascending=False).style.format({"Open": "{:.2f}", "Close": "{:.2f}", "Volume": "{:,}", "MA5": "{:.2f}"}))
        
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
        st.error(f"畫面或回測處理錯誤: {e}")
        st.write("請檢查選股範圍，確保資料完整性足夠計算均線 (約60天)。")
else:
    st.warning(f"找不到代號 {target_stock} 的資料。")
