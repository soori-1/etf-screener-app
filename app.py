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
        if isinstance(live_data.columns, pd.MultiIndex):
            close_data = live_data['Close']
        elif 'Close' in live_data.columns:
            close_data = live_data['Close']
        else:
            close_data = live_data
            
        close_data = close_data.ffill() 
        
        if len(close_data) >= 2:
            latest_prices = close_data.iloc[-1]  
            prev_prices = close_data.iloc[-2]    
            returns_1d = ((latest_prices - prev_prices) / prev_prices) * 100
            
            df_live = pd.DataFrame({
                'Ticker': returns_1d.index.astype(str).str.strip(),
                'Live_CMP': latest_prices.values,
                'Dynamic_1D_Return': returns_1d.values
            })
            return df_live
        else:
            return pd.DataFrame(columns=['Ticker', 'Live_CMP', 'Dynamic_1D_Return'])
    except Exception:
        return pd.DataFrame(columns=['Ticker', 'Live_CMP', 'Dynamic_1D_Return'])

# Load Base Data
df_baseline = load_baseline()
tickers_list = df_baseline['Ticker'].dropna().tolist()

# --- 4. HEADER & REFRESH LOGIC ---
st.write("") 
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("🌐 Global ETF Screener Dashboard")
with col_btn:
    st.write("") 
    refresh_clicked = st.button("🔄 Refresh Live Prices", use_container_width=True)

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = "Never"

if refresh_clicked or 'df_merged' not in st.session_state:
    with st.spinner("Fetching live prices and volume from Yahoo Finance..."):
        df_live = get_live_prices(tickers_list)
        df_vol = load_volume_data(tickers_list)
        
        df_merged = pd.merge(df_baseline, df_live, on='Ticker', how='left')
        df_merged = pd.merge(df_merged, df_vol, on='Ticker', how='left')
        
        # Map 1D Return dynamically
        if 'Dynamic_1D_Return' in df_merged.columns:
            df_merged['Intraday 1D (%)'] = df_merged['Dynamic_1D_Return']
        else:
            df_merged['Intraday 1D (%)'] = np.nan

        # Safe 52W Math
        if '52W High' in df_merged.columns and '52W Low' in df_merged.columns:
            df_merged['% From 52W High'] = ((df_merged['Live_CMP'] - df_merged['52W High']) / df_merged['52W High']) * 100
            df_merged['% From 52W Low'] = ((df_merged['Live_CMP'] - df_merged['52W Low']) / df_merged['52W Low']) * 100
        
        cols_to_round = ['Live_CMP', 'Intraday 1D (%)', '% From 52W High', '% From 52W Low']
        for col in cols_to_round:
            if col in df_merged.columns:
                df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').round(2)
        
        st.session_state.df_merged = df_merged
        st.session_state.last_refresh = datetime.now().strftime('%H:%M:%S')

df = st.session_state.df_merged
st.caption(f"Last updated: {st.session_state.last_refresh}")
st.divider()

# --- 5. INTERACTIVE FILTERS ---
st.subheader("🔍 Filters")
col1, col2, col3 = st.columns(3)

with col1:
    selected_countries = st.multiselect("Region Exposure", options=sorted(df['Country'].dropna().unique()))
with col2:
    selected_sectors = st.multiselect("Sector", options=sorted(df['Sector'].dropna().unique()))
with col3:
    selected_themes = st.multiselect("Theme", options=sorted(df['Theme'].dropna().unique()))

filtered_df = df.copy()
if selected_countries:
    filtered_df = filtered_df[filtered_df['Country'].isin(selected_countries)]
if selected_sectors:
    filtered_df = filtered_df[filtered_df['Sector'].isin(selected_sectors)]
if selected_themes:
    filtered_df = filtered_df[filtered_df['Theme'].isin(selected_themes)]

st.divider()

