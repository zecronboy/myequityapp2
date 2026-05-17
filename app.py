import streamlit as st
import requests
import yfinance as yf

st.set_page_config(page_title="My Equities App", layout="wide")

def format_data(value, prefix="", suffix="", decimals=2):
    if value is None or value == "N/A" or value == "" or str(value).lower() == "nan":
        return "N/A"
    if type(value) in [float, int]:
        return f"{prefix}{value:,.{decimals}f}{suffix}"
    return str(value)

st.title("🌎 Global Equities Research Dashboard")
st.write("Welcome to your personal stock screener!")

ticker_symbol = st.text_input("Enter a Stock Ticker (e.g. AAPL or 3750.HK):", "AAPL").upper()

if st.button("Search Stock"):
    with st.spinner(f'Engaging engines for {ticker_symbol}...'):
        
        API_KEY = st.secrets["FINNHUB_KEY"]
        use_fallback = False
        
        # --- ENGINE 1: FINNHUB (MAIN) ---
        quote_url = f"https://finnhub.io/api/v1/quote?symbol={ticker_symbol}&token={API_KEY}"
        
        try:
            quote_data = requests.get(quote_url).json()
            
            if "error" in quote_data:
                st.warning(f"Finnhub Blocked: '{quote_data['error']}'... Switching to Hybrid Fallback 🚀")
                use_fallback = True
                
            elif quote_data.get('c', 0) == 0:
                st.warning("Empty data. Searching Global Fallback Engine... 🚀")
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
            st.error("Engine 1 failed completely.")
            use_fallback = True
            
        # --- ENGINE 2: YFINANCE (THE HUMAN DISGUISE) ---
        if use_fallback:
            try:
                # 1. Open a Custom Web Session
                session = requests.Session()
                # 2. Tell Yahoo we are an ordinary Windows user running Google Chrome 🥸
                session.headers.update(
                    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
                )
                
                # 3. Ask for the data using our disguise
                stock = yf.Ticker(ticker_symbol, session=session)
                info = stock.info
                
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                
                if price is None:
                    st.error("Global Engine failed too: Ticker might not exist on Yahoo Finance.")
                else:
                    previous_close = info.get('previousClose')
                    change_num = (price - previous_close) if previous_close else None
                    
                    currency_raw = info.get('currency', 'USD')
                    # Make Asian/Euro currencies display nicely!
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
                st.error(f"Global Fallback blocked. Even the disguise failed! Reason: {e}")
                price = None 


        # --- THE MAGIC DISPLAY WIDGETS --- 
        if 'price' in locals() and price is not None:
            engine_used = "Yahoo Finance Global Fallback (Chrome Bypass)" if use_fallback else "Finnhub Official Data"
            
            st.subheader(f"{ticker_symbol}")
            st.metric(label="Current Price", 
                      value=format_data(price, prefix=currency_symbol), 
                      delta=format_data(change_num, prefix=currency_symbol))
            
            st.caption(f"✅ Data routed via: **{engine_used}**")
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

            st.write("---")
