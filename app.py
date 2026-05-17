import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import time

st.set_page_config(page_title="Family Office Hub", layout="wide")

st.title("💼 Family Office Command Center")
st.write("Track holdings, compare sector metrics, and prepare for market events.")

# --- MODULE 1: THE WATCHLIST EDITOR ---
st.sidebar.header("📝 Watchlist Manager")
st.sidebar.write("Type a ticker below, press Enter. Select a row and click Delete to remove.")

# Create database in session_state!
if "watchlist" not in st.session_state:
    st.session_state.watchlist = pd.DataFrame({
        "Ticker": ["AAPL", "MSFT", "TSLA", "3750.HK", "JPM", "UNH"]
    })

# The Editable Widget
edited_df = st.sidebar.data_editor(
    st.session_state.watchlist,
    num_rows="dynamic",
    use_container_width=True
)
st.session_state.watchlist = edited_df

# Safe filter: Clear blanks or empty dropdown 'None' clicks
tickers = [str(t).upper().strip() for t in edited_df['Ticker'].tolist() if str(t).upper().strip() not in ["", "NONE", "NAN"]]

if not tickers:
    st.warning("Your watchlist is empty! Add a ticker in the sidebar.")
    st.stop()
    
st.write("---")

# --- MODULE 2: BULLETPROOF SYNCHRONIZER (Hybrid Pipeline!) ---
if st.button("🔄 Sync Market Data & Classify Industries", use_container_width=True):
    with st.spinner("Scouting global markets and pulling metrics via Hybrid Pipeline..."):
        
        API_KEY = st.secrets["FINNHUB_KEY"]
        data_rows = []
        progress_bar = st.progress(0)
        
        for idx, t in enumerate(tickers):
            try:
                # Set up Finnhub calls
                prof_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={t}&token={API_KEY}"
                quote_url = f"https://finnhub.io/api/v1/quote?symbol={t}&token={API_KEY}"
                
                prof_data = requests.get(prof_url).json()
                quote_data = requests.get(quote_url).json()
                
                # Check if Finnhub failed (Intl. stock, block, or invalid)
                if not prof_data or "error" in quote_data or quote_data.get('c', 0) == 0:
                    
                    # ⚠️ YFINANCE FALLBACK PIPELINE ⚠️
                    stock = yf.Ticker(t)
                    try:
                        # Asking for deep fundamental metrics...
                        info = stock.info 
                        sector = info.get('sector') or info.get('industry') or "International / Hybrid Fallback"
                        price = info.get('currentPrice') or info.get('regularMarketPrice')
                        curr = info.get('currency', 'USD')
                        currency_sym = "HK$" if curr == "HKD" else "$"
                        
                        pe = info.get('trailingPE')
                        eps = info.get('trailingEps')
                        eps_growth = (info.get('earningsGrowth') * 100) if info.get('earningsGrowth') else None
                        rev_growth = (info.get('revenueGrowth') * 100) if info.get('revenueGrowth') else None
                        pb = info.get('priceToBook')
                        
                    except Exception:
                        # 🚨 TAPE DATA LAST-RESORT SURVIVAL ENGINE 🚨
                        hist = stock.history(period="1d")
                        if not hist.empty:
                            price = float(hist['Close'].iloc[-1])
                            currency_sym, sector = "", "International / Unclassified"
                            pe, eps, eps_growth, rev_growth, pb = None, None, None, None, None
                        else:
                            raise Exception("Failed All Routing")

                else:
                    # ✅ FINNHUB PRIMARY PIPELINE ✅
                    metric_url = f"https://finnhub.io/api/v1/stock/metric?symbol={t}&metric=all&token={API_KEY}"
                    metrics_data = requests.get(metric_url).json().get('metric', {})
                    
                    sector = prof_data.get('finnhubIndustry') or "US Equity / Diversified"
                    price = quote_data.get('c')
                    
                    curr = prof_data.get('currency', 'USD')
                    currency_sym = "HK$" if curr == "HKD" else "$"
                    
                    pe = metrics_data.get('peTTM')
                    eps = metrics_data.get('epsTTM')
                    eps_growth = metrics_data.get('epsGrowthTTMYoy')
                    rev_growth = metrics_data.get('revenueGrowthTTMYoy')
                    pb = metrics_data.get('pbAnnual')
                
                # Format to table string immediately!
                data_rows.append({
                    "Ticker": t,
                    "Sector": sector,
                    "Price": f"{currency_sym}{price:,.2f}" if price else "N/A",
                    "P/E": f"{pe:.1f}" if isinstance(pe, (int, float)) else "N/A",
                    "EPS": f"{currency_sym}{eps:.2f}" if isinstance(eps, (int, float)) else "N/A",
                    "EPS Gro %": f"{eps_growth:.1f}%" if isinstance(eps_growth, (int, float)) else "N/A",
                    "Rev Gro %": f"{rev_growth:.1f}%" if isinstance(rev_growth, (int, float)) else "N/A",
                    "P/B": f"{pb:.1f}" if isinstance(pb, (int, float)) else "N/A"
                })
                
            except Exception as e:
                # If everything shatters (Like an absolutely fake ticker string)
                data_rows.append({
                    "Ticker": t, "Sector": "⚠️ Sync Failed", "Price": "Error",
                    "P/E": "N/A", "EPS": "N/A", "EPS Gro %": "N/A", "Rev Gro %": "N/A", "P/B": "N/A"
                })
            
            # Show process
            progress_bar.progress((idx + 1) / len(tickers))
            time.sleep(0.3) 
            
        progress_bar.empty()
        st.session_state.master_df = pd.DataFrame(data_rows)
        st.success(f"Successfully processed {len(tickers)} targets. AI Auto-Grouping complete.")

# --- MODULE 3: THE DASHBOARD GRID DISPLAY ---
if 'master_df' in st.session_state:
    mdf = st.session_state.master_df
    
    unique_sectors = sorted(list(mdf['Sector'].unique()))
    
    for sector in unique_sectors:
        st.subheader(f"🏢 Industry Sub-Grid: {sector}")
        sector_df = mdf[mdf['Sector'] == sector].drop(columns=['Sector'])
        
        st.dataframe(
            sector_df, 
            use_container_width=True, 
            hide_index=True 
        )
