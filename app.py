import streamlit as st
import requests
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Global Equities App", layout="wide")

def format_data(value, prefix="", suffix="", decimals=2):
    if value is None or value == "N/A" or value == "" or str(value).lower() == "nan":
        return "N/A"
    if type(value) in [float, int]:
        return f"{prefix}{value:,.{decimals}f}{suffix}"
    return str(value)

st.title("🌎 Global Equities Research Dashboard")
st.write("Welcome to your personal stock screener!")

# --- UI CONTROL PANEL ---
ui_col1, ui_col2 = st.columns(2)

with ui_col1:
    ticker_symbol = st.text_input("Enter a Stock Ticker (e.g. AAPL or 3750.HK):", "AAPL").upper()
    
with ui_col2:
    timeframe_choice = st.selectbox("Select Chart Timeframe:", [
        "Intraday (Hourly intervals, past 2 Years Max)", 
        "Daily (1d intervals, past 5 Years)",          
        "Weekly (1wk intervals, past 5 Years)"
    ], index=1)

if st.button("Search Stock"):
    with st.spinner(f'Engaging engines for {ticker_symbol}...'):
        
        API_KEY = st.secrets["FINNHUB_KEY"]
        use_fallback = False
        
        # --- ENGINE 1: FINNHUB ---
        quote_url = f"https://finnhub.io/api/v1/quote?symbol={ticker_symbol}&token={API_KEY}"
        
        try:
            quote_data = requests.get(quote_url).json()
            if "error" in quote_data:
                use_fallback = True
            elif quote_data.get('c', 0) == 0:
                use_fallback = True
            else:
                metric_url = f"https://finnhub.io/api/v1/stock/metric?symbol={ticker_symbol}&metric=all&token={API_KEY}"
                metric_data = requests.get(metric_url).json()
                metrics = metric_data.get('metric', {})
                price = quote_data.get('c')  
                change_num = quote_data.get('d') 
                currency_symbol = "$" 
                
                trailing_pe = metrics.get('peTTM')
                forward_pe = metrics.get('peNormalizedAnnual')
                pb_ratio = metrics.get('pbAnnual')
                eps = metrics.get('epsTTM')
                net_margin = metrics.get('netMarginTTM') or metrics.get('netMarginAnnual')
                eps_growth = metrics.get('epsGrowthTTMYoy')
                rev_growth = metrics.get('revenueGrowthTTMYoy')
                roa = metrics.get('roaTTM')
                roe = metrics.get('roeTTM')
        except Exception as e:
            use_fallback = True
            
        # --- ENGINE 2: YFINANCE GLOBAL NINJA ---
        if use_fallback:
            try:
                stock = yf.Ticker(ticker_symbol)
                info = {}
                try: 
                    info = stock.info 
                except Exception:
                    pass
                
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                
                if price is None:
                    hist = stock.history(period="5d")
                    if not hist.empty:
                        price = float(hist['Close'].iloc[-1])
                        previous_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else price
                        change_num = price - previous_close
                else: 
                    previous_close = info.get('previousClose')
                    change_num = (price - previous_close) if previous_close else None

                currency_raw = info.get('currency', 'USD') if info else 'USD'
                currency_symbol = "HK$" if currency_raw == "HKD" else (currency_raw + " " if currency_raw != "USD" else "$")

                trailing_pe = info.get('trailingPE')
                forward_pe = info.get('forwardPE')
                pb_ratio = info.get('priceToBook')
                eps = info.get('trailingEps')
                net_margin = (info.get('profitMargins') * 100) if info.get('profitMargins') else None
                eps_growth = (info.get('earningsGrowth') * 100) if info.get('earningsGrowth') else None
                rev_growth = (info.get('revenueGrowth') * 100) if info.get('revenueGrowth') else None
                roa = (info.get('returnOnAssets') * 100) if info.get('returnOnAssets') else None
                roe = (info.get('returnOnEquity') * 100) if info.get('returnOnEquity') else None
                    
            except Exception as e:
                price = None 


        # --- DASHBOARD PAINTING ---
        if 'price' in locals() and price is not None:
            engine_used = "Yahoo Global Pipeline" if use_fallback else "Finnhub Pro Pipeline"
            
            st.subheader(f"{ticker_symbol}")
            st.metric(label="Current Price", 
                      value=format_data(price, prefix=currency_symbol), 
                      delta=format_data(change_num, prefix=currency_symbol))
            st.caption(f"✅ Route Success: {engine_used}")
            st.divider() 
            
            st.subheader("📊 Fundamental Master List")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown("**Valuations**")
                st.metric(label="Trailing P/E", value=format_data(trailing_pe))
                st.metric(label="Forward P/E", value=format_data(forward_pe))
                st.metric(label="P/B Ratio", value=format_data(pb_ratio))
            with col2:
                st.markdown("**Earnings & Margins**")
                st.metric(label="EPS (TTM)", value=format_data(eps, prefix=currency_symbol))
                st.metric(label="Net Profit Margin", value=format_data(net_margin, suffix="%"))
            with col3:
                st.markdown("**Growth (YoY)**")
                st.metric(label="EPS Growth", value=format_data(eps_growth, suffix="%"))
                st.metric(label="Revenue Growth", value=format_data(rev_growth, suffix="%"))
            with col4:
                st.markdown("**Health & Efficiency**")
                st.metric(label="ROA", value=format_data(roa, suffix="%"))
                st.metric(label="ROE", value=format_data(roe, suffix="%"))


        # --- 📈 ADVANCED TRADINGVIEW CHARTING 📈 ---
        st.write("---")
        st.subheader(f"🕯️ Interactive Candlestick Chart")
        
        if "Intraday" in timeframe_choice:
            c_period = "730d"  
            c_interval = "1h"
            ma_window = 20
        elif "Daily" in timeframe_choice:
            c_period = "5y"    
            c_interval = "1d"
            ma_window = 50 
        else:
            c_period = "5y"    
            c_interval = "1wk"
            ma_window = 50
            
        try:
            chart_stock = yf.Ticker(ticker_symbol)
            # Fetch data and safely order it just in case!
            history_data = chart_stock.history(period=c_period, interval=c_interval)
            
            if not history_data.empty:
                history_data = history_data.sort_index()
                
                # Math formula to create a Rolling Moving Average Line 
                history_data['SMA'] = history_data['Close'].rolling(window=ma_window).mean()
                
                # --- PRO FIX #1b: THE AVALANCHE PREVENTER ---
                # We put %Y back into the Hourly labels so duplicate month labels from previous 
                # years don't scramble Plotly's rendering engine!
                if c_interval == '1h':
                    clean_dates = history_data.index.strftime('%Y-%m-%d %H:%M')
                else:
                    clean_dates = history_data.index.strftime('%Y-%m-%d')
                
                fig = go.Figure()
                
                fig.add_trace(go.Candlestick(
                    x=clean_dates,
                    open=history_data['Open'],
                    high=history_data['High'],
                    low=history_data['Low'],
                    close=history_data['Close'],
                    name='Market Price',
                    increasing_line_color='#26a69a', 
                    decreasing_line_color='#ef5350'  
                ))
                
                fig.add_trace(go.Scatter(
                    x=clean_dates,
                    y=history_data['SMA'],
                    mode='lines',
                    line=dict(color='orange', width=2),
                    name=f'{ma_window} SMA',
                    hoverinfo='skip'
                ))
                
                fig.update_layout(
                    dragmode='pan', 
                    xaxis_rangeslider_visible=False,
                    margin=dict(l=20, r=40, t=20, b=20),
                    height=600,
                    hovermode="x unified",
                    yaxis=dict(showgrid=True, gridcolor='rgba(200,200,200, 0.2)', tickprefix=currency_symbol if 'currency_symbol' in locals() else "$", fixedrange=False),
                    xaxis=dict(
                        showgrid=False, 
                        type='category', 
                        nticks=10, 
                        fixedrange=False
                    ),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                
                st.plotly_chart(
                    fig, 
                    use_container_width=True, 
                    config={
                        'scrollZoom': True, 
                        'displayModeBar': True,
                        'modeBarButtonsToRemove': ['lasso2d', 'select2d']
                    }
                )
            else:
                st.warning(f"No history chart data available for this timeframe (Try selecting a shorter period).")
                
        except Exception as e:
            st.error(f"Chart Render Error: {e}")
