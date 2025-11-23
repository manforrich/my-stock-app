import pandas as pd

def run_backtest(df, initial_capital):
    capital = initial_capital
    shares = 0
    trade_log = []
    
    # 初始化欄位
    df['Portfolio_Value'] = initial_capital
    df['Shares_Held'] = 0
    df['Cash'] = initial_capital
    
    # 設定回測起始點 (確保有 MA 資料)
    # 假設我們以 MA20 為主，從第 20 天開始
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
        # 邏輯：昨天短線 < 昨天長線  AND  今天短線 >= 今天長線
        buy_signal = (prev_ma_short < prev_ma_long) and (current_ma_short >= current_ma_long)
        
        # 2. 賣出訊號：死亡交叉 (短線由上往下穿過長線)
        # 邏輯：昨天短線 > 昨天長線  AND  今天短線 <= 今天長線
        sell_signal = (prev_ma_short > prev_ma_long) and (current_ma_short <= current_ma_long)
        
        # --- 執行交易 ---
        
        # 執行賣出 (如果有持股 且 出現賣訊)
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

        # 執行買入 (如果沒持股 且 出現買訊 且 資金足夠)
        elif shares == 0 and buy_signal:
            # 簡單起見，全倉買入 (可自行調整為買 90% 或固定金額)
            shares_to_buy = int(capital / price / 1000) * 1000 # 無條件捨去至張數(1000股)
            
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

    # 回測結束：若還有持股，以最後一天收盤價計算最終價值
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
df = df.dropna()

# 1. 呼叫函數開始運算 (假設本金為 100 萬)
# 注意：這裡的 'df' 必須是您前面抓取股票資料後的那個變數名稱
final_capital, log, result_df = run_backtest(df, 1000000)

# 2. 使用 Streamlit 顯示文字結果
st.subheader("回測結果")
st.metric("最終總資產", f"{int(final_capital):,} 元")

# 3. 繪製資產曲線圖
st.line_chart(result_df['Portfolio_Value'])

# 4. 顯示詳細交易紀錄
if log:
    st.write("### 交易紀錄明細")
    st.dataframe(log)
else:
    st.write("這段期間沒有觸發任何交易。")
