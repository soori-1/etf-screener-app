import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime
import numpy as np

# --- 1. Page Configuration ---
st.set_page_config(page_title="Right Horizons - Global ETF Screener", layout="wide")
st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)

# --- 2. Data Handling (Baseline + Volume) ---
@st.cache_data
def load_baseline():
    try:
        df = pd.read_csv('historical_baseline.csv')
        df['Sector'] = df['Sector'].fillna('Other Sectors')
        df['Theme'] = df['Theme'].fillna('Other Themes')
        df['Country'] = df['Country'].fillna('Unclassified')
        return df
    except FileNotFoundError:
        st.error("⚠️ historical_baseline.csv not found. Please run update_baseline.py first.")
        st.stop()

@st.cache_data
def load_volume_data(tickers):
    try:
        vol_data = yf.download(tickers, period="1mo", interval="1d")['Volume']
        avg_vol = vol_data.mean()
        df_vol = avg_vol.reset_index()
        df_vol.columns = ['Ticker', '30D_Volume']
        return df_vol
    except Exception as e:
        return pd.DataFrame(columns=['Ticker', '30D_Volume'])

# --- 3. Live Price Fetcher ---
def get_live_prices(tickers):
    try:
        live_data = yf.download(tickers, period="1d", interval="1m")['Close']
        latest_prices = live_data.ffill().iloc[-1] 
        df_live = latest_prices.reset_index()
        df_live.columns = ['Ticker', 'Live_CMP']
        return df_live
    except Exception as e:
        return pd.DataFrame(columns=['Ticker', 'Live_CMP'])

# Load Base Data
df_baseline = load_baseline()
tickers_list = df_baseline['Ticker'].dropna().tolist()

# --- 4. HEADER & REFRESH LOGIC ---
st.write("") 
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("🌐 Right Horizons - Global ETF Screener Dashboard")
with col_btn:
    st.write("") 
    refresh_clicked = st.button("🔄 Refresh Live Prices", use_container_width=True)

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = "Never"

if refresh_clicked or 'df_merged' not in st.session_state:
    with st.spinner("Fetching live prices and 30-Day Volume data..."):
        df_live = get_live_prices(tickers_list)
        df_vol = load_volume_data(tickers_list)
        
        df_merged = pd.merge(df_baseline, df_live, on='Ticker', how='left')
        df_merged = pd.merge(df_merged, df_vol, on='Ticker', how='left')
        
        df_merged['Live_CMP'] = df_merged['Live_CMP'].fillna(df_merged['Yesterday_Close'])
        df_merged['Intraday 1D (%)'] = ((df_merged['Live_CMP'] - df_merged['Yesterday_Close']) / df_merged['Yesterday_Close']) * 100
        df_merged['% From 52W High'] = ((df_merged['Live_CMP'] - df_merged['52W High']) / df_merged['52W High']) * 100
        df_merged['% From 52W Low'] = ((df_merged['Live_CMP'] - df_merged['52W Low']) / df_merged['52W Low']) * 100
        
        cols_to_round = ['Live_CMP', 'Intraday 1D (%)', '% From 52W High', '% From 52W Low']
        for col in cols_to_round:
            df_merged[col] = df_merged[col].round(2)
        
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
st.subheader("📊 Capital Rotation Treemap (Finviz Style)")

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
plot_df[metric_col] = pd.to_numeric(plot_df[metric_col], errors='coerce')

if '30D_Volume' in plot_df.columns:
    plot_df['30D_Volume'] = pd.to_numeric(plot_df['30D_Volume'], errors='coerce').fillna(1000)
    plot_df.loc[plot_df['30D_Volume'] <= 0, '30D_Volume'] = 1000 
else:
    plot_df['30D_Volume'] = 1000

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

    # --- INLINE NAME & PERCENTAGE GENERATOR ---
    try:
        computed_colors = fig.data[0].marker.colors
        labels = fig.data[0].labels
        custom_text = []
        
        # Combine the sector/ETF name and its average directly side-by-side
        for label, c in zip(labels, computed_colors):
            if pd.isna(c):
                custom_text.append(f"<b>{label}</b>")
            else:
                custom_text.append(f"<b>{label}</b> ({c:.2f}%)")
                
        fig.data[0].text = custom_text
    except Exception as e:
        pass 
    # ----------------------------------------

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

    fig.update_traces(
        textinfo="text", # We tell Plotly to ONLY use our new combined text
        textfont_size=14,
        marker_line_color="#1E1E1E", 
        hovertemplate='<b>%{label}</b><br>Return: %{color:.2f}%<br>Volume: %{value:,.0f}'
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

st.dataframe(
    plot_df[display_cols].sort_values(by='Intraday 1D (%)', ascending=False), 
    use_container_width=True, 
    hide_index=True
)
