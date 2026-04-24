import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# ─────────────────────────────────────────────
# 1. PAGE CONFIG & GLOBAL STYLES
# ─────────────────────────────────────────────
st.set_page_config(page_title="Global ETF Screener | Right Horizons", layout="wide", page_icon="📊")

st.markdown("""
<style>
    /* ── Base & Background ── */
    .stApp { background-color: #F9F6F1; }
    div.block-container { padding-top: 0rem; padding-bottom: 1rem; }

    /* ── Header Banner ── */
    .rh-header {
        background: linear-gradient(135deg, #7B3F00 0%, #A0522D 50%, #C06A2F 100%);
        padding: 18px 32px;
        border-radius: 0 0 12px 12px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 15px rgba(123,63,0,0.25);
    }
    .rh-header h1 {
        color: #FFFFFF;
        font-size: 1.7rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.5px;
    }
    .rh-header p {
        color: #FFD9A0;
        font-size: 0.82rem;
        margin: 4px 0 0 0;
    }
    .rh-badge {
        background: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.3);
        border-radius: 20px;
        padding: 6px 16px;
        color: #FFFFFF;
        font-size: 0.78rem;
        font-weight: 600;
    }

    /* ── Section Cards ── */
    .rh-card {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 16px;
        border: 1px solid #E8DDD0;
        box-shadow: 0 2px 8px rgba(123,63,0,0.07);
    }
    .rh-card-title {
        color: #7B3F00;
        font-size: 0.95rem;
        font-weight: 700;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 2px solid #E8DDD0;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }

    /* ── Metric Pills ── */
    .metric-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
    .metric-pill {
        background: #FFF8F0;
        border: 1px solid #E8DDD0;
        border-radius: 8px;
        padding: 10px 18px;
        text-align: center;
        min-width: 120px;
    }
    .metric-pill .val { font-size: 1.3rem; font-weight: 700; color: #7B3F00; }
    .metric-pill .lbl { font-size: 0.7rem; color: #999; text-transform: uppercase; letter-spacing: 0.5px; }

    /* ── Radio buttons ── */
    div[role="radiogroup"] label {
        background: #FFF8F0 !important;
        border: 1px solid #D4956A !important;
        border-radius: 6px !important;
        color: #7B3F00 !important;
        font-weight: 600 !important;
        padding: 4px 14px !important;
        margin-right: 6px !important;
        font-size: 0.82rem !important;
    }
    div[role="radiogroup"] label[data-selected="true"],
    div[role="radiogroup"] input:checked + label {
        background: #7B3F00 !important;
        color: #FFFFFF !important;
    }

    /* ── Multiselect ── */
    .stMultiSelect [data-baseweb="select"] {
        border-color: #D4956A !important;
    }
    .stMultiSelect span[data-baseweb="tag"] {
        background-color: #A0522D !important;
        color: white !important;
    }

    /* ── Divider ── */
    hr { border-color: #E8DDD0 !important; }

    /* ── Refresh button ── */
    .stButton > button {
        background: linear-gradient(135deg, #A0522D, #7B3F00) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 8px 16px !important;
        box-shadow: 0 3px 10px rgba(123,63,0,0.3) !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #7B3F00, #5C2E00) !important;
        box-shadow: 0 5px 15px rgba(123,63,0,0.4) !important;
    }

    /* ── Caption / Last Updated ── */
    .stCaption { color: #A07850 !important; font-size: 0.78rem !important; }

    /* ── Dataframe header ── */
    .stDataFrame thead th {
        background-color: #7B3F00 !important;
        color: white !important;
    }

    /* ── Subheader override ── */
    h2, h3 { color: #7B3F00 !important; }

    /* ── Filter label ── */
    label[data-testid="stWidgetLabel"] { color: #5C2E00 !important; font-weight: 600 !important; }

    /* ── Spinner ── */
    .stSpinner > div { border-top-color: #A0522D !important; }

    /* ── Warning / Error ── */
    .stAlert { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 2. DATA FUNCTIONS
# ─────────────────────────────────────────────

@st.cache_data
def load_baseline():
    df = pd.read_csv('historical_baseline.csv')
    df['Sector']  = df['Sector'].fillna('Other Sectors')
    df['Theme']   = df['Theme'].fillna('Other Themes')
    df['Country'] = df['Country'].fillna('Unclassified')
    df['Ticker']  = df['Ticker'].astype(str).str.strip()
    df['Name']    = df['Name'].fillna(df['Ticker']) if 'Name' in df.columns else df['Ticker']

    for col in ['1W (%)', '1M (%)', '3M (%)', '6M (%)', '1Y (%)']:
        if col in df.columns:
            df[col] = (df[col].astype(str)
                       .str.replace('%', '', regex=False)
                       .str.replace(',', '', regex=False))
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def _fetch_single(ticker: str, period: str = "5d") -> dict:
    """Download one ticker safely; return dict with Close series."""
    try:
        data = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)
        if data.empty:
            return {}
        return {'close': data['Close'].dropna(), 'volume': data['Volume'].dropna()}
    except Exception:
        return {}


def get_live_prices(tickers: list) -> pd.DataFrame:
    records = []
    progress = st.progress(0, text="Fetching live prices…")
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        info = _fetch_single(ticker, period="5d")
        closes = info.get('close', pd.Series(dtype=float))

        if len(closes) >= 2:
            latest = float(closes.iloc[-1])
            prev   = float(closes.iloc[-2])
            ret_1d = round(((latest - prev) / prev) * 100, 2)
        else:
            latest, ret_1d = np.nan, np.nan

        records.append({'Ticker': ticker, 'Live_CMP': latest, 'Dynamic_1D_Return': ret_1d})
        progress.progress((i + 1) / total, text=f"Fetching {ticker}… ({i+1}/{total})")

    progress.empty()
    return pd.DataFrame(records)


def get_volume_data(tickers: list) -> pd.DataFrame:
    records = []
    for ticker in tickers:
        info = _fetch_single(ticker, period="1mo")
        vol  = info.get('volume', pd.Series(dtype=float))
        avg_vol = float(vol.mean()) if len(vol) > 0 else np.nan
        records.append({'Ticker': ticker, '30D_Volume': avg_vol})
    return pd.DataFrame(records)


# ─────────────────────────────────────────────
# 3. MAIN APP
# ─────────────────────────────────────────────

try:
    # ── Load CSV ──
    try:
        df_baseline  = load_baseline()
        tickers_list = df_baseline['Ticker'].dropna().unique().tolist()
    except FileNotFoundError:
        st.error("⚠️ historical_baseline.csv not found. Please upload it to your GitHub repository.")
        st.stop()

    # ── Header ──
    st.markdown(f"""
    <div class="rh-header">
        <div>
            <h1>🌐 Global ETF Screener Dashboard</h1>
            <p>Real-time capital rotation tracker powered by Yahoo Finance</p>
        </div>
        <div class="rh-badge">RIGHT HORIZONS</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Refresh Button ──
    col_refresh, col_ts = st.columns([1, 5])
    with col_refresh:
        refresh_clicked = st.button("🔄 Refresh Live Data", use_container_width=True)
    with col_ts:
        if 'last_refresh' in st.session_state:
            st.caption(f"⏱ Last updated: **{st.session_state.last_refresh}**  |  {len(tickers_list)} ETFs tracked")

    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = "Never"

    # ── Fetch / Cache ──
    if refresh_clicked or 'df_merged' not in st.session_state:
        df_live = get_live_prices(tickers_list)
        df_vol  = get_volume_data(tickers_list)

        df_merged = pd.merge(df_baseline, df_live, on='Ticker', how='left')
        df_merged = pd.merge(df_merged,   df_vol,  on='Ticker', how='left')

        df_merged['Intraday 1D (%)'] = df_merged.get('Dynamic_1D_Return', np.nan)

        if '52W High' in df_merged.columns and '52W Low' in df_merged.columns:
            df_merged['% From 52W High'] = ((df_merged['Live_CMP'] - df_merged['52W High']) / df_merged['52W High'] * 100).round(2)
            df_merged['% From 52W Low']  = ((df_merged['Live_CMP'] - df_merged['52W Low'])  / df_merged['52W Low']  * 100).round(2)

        for col in ['Live_CMP', 'Intraday 1D (%)']:
            if col in df_merged.columns:
                df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').round(2)

        st.session_state.df_merged    = df_merged
        st.session_state.last_refresh = datetime.now().strftime('%d %b %Y  %H:%M:%S')
        st.rerun()

    df = st.session_state.df_merged

    # ── Summary KPI Pills ──
    total_etfs   = len(df)
    gainers      = int((df['Intraday 1D (%)'] > 0).sum())
    losers       = int((df['Intraday 1D (%)'] < 0).sum())
    avg_ret      = df['Intraday 1D (%)'].mean()
    avg_ret_str  = f"{avg_ret:+.2f}%" if not np.isnan(avg_ret) else "—"

    st.markdown(f"""
    <div class="rh-card">
        <div class="rh-card-title">📈 Market Pulse — Today</div>
        <div class="metric-row">
            <div class="metric-pill"><div class="val">{total_etfs}</div><div class="lbl">Total ETFs</div></div>
            <div class="metric-pill"><div class="val" style="color:#27AE60">{gainers}</div><div class="lbl">Gainers</div></div>
            <div class="metric-pill"><div class="val" style="color:#C0392B">{losers}</div><div class="lbl">Losers</div></div>
            <div class="metric-pill"><div class="val">{avg_ret_str}</div><div class="lbl">Avg 1D Return</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────
    # 4. FILTERS
    # ─────────────────────────────────────────
    with st.expander("🔍 Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_countries = st.multiselect("🌍 Region Exposure", options=sorted(df['Country'].dropna().unique()))
        with col2:
            selected_sectors   = st.multiselect("🏭 Sector",          options=sorted(df['Sector'].dropna().unique()))
        with col3:
            selected_themes    = st.multiselect("💡 Theme",            options=sorted(df['Theme'].dropna().unique()))

    filtered_df = df.copy()
    if selected_countries:
        filtered_df = filtered_df[filtered_df['Country'].isin(selected_countries)]
    if selected_sectors:
        filtered_df = filtered_df[filtered_df['Sector'].isin(selected_sectors)]
    if selected_themes:
        filtered_df = filtered_df[filtered_df['Theme'].isin(selected_themes)]

    # ─────────────────────────────────────────
    # 5. TREEMAP
    # ─────────────────────────────────────────
    st.markdown('<div class="rh-card">', unsafe_allow_html=True)
    st.markdown('<div class="rh-card-title">📊 Capital Rotation Treemap — Finviz Style</div>', unsafe_allow_html=True)

    timeframe_options = {
        "1 Day":   "Intraday 1D (%)",
        "1 Week":  "1W (%)",
        "1 Month": "1M (%)",
        "3 Months":"3M (%)",
        "6 Months":"6M (%)",
        "1 Year":  "1Y (%)"
    }

    col_tf, col_info = st.columns([3, 2])
    with col_tf:
        selected_timeframe = st.radio(
            "Performance Timeframe:",
            options=list(timeframe_options.keys()),
            horizontal=True,
            label_visibility="collapsed"
        )
    with col_info:
        st.caption("📦 Box Size = 30-Day Avg Volume &nbsp;|&nbsp; 🎨 Box Color = Performance")

    metric_col = timeframe_options[selected_timeframe]

    plot_df = filtered_df.copy().dropna(subset=['Ticker'])

    if metric_col in plot_df.columns:
        plot_df[metric_col] = pd.to_numeric(plot_df[metric_col], errors='coerce')
    else:
        plot_df[metric_col] = np.nan

    plot_df['30D_Volume'] = pd.to_numeric(
        plot_df.get('30D_Volume', 1000), errors='coerce'
    ).fillna(1000).clip(lower=1)

    plot_df = plot_df.dropna(subset=[metric_col])

    if plot_df.empty:
        st.warning("⚠️ No ETFs match the selected filters or have data for this timeframe.")
    else:
        c_range_map = {
            "1 Day": [-3, 3], "1 Week": [-5, 5], "1 Month": [-10, 10],
            "3 Months": [-20, 20], "6 Months": [-25, 25], "1 Year": [-35, 35]
        }
        c_range = c_range_map.get(selected_timeframe, [-10, 10])

        fig = px.treemap(
            plot_df,
            path=[px.Constant("Global ETFs"), 'Sector', 'Theme', 'Ticker'],
            values='30D_Volume',
            color=metric_col,
            color_continuous_scale=[
                [0.0,  '#8B0000'],
                [0.2,  '#C0392B'],
                [0.4,  '#E67E22'],
                [0.5,  '#FFF8F0'],
                [0.6,  '#A8D5A2'],
                [0.8,  '#27AE60'],
                [1.0,  '#145A32'],
            ],
            range_color=c_range,
            custom_data=['Name']
        )

        fig.update_layout(
            height=520,
            margin=dict(t=10, l=5, r=5, b=5),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Arial, sans-serif"),
            coloraxis_colorbar=dict(
                title=dict(text="Return (%)", font=dict(size=12, color='#7B3F00')),
                thicknessmode="pixels", thickness=14,
                lenmode="pixels",       len=280,
                yanchor="top",          y=1,
                ticks="outside",
                tickfont=dict(size=11),
            )
        )

        fig.update_traces(
            texttemplate="<b>%{label}</b><br>%{color:.2f}%",
            textfont=dict(size=13, family="Arial, sans-serif"),
            marker_line_color="#F9F6F1",
            marker_line_width=1.5,
            hovertemplate=(
                '<b>%{label}</b><br>'
                '<i>%{customdata[0]}</i><br>'
                '──────────────<br>'
                'Return : <b>%{color:.2f}%</b><br>'
                'Avg Vol: <b>%{value:,.0f}</b>'
                '<extra></extra>'
            )
        )

        st.plotly_chart(fig, use_container_width=True, theme=None)

    st.markdown('</div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────
    # 6. DATA TABLE
    # ─────────────────────────────────────────
    st.markdown('<div class="rh-card">', unsafe_allow_html=True)
    st.markdown('<div class="rh-card-title">📋 Underlying Performance Data</div>', unsafe_allow_html=True)

    display_cols = [
        'Ticker', 'Name', 'Sector', 'Theme', 'Country',
        'Live_CMP', 'Intraday 1D (%)',
        '1W (%)', '1M (%)', '3M (%)', '6M (%)', '1Y (%)',
        '% From 52W High', '% From 52W Low', '30D_Volume'
    ]
    valid_cols = [c for c in display_cols if c in plot_df.columns]

    sort_col = 'Intraday 1D (%)' if 'Intraday 1D (%)' in valid_cols else valid_cols[0]

    # Color positive/negative in the table
    styled = (
        plot_df[valid_cols]
        .sort_values(by=sort_col, ascending=False)
        .reset_index(drop=True)
    )

    # Highlight columns
    pct_cols = [c for c in valid_cols if '(%)' in c]

    def color_pct(val):
        try:
            v = float(val)
            if v > 0:   return 'color: #27AE60; font-weight:600'
            elif v < 0: return 'color: #C0392B; font-weight:600'
        except: pass
        return ''

    st.dataframe(
        styled.style.applymap(color_pct, subset=pct_cols)
                    .format({c: "{:.2f}" for c in pct_cols if c in styled.columns}, na_rep="—")
                    .format({'Live_CMP': "{:.2f}", '30D_Volume': "{:,.0f}"}, na_rep="—"),
        use_container_width=True,
        hide_index=True,
        height=420
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div style="text-align:center; padding:16px; color:#A07850; font-size:0.75rem; border-top:1px solid #E8DDD0; margin-top:8px;">
        © Right Horizons Wealth Management &nbsp;|&nbsp; Data via Yahoo Finance &nbsp;|&nbsp; For informational purposes only
    </div>
    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"🚨 App Error: {e}")
    import traceback
    st.code(traceback.format_exc())
