import pandas as pd
import yfinance as yf
import numpy as np
import os

# --- CONFIGURATION ---
EXCEL_FILE = '290 etf.xlsx' # CHANGE THIS TO YOUR EXCEL FILE NAME
OUTPUT_FILE = 'historical_baseline.csv'

def process_etf_data():
    print(f"Loading {EXCEL_FILE}...")
    df_master = pd.read_excel(EXCEL_FILE)
    
    if 'Ticker' not in df_master.columns:
        print("Error: Could not find 'Ticker' column in Excel file.")
        return

    tickers = df_master['Ticker'].dropna().astype(str).tolist()

    print(f"Fetching 1-year historical data for {len(tickers)} ETFs...")
    # Batch download 1 year of daily data
    historical_data = yf.download(tickers, period="1y", interval="1d")['Close']

    metrics_list = []

    print("Calculating metrics...")
    for ticker in tickers:
        if ticker not in historical_data.columns:
            continue
            
        prices = historical_data[ticker].dropna()
        if len(prices) < 2:
            continue

        yesterday_close = float(prices.iloc[-1])
        
        # Calculate Returns (Assuming 252 trading days/year)
        def calc_return(days_back):
            if len(prices) > days_back:
                return ((yesterday_close - float(prices.iloc[-(days_back + 1)])) / float(prices.iloc[-(days_back + 1)])) * 100
            return np.nan

        ret_1d = calc_return(1)
        ret_1w = calc_return(5)
        ret_1m = calc_return(21)
        ret_3m = calc_return(63)
        ret_6m = calc_return(126)
        ret_1y = calc_return(252) if len(prices) >= 252 else ((yesterday_close - float(prices.iloc[0])) / float(prices.iloc[0])) * 100

        # Calculate 52-Week Positioning
        high_52w = float(prices.max())
        low_52w = float(prices.min())

        metrics_list.append({
            'Ticker': ticker,
            'Yesterday_Close': round(yesterday_close, 2),
            '1D (%)': round(ret_1d, 2),
            '1W (%)': round(ret_1w, 2),
            '1M (%)': round(ret_1m, 2),
            '3M (%)': round(ret_3m, 2),
            '6M (%)': round(ret_6m, 2),
            '1Y (%)': round(ret_1y, 2),
            '52W High': round(high_52w, 2),
            '52W Low': round(low_52w, 2)
        })

    # Merge metrics with original Excel data
    df_metrics = pd.DataFrame(metrics_list)
    df_final = pd.merge(df_master, df_metrics, on='Ticker', how='inner')
    
    # Save to CSV
    df_final.to_csv(OUTPUT_FILE, index=False)
    print(f"Success! Saved baseline data to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_etf_data()