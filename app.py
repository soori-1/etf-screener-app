import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime
import numpy as np

# --- 1. Page Configuration ---
st.set_page_config(page_title="Global ETF Screener", layout="wide")
st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)

# --- 2. Data Handling ---
@st.cache_data
def load_baseline():
    try:
        df = pd.read_csv('historical_baseline.csv')
        df['Sector'] = df['Sector'].fillna('Other Sectors')
        df['Theme'] = df['Theme'].fillna('Other Themes')
        df['Country'] = df['Country'].fillna('Unclassified')
        df['Ticker'] = df['Ticker'].astype(str).str.strip()
        
        # Heavy-duty cleaner: Strip '%' and ',' from historical returns
        timeframe_cols = ['1W (%)', '1M (%)', '3M (%)', '6M (%)', '1Y (%)']
        for col in timeframe_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('%', '', regex=False).str.replace(',', '', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except FileNotFoundError:
        st.error("⚠️ historical_baseline.csv not found.")
        st.stop()

def load_volume_data(tickers):
    try:
        vol_data = yf.download(tickers, period="1mo", interval="1d", threads=False)['Volume']
        avg_vol = vol_data.mean()
        df_vol = avg_vol.reset_index()
        df_vol.columns = ['Ticker', '30D_Volume']
        df_vol['Ticker'] = df_vol['Ticker'].astype(str).str.strip()
        return df_vol
    except Exception:
        return pd.DataFrame(columns=['Ticker', '30D_Volume'])

# --- 3. Weekend-Proof Live Fetcher ---
def get_live_prices(tickers):
    try:
        live_data = yf.download(tickers, period="5d", interval="1d", threads=False)
        
        # Safely extract close prices
        if isinstance(live_data.columns, pd.MultiIndex
