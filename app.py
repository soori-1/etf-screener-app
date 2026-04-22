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

if metric_col in plot_df.columns:
    plot_df[metric_col] = pd.to_numeric(plot_df[metric_col], errors='coerce')
else:
    plot_df[metric_col] = 0.0

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

    # MAGIC FIX: Extract the hidden math and force it into the text array safely
    try:
        computed_colors = fig.data[0].marker.colors
        # Safely map every single box (including Sector averages) to a clean text percentage
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

    # Injecting the new %{text} variable keeps the beautiful auto-scaling font engine!
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
