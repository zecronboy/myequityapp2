import streamlit as st
import yfinance as yf

st.set_page_config(page_title="My Equities App", layout="centered")

st.title("📈 Equities Research Dashboard")
st.write("Welcome to your personal stock screener!")

ticker_symbol = st.text_input("Enter a Stock Ticker:", "MSFT")

if st.button("Search Stock"):
    with st.spinner('Fetching real-time data...'):
        stock = yf.Ticker(ticker_symbol)
        info = stock.info

        price = info.get('currentPrice', 'N/A')
        volume = info.get('volume', 'N/A')
        eps = info.get('trailingEps', 'N/A')
        trailing_pe = info.get('trailingPE', 'N/A')
        
        st.subheader(f"Data for {ticker_symbol.upper()}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(label="Current Price", value=f"${price}")
        with col2:
            st.metric(label="Volume", value=f"{volume:,}" if type(volume) == int else volume)
        with col3:
            st.metric(label="EPS", value=f"${eps}")
        with col4:
            st.metric(label="Trailing P/E", value=trailing_pe)
            
        st.write("---")
        st.write("A fully functioning dashboard hosted on the web! Next we add all the rest of the fundamental data.")
