import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. 回測函數 (您的核心邏輯) ---
def run_backtest(df, initial_capital):
    capital = initial_capital
    shares = 0
    trade_log = []
    
    # 初始化欄位
    df['Portfolio_Value'] = initial_capital
    df['Shares_Held'] = 0
    df['Cash'] = initial_capital
    
    # 設定回測起始點 (確保有 MA20 資料)
    start_index = 20 
    
    for i in range(start_index, len(df)):
        date = df.index[i]
        price = df['Close'].iloc[i]
        
        # 取得當日與前一日的均線數據
        current_ma_short = df['MA5'].iloc[i]   # 短期均線
        current_ma_long = df['MA20'].iloc[i]   # 長期均線
        
        prev_ma_short = df['MA5'].iloc[i-1]
        prev_ma_long = df['MA20'].iloc[i-1]
        
        # --- 交易邏輯區 (全進全出) ---
        
        # 1. 買入訊號：黃金交叉 (短線由下往上穿過長線)
        buy_signal = (prev_ma_short < prev_ma_long) and (current_ma_short >= current_ma_long)
        
        # 2. 賣出訊號：死亡交叉 (短線由上往下穿過長線)
        sell_signal = (prev_ma_short > prev_ma_long) and (current_ma_short <= current_ma_long)
        
        # --- 執行交易 ---
        
        # 執行賣出
        if shares > 0 and sell_signal:
            cash_gain = shares * price
            capital += cash_gain
            
            trade_log.append({
                'Date': date,
                'Action': 'SELL',
                'Price': price,
                'Shares': shares,
                'Value': cash_gain,
                'Capital_After': capital
            })
            shares = 0 # 清空持股

        # 執行買入
        elif shares == 0 and buy_signal:
            shares_to_buy = int(capital / price / 1000) * 1000 
            
            if shares_to_buy > 0:
                cost = shares_to_buy * price
                capital -= cost
                shares += shares_to_buy
                
                trade_log.append({
                    'Date': date,
                    'Action': 'BUY',
                    'Price': price,
                    'Shares': shares_to_buy,
                    'Value': cost,
                    'Capital_After': capital
                })
        
        # --- 紀錄每日狀態 ---
        df.loc[date, 'Portfolio_Value'] = capital + (shares * price)
        df.loc[date, 'Shares_Held'] = shares
        df.loc[date, 'Cash'] = capital

    # 回測結束結算
    if shares > 0:
        final_price = df['Close'].iloc[-1]
        final_value = shares * final_price
        capital += final_value
        trade_log.append({
            'Date': df.index[-1], 
            'Action': 'Final Liquidation', 
            'Price': final_price, 
            'Shares': shares, 
            'Value': final_value, 
            'Capital_After': capital
        })
        shares = 0

    return capital, trade_log, df

# --- 2. 網頁介面與資料下載 (這部分一定要在回測之前！) ---

st.title("股票回測系統 (MA5 vs MA20)")

# 設定輸入選項
col1, col2 = st.columns(2)
with col1:
    ticker = st.text_input("輸入股票代號", "2330.TW")
with col2:
    initial_capital = st.number_input("初始本金", value=1000000)

start_date = st.date_input("開始日期", pd.to_datetime("2022-01-01"))
end_date = st.date_input("結束日期", pd.to_datetime("today"))

if ticker:
    # 步驟 1: 下載資料 (這就是創造 df 的過程)
    try:
        df = yf.download(ticker, start=start_date, end=end_date)
        
        # 檢查資料是否下載成功
        if df.empty:
            st.error("找不到資料，請檢查股票代號。")
        else:
            # 處理 yfinance 新版格式問題
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 步驟 2: 計算均線 (回測函數需要用到這些欄位)
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            
            # 畫出股價走勢
            st.subheader(f"{ticker} 歷史股價")
            st.line_chart(df['Close'])
            
            # 步驟 3: 準備執行回測
            # 移除 NaN (因為計算 MA 前幾天會有空值)
            df_clean = df.dropna()

            # --- 呼叫回測函數 ---
            st.divider()
            st.subheader("回測結果")
            
            # 這裡呼叫函數，傳入準備好的資料
            final_capital, log, result_df = run_backtest(df_clean, initial_capital)

            # --- 顯示結果 ---
            
            # 計算報酬率
            roi = ((final_capital - initial_capital) / initial_capital) * 100
            
            # 顯示指標
            col1, col2 = st.columns(2)
            col1.metric("最終總資產", f"${int(final_capital):,}")
            col2.metric("投資報酬率 (ROI)", f"{roi:.2f}%", delta=f"{roi:.2f}%")

            # 繪製資產曲線圖
            st.line_chart(result_df['Portfolio_Value'])

            # 顯示詳細交易紀錄
            if log:
                with st.expander("查看詳細交易紀錄"):
                    st.dataframe(pd.DataFrame(log))
            else:
                st.info("這段期間沒有觸發任何交易 (沒有黃金/死亡交叉)。")

    except Exception as e:
        st.error(f"發生錯誤: {e}")
