import streamlit as st
import requests

st.set_page_config(page_title="My Equities App", layout="centered")

st.title("📈 Equities Research Dashboard")
st.write("Welcome to your personal stock screener!")

ticker_symbol = st.text_input("Enter a Stock Ticker:", "AAPL").upper()

if st.button("Search Stock"):
    with st.spinner(f'Fetching real-time data for {ticker_symbol}...'):
        
        API_KEY = st.secrets["FINNHUB_KEY"]
        
        # 1. New pipelines! Asking Finnhub for the Quote (price) and Metric (PE, EPS)
        quote_url = f"https://finnhub.io/api/v1/quote?symbol={ticker_symbol}&token={API_KEY}"
        metric_url = f"https://finnhub.io/api/v1/stock/metric?symbol={ticker_symbol}&metric=all&token={API_KEY}"
        
        try:
            quote_data = requests.get(quote_url).json()
            metric_data = requests.get(metric_url).json()

            # --- BULLETPROOFING FOR FINNHUB ---
            if "error" in quote_data:
                st.error(f"Finnhub API Block Message: {quote_data['error']}")
            
            # The key 'c' stands for 'Current Price' in Finnhub
            elif 'c' in quote_data and quote_data['c'] > 0:
                
                # Prices and Change for the day
                price = quote_data['c']  
                change_num = quote_data['d'] # 'd' is the actual dollar change today
                
                # Grabbing the fundamental metrics
                metrics = metric_data.get('metric', {})
                trailing_pe = metrics.get('peTTM', 'N/A')
                pb_ratio = metrics.get('pbAnnual', 'N/A') 
                eps = metrics.get('epsTTM', 'N/A')

                st.subheader(f"Fundamental Data for {ticker_symbol}")
                
                # Creating 4 equal column spaces!
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(label="Current Price", value=f"${price}", delta=f"${change_num}")
                with col2:
                    st.metric(label="Trailing P/E", value=round(trailing_pe, 2) if type(trailing_pe) in [int, float] else trailing_pe)
                with col3:
                    st.metric(label="P/B Ratio", value=round(pb_ratio, 2) if type(pb_ratio) in [int, float] else pb_ratio)
                with col4:
                    st.metric(label="EPS (TTM)", value=f"${round(eps, 2)}" if type(eps) in [int, float] else eps)

                st.write("---")
                st.success("✅ SUCCESS! Connected to a bulletproof Free API that doesn't hold you hostage.")
            else:
                st.warning("No data found! Are you sure you spelled the Ticker symbol correctly?")
                
        except Exception as e:
            st.error(f"App broken: {e}")
