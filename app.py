import streamlit as st
import requests

st.set_page_config(page_title="My Equities App", layout="centered")

st.title("📈 Equities Research Dashboard")
st.write("Welcome to your personal stock screener!")

ticker_symbol = st.text_input("Enter a Stock Ticker:", "AAPL").upper()

if st.button("Search Stock"):
    with st.spinner(f'Fetching real-time data for {ticker_symbol}...'):
        
        API_KEY = st.secrets["FMP_KEY"]
        
        # 2. Knock on FMP's door using the most reliable 'Quote' pipeline!
        quote_url = f"https://financialmodelingprep.com/api/v3/quote/{ticker_symbol}?apikey={API_KEY}"
        
        try:
            # 3. Pull the data out of the URL 
            raw_data = requests.get(quote_url).json()

            # --- BULLETPROOFING THE ERROR ---
            # If FMP sends us a blocked message instead of stock data, let's display what it says!
            if type(raw_data) is dict and "Error Message" in raw_data:
                st.error(f"FMP API BLOCK MESSAGE: {raw_data['Error Message']}")
                st.info("Check your API Key in the settings to ensure it matches your real key, or verify your email.")
            
            # --- IF IT SUCCEEDS! ---
            elif len(raw_data) > 0:
                item = raw_data[0] # Grab the very first result safely 
                
                # Pluck out the fundamental gems!
                price = item.get('price', 'N/A')
                volume = item.get('volume', 'N/A')
                pe_ratio = item.get('pe', 'N/A')
                eps = item.get('eps', 'N/A')
                
                st.subheader(f"Fundamental Data for {ticker_symbol}")
                
                # Setup Dashboard View
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(label="Current Price", value=f"${price}")
                with col2:
                    st.metric(label="Avg Volume", value=f"{int(volume):,}" if type(volume) in [int, float] else volume)
                with col3:
                    st.metric(label="P/E Ratio", value=round(pe_ratio, 2) if type(pe_ratio) in [int, float] and pe_ratio is not None else "N/A")
                with col4:
                    st.metric(label="EPS", value=f"${round(eps, 2)}" if type(eps) in [int, float] and eps is not None else "N/A")

                st.write("---")
                st.success("✅ SUCCESS! Connected to FMP via a real Data API.")
            else:
                st.warning("No data found! Double-check the ticker symbol.")
                
        except Exception as e:
            st.error(f"App broken: {e}")
