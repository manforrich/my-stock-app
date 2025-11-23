# --- 5. 回測引擎 (Backtesting Logic) ---

def run_backtest(df, initial_capital):
    capital = initial_capital
    shares = 0
    trade_log = []
    
    # 初始化投資組合價值 (用於繪圖)
    df['Portfolio_Value'] = initial_capital
    df['Shares_Held'] = 0
    df['Cash'] = initial_capital
    
    # 從有 MA60 資料的第二天開始回測
    for i in range(1, len(df)):
        date = df.index[i]
        price = df['Close'].iloc[i] # <-- **當日收盤價 (用於交易執行)**
        
        # 前一日的資料 (用於判斷是否發生穿越/跌破)
        prev_close = df['Close'].iloc[i-1]
        prev_ma60 = df['MA60'].iloc[i-1]
        
        # 當日均線
        current_ma5 = df['MA5'].iloc[i]
        current_ma10 = df['MA10'].iloc[i]
        current_ma20 = df['MA20'].iloc[i]
        current_ma60 = df['MA60'].iloc[i]
        
        # 總資產現值 (當日收盤前)
        current_portfolio_value = capital + shares * price
        
        # --- 賣出/出場邏輯 (優先判斷) ---
        
        # 1. 跌破季線 (MA60) 則全部出場
        if shares > 0 and prev_close > prev_ma60 and price < current_ma60:
            amount_to_sell = shares
            cash_gain = amount_to_sell * price # <-- 使用當日收盤價執行
            capital += cash_gain
            shares -= amount_to_sell
            trade_log.append({'Date': date, 'Price': price, 'Action': 'EXIT ALL', 'Shares': amount_to_sell, 'Value': amount_to_sell * price, 'Capital_After': capital})
            
        # 2. 跌破月線 (MA20) 則減碼 50%
        elif shares > 0 and prev_close > df['MA20'].iloc[i-1] and price < current_ma20:
            amount_to_sell = shares * 0.5
            amount_to_sell = int(amount_to_sell / 1000) * 1000 # 捨去到張
            if amount_to_sell > 0:
                cash_gain = amount_to_sell * price # <-- 使用當日收盤價執行
                capital += cash_gain
                shares -= amount_to_sell
                trade_log.append({'Date': date, 'Price': price, 'Action': 'SELL 50%', 'Shares': amount_to_sell, 'Value': amount_to_sell * price, 'Capital_After': capital})

        # --- 買入/加碼邏輯 ---

        # 3. 碰觸 (穿越) 10日線 則加碼 10%
        elif capital > 0 and prev_close < df['MA10'].iloc[i-1] and price >= current_ma10:
            investment_amount = current_portfolio_value * 0.10
            shares_to_buy = int(investment_amount / price / 1000) * 1000
            
            # 確保有足夠的現金，且買入單位不為零
            if shares_to_buy > 0 and capital >= shares_to_buy * price:
                capital -= shares_to_buy * price # <-- 使用當日收盤價執行
                shares += shares_to_buy
                trade_log.append({'Date': date, 'Price': price, 'Action': 'BUY 10% (MA10)', 'Shares': shares_to_buy, 'Value': shares_to_buy * price, 'Capital_After': capital})

        # 4. 碰觸 (穿越) 5日線 則加碼 5%
        elif capital > 0 and prev_close < df['MA5'].iloc[i-1] and price >= current_ma5:
            investment_amount = current_portfolio_value * 0.05
            shares_to_buy = int(investment_amount / price / 1000) * 1000
            
            if shares_to_buy > 0 and capital >= shares_to_buy * price:
                capital -= shares_to_buy * price # <-- 使用當日收盤價執行
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
