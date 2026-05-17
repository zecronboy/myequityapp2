import streamlit as st
import requests

st.set_page_config(page_title="My Equities App", layout="centered")

st.title("📈 Equities Research Dashboard")
st.write("Welcome to your personal stock screener!")

ticker_symbol = st.text_input("Enter a Stock Ticker:", "MSFT").upper()

if st.button("Search Stock"):
    with st.spinner(f'Fetching real-time data for {ticker_symbol}...'):
        
        # 1. We reach securely into your Streamlit vault for your FMP API Key!
        API_KEY = st.secrets["FMP_KEY"]
        
        # 2. Go knock on FMP's door (Direct API Pipeline)
        # Getting Price and Volume...
        profile_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker_symbol}?apikey={API_KEY}"
        # Getting PE Ratio, EPS, PB Ratio...
        metrics_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker_symbol}?apikey={API_KEY}"

        # Fetch JSON safely 
        try:
            profile_data = requests.get(profile_url).json()
            metrics_data = requests.get(metrics_url).json()

            if profile_data and metrics_data:
                # Pluck out the fundamental gems!
                price = profile_data[0].get('price', 'N/A')
                volume = profile_data[0].get('volAvg', 'N/A')
                
                trailing_pe = metrics_data[0].get('peRatioTTM', 'N/A')
                pb_ratio = metrics_data[0].get('pbRatioTTM', 'N/A')
                eps = metrics_data[0].get('netIncomePerShareTTM', 'N/A')
                
                st.subheader(f"Fundamental Data for {ticker_symbol}")
                
                # Setup Dashboard View
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric(label="Current Price", value=f"${price}")
                with col2:
                    st.metric(label="Avg Volume", value=f"{int(volume):,}" if type(volume) in [int, float] else volume)
                with col3:
                    st.metric(label="Trailing P/E", value=round(trailing_pe, 2) if type(trailing_pe) in [int, float] else trailing_pe)
                with col4:
                    st.metric(label="P/B Ratio", value=round(pb_ratio, 2) if type(pb_ratio) in [int, float] else pb_ratio)
                with col5:
                    st.metric(label="Trailing EPS", value=f"${round(eps, 2)}" if type(eps) in [int, float] else eps)

                st.write("---")
                st.success("✅ Dashboard successfully upgraded from scrapers to Official Data API pipelines.")
            else:
                st.error("No data found! Double-check the ticker symbol.")
                
        except Exception as e:
            st.error(f"Something broke communicating with our Data pipeline: {e}")