# --- 6. ADVANCED TREEMAP VISUALIZATION ---
st.subheader("📊 Capital Rotation Treemap")

timeframe_options = {
    "1 Day": "Intraday 1D (%)",
    "1 Week": "1W (%)",
    "1 Month": "1M (%)",
    "3 Months": "3M (%)",
    "6 Months": "6M (%)",
    "1 Year": "1Y (%)"
}

selected_timeframe = st.radio(
    "Select Performance Timeframe:",
    options=list(timeframe_options.keys()),
    horizontal=True
)

metric_col = timeframe_options[selected_timeframe]
st.write(f"Box Size = **30-Day Avg Volume** | Box Color = **{selected_timeframe} Performance**")

# --- DATA CLEANING ---
plot_df = filtered_df.copy()
plot_df = plot_df.dropna(subset=['Ticker'])

# Ensure the metric is absolutely a clean number
if metric_col in plot_df.columns:
    plot_df[metric_col] = pd.to_numeric(plot_df[metric_col], errors='coerce')
else:
    plot_df[metric_col] = np.nan

# Force Volume to have no NaNs
if '30D_Volume' in plot_df.columns:
    plot_df['30D_Volume'] = pd.to_numeric(plot_df['30D_Volume'], errors='coerce').fillna(1000)
    plot_df.loc[plot_df['30D_Volume'] <= 0, '30D_Volume'] = 1000 
else:
    plot_df['30D_Volume'] = 1000

# Drop any row that couldn't be converted to a number
plot_df = plot_df.dropna(subset=[metric_col])
# ----------------------------------

if plot_df.empty:
    st.warning("No ETFs match the selected filters or have data for this timeframe.")
else:
    if selected_timeframe == "1 Day":
        c_range = [-3, 3]
    elif selected_timeframe == "1 Week":
        c_range = [-5, 5]
    elif selected_timeframe == "1 Month":
        c_range = [-10, 10]
    else:
        c_range = [-25, 25] 

    fig = px.treemap(
        plot_df,
        path=[px.Constant("Global ETFs"), 'Sector', 'Theme', 'Ticker'], 
        values='30D_Volume',      
        color=metric_col,  
        color_continuous_scale='RdYlGn', 
        range_color=c_range
    )

    try:
        computed_colors = fig.data[0].marker.colors
        fig.data[0].text = [f"{c:.2f}%" if not pd.isna(c) else "0.00%" for c in computed_colors]
    except Exception:
        pass 

    fig.update_layout(
        margin=dict(t=0, l=10, r=10, b=0), 
        paper_bgcolor='rgba(0,0,0,0)',            
        plot_bgcolor='rgba(0,0,0,0)',
        coloraxis_colorbar=dict(
            title=f"Return (%)",
            thicknessmode="pixels", thickness=15,
            lenmode="pixels", len=300,
            yanchor="top", y=1,
            ticks="outside"
        )
    )

    # Plotly's native formatting - scales text beautifully
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>%{text}", 
        textfont_size=14,
        marker_line_color="#1E1E1E", 
        hovertemplate='<b>%{label}</b><br>Return: %{text}<br>Volume: %{value:,.0f}'
    )

    st.plotly_chart(fig, use_container_width=True, theme="streamlit") 

st.divider()

# --- 7. CORE METRICS TABLE ---
st.subheader("📋 Underlying Performance Data")
display_cols = [
    'Ticker', 'Name', 'Sector', 'Theme', 
    'Intraday 1D (%)', 'Live_CMP', '30D_Volume',
    '1W (%)', '1M (%)', '1Y (%)', 
    '% From 52W High', '% From 52W Low'
]

valid_cols = [col for col in display_cols if col in plot_df.columns]

st.dataframe(
    plot_df[valid_cols].sort_values(by='Intraday 1D (%)', ascending=False) if 'Intraday 1D (%)' in valid_cols else plot_df[valid_cols], 
    use_container_width=True, 
    hide_index=True
)
