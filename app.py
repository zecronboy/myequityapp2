import streamlit as st
import pandas as pd
import yfinance as yf
import time

st.set_page_config(page_title="Family Office Hub", layout="wide")

st.title("💼 Family Office Command Center")
st.write("Track holdings, compare sector metrics, and prepare for market events.")

# --- MODULE 1: THE WATCHLIST EDITOR ---
st.sidebar.header("📝 Watchlist Manager")
st.sidebar.write("Add or remove tickers. Press Enter to confirm, and use the trash can to delete.")

# We create a "temporary" database in the cloud's memory using session_state!
if "watchlist" not in st.session_state:
    st.session_state.watchlist = pd.DataFrame({
        "Ticker": ["AAPL", "MSFT", "TSLA", "3750.HK", "JPM", "UNH"]
    })

# This magical widget creates an editable spreadsheet right on your sidebar!
edited_df = st.sidebar.data_editor(
    st.session_state.watchlist,
    num_rows="dynamic",
    use_container_width=True
)
st.session_state.watchlist = edited_df

# Strip out empty rows or accidents
tickers = [str(t).upper().strip() for t in edited_df['Ticker'].tolist() if str(t).strip() != ""]

if not tickers:
    st.warning("Your watchlist is empty! Add a ticker in the sidebar.")
    st.stop()
    
st.write("---")

# --- MODULE 2: DATA SYNCHRONIZER ---
# We use a Sync Button so it doesn't accidentally spam APIs while you are still typing!
if st.button("🔄 Sync Market Data & Classify Industries", use_container_width=True):
    with st.spinner("Scouting global markets and running AI/Industry classification..."):
        
        data_rows = []
        progress_bar = st.progress(0)
        
        for idx, t in enumerate(tickers):
            try:
                # Ninja engine activating!
                stock = yf.Ticker(t)
                info = stock.info
                
                # Digging for Industry categorization! 
                sector = info.get('sector') or info.get('industry') or 'Unclassified / Other'
                price = info.get('currentPrice') or info.get('regularMarketPrice') or 0.0
                currency = info.get('currency', 'USD')
                pe = info.get('trailingPE')
                eps = info.get('trailingEps')
                eps_growth = info.get('earningsGrowth')
                rev_growth = info.get('revenueGrowth')
                pb = info.get('priceToBook')
                
                # Adding it neatly to a table format
                data_rows.append({
                    "Ticker": t,
                    "Sector": sector,
                    "Price": f"{price:,.2f} {currency}" if price else "N/A",
                    "P/E Ratio": round(pe, 2) if pe else None,
                    "EPS": f"{eps:,.2f} {currency}" if eps else None,
                    "EPS Growth": f"{eps_growth*100:.1f}%" if eps_growth else None,
                    "Rev Growth": f"{rev_growth*100:.1f}%" if rev_growth else None,
                    "P/B": round(pb, 2) if pb else None
                })
            except Exception as e:
                # Graceful Failure if it misses one ticker!
                data_rows.append({
                    "Ticker": t, "Sector": "Lookup Failed", "Price": "Error",
                    "P/E Ratio": None, "EPS": None, "EPS Growth": None,
                    "Rev Growth": None, "P/B": None
                })
            
            # Animate the progress bar so you know it hasn't crashed!
            progress_bar.progress((idx + 1) / len(tickers))
            time.sleep(0.5) # Gentle rate-limit pacing
            
        progress_bar.empty()
        
        # Save our master list into Pandas format!
        master_df = pd.DataFrame(data_rows)
        st.session_state.master_df = master_df
        st.success("Database Synced Successfully!")

# --- MODULE 3: INDUSTRY AUTO-GROUPER DISPLAY ---
if 'master_df' in st.session_state:
    mdf = st.session_state.master_df
    
    # AI logic to sort by sector group!
    unique_sectors = sorted(list(mdf['Sector'].unique()))
    
    for sector in unique_sectors:
        # Give every industry its own beautiful section!
        st.subheader(f"🏢 Industry/Sector: {sector}")
        
        # Filter the big dataframe into small industry packets
        sector_df = mdf[mdf['Sector'] == sector].drop(columns=['Sector'])
        
        st.dataframe(
            sector_df, 
            use_container_width=True, 
            hide_index=True # Hides ugly internal database ID numbers!
        )
