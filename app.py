import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import time

st.set_page_config(page_title="Family Office Hub", layout="wide")

# --- CUSTOM CSS: TO MASTERFULLY CONTROL THE FONTS & DESIGN! ---
st.markdown("""
    <style>
        .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; font-family: -apple-system, sans-serif; }
        .custom-table th { font-size: 11px; font-weight: 600; color: #888; border-bottom: 2px solid #555; padding: 10px; text-align: left; text-transform: uppercase; }
        .custom-table td { font-size: 19px; font-weight: 400; border-bottom: 1px solid #333; padding: 12px 10px; }
        .ticker-col { font-size: 26px !important; font-weight: 800; color: #4FA6FF; } /* Large blue tickers */
        .cat-heading { color: #fff; font-size: 24px; font-weight: bold; border-bottom: 2px solid #4FA6FF; padding-bottom: 8px; margin-bottom: 15px;}
    </style>
""", unsafe_allow_html=True)


st.title("💼 Family Office Command Center")
st.write("Track custom portfolios, rank holdings side-by-side, and hunt for market catalysts.")

# --- MODULE 1: THE MANUAL CATEGORY & WATCHLIST EDITOR ---
st.sidebar.header("📝 Custom Portfolio Editor")
st.sidebar.caption("Organize your book manually. Just type a new category to create a fresh group!")

# Preloaded data with custom headers defined directly by YOU
if "watchlist" not in st.session_state:
    st.session_state.watchlist = pd.DataFrame({
        "Category": ["Core Tech Holdings", "Core Tech Holdings", "High Growth / Volatile", "Global Exposure", "Legacy Finance", "Healthcare Targets"],
        "Ticker": ["AAPL", "MSFT", "TSLA", "3750.HK", "JPM", "UNH"]
    })

# Editable UI on sidebar
edited_df = st.sidebar.data_editor(
    st.session_state.watchlist,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True
)
st.session_state.watchlist = edited_df

# Parse user input cleanly
valid_rows = []
for index, row in edited_df.iterrows():
    cat = str(row['Category']).strip()
    tick = str(row['Ticker']).strip().upper()
    if tick != "" and tick != "NAN" and tick != "NONE":
        if cat == "" or cat == "NAN" or cat == "NONE":
            cat = "Uncategorized"
        valid_rows.append({"Category": cat, "Ticker": tick})

if not valid_rows:
    st.warning("Your watchlist is empty! Add categories and tickers in the sidebar.")
    st.stop()
    
st.write("---")

# --- MODULE 2: HYBRID API ENGINE ---
if st.button("🔄 Synchronize Book & Pull Wall Street Data", use_container_width=True):
    with st.spinner("Connecting to primary feeds & querying data streams..."):
        
        API_KEY = st.secrets["FINNHUB_KEY"]
        data_outputs = []
        progress_bar = st.progress(0)
        
        for idx, row in enumerate(valid_rows):
            cat = row["Category"]
            t = row["Ticker"]
            
            try:
                prof_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={t}&token={API_KEY}"
                quote_url = f"https://finnhub.io/api/v1/quote?symbol={t}&token={API_KEY}"
                
                prof_data = requests.get(prof_url).json()
                quote_data = requests.get(quote_url).json()
                
                if not prof_data or "error" in quote_data or quote_data.get('c', 0) == 0:
                    # YFINANCE HYBRID FALLBACK 
                    stock = yf.Ticker(t)
                    try:
                        info = stock.info 
                        price = info.get('currentPrice') or info.get('regularMarketPrice')
                        curr = info.get('currency', 'USD')
                        currency_sym = "HK$" if curr == "HKD" else "$"
                        
                        pe = info.get('trailingPE')
                        eps = info.get('trailingEps')
                        eps_growth = (info.get('earningsGrowth') * 100) if info.get('earningsGrowth') else None
                        rev_growth = (info.get('revenueGrowth') * 100) if info.get('revenueGrowth') else None
                        pb = info.get('priceToBook')
                    except Exception:
                        hist = stock.history(period="1d")
                        if not hist.empty:
                            price = float(hist['Close'].iloc[-1])
                            currency_sym = ""
                            pe, eps, eps_growth, rev_growth, pb = None, None, None, None, None
                        else:
                            raise Exception("Fail")
                else:
                    # FINNHUB PIPELINE 
                    metric_url = f"https://finnhub.io/api/v1/stock/metric?symbol={t}&metric=all&token={API_KEY}"
                    metrics_data = requests.get(metric_url).json().get('metric', {})
                    price = quote_data.get('c')
                    curr = prof_data.get('currency', 'USD')
                    currency_sym = "HK$" if curr == "HKD" else "$"
                    
                    pe = metrics_data.get('peTTM')
                    eps = metrics_data.get('epsTTM')
                    eps_growth = metrics_data.get('epsGrowthTTMYoy')
                    rev_growth = metrics_data.get('revenueGrowthTTMYoy')
                    pb = metrics_data.get('pbAnnual')
                
                data_outputs.append({
                    "Category": cat, "Ticker": t,
                    "Price": f"{currency_sym}{price:,.2f}" if price else "N/A",
                    "P/E": f"{pe:.1f}" if isinstance(pe, (int, float)) else "N/A",
                    "EPS": f"{currency_sym}{eps:.2f}" if isinstance(eps, (int, float)) else "N/A",
                    "EPS_Gro": f"{eps_growth:.1f}%" if isinstance(eps_growth, (int, float)) else "N/A",
                    "Rev_Gro": f"{rev_growth:.1f}%" if isinstance(rev_growth, (int, float)) else "N/A",
                    "PB": f"{pb:.1f}" if isinstance(pb, (int, float)) else "N/A"
                })
                
            except Exception as e:
                data_outputs.append({
                    "Category": cat, "Ticker": t, "Price": "ERROR",
                    "P/E": "-", "EPS": "-", "EPS_Gro": "-", "Rev_Gro": "-", "PB": "-"
                })
            
            progress_bar.progress((idx + 1) / len(valid_rows))
            time.sleep(0.3) 
            
        progress_bar.empty()
        st.session_state.master_df = pd.DataFrame(data_outputs)
        st.success(f"Dashboard synchronized! Synced {len(valid_rows)} target equities.")

# --- MODULE 3: THE HTML "PRO GRID" VIEWER ---
if 'master_df' in st.session_state:
    mdf = st.session_state.master_df
    unique_cats = []
    # Ensures categories stay in the exact order you arranged them!
    for cat in valid_rows:
        if cat["Category"] not in unique_cats:
            unique_cats.append(cat["Category"])
            
    # Draw a massive customized Grid! 
    for category in unique_cats:
        st.markdown(f"<div class='cat-heading'>{category}</div>", unsafe_allow_html=True)
        cat_df = mdf[mdf['Category'] == category]
        
        # We physically handwrite the CSS Grid in Python to maximize font design requests
        table_html = "<table class='custom-table'>"
        table_html += "<tr><th>Target Asset</th><th>Last Price</th><th>P/E Ratio (TTM)</th><th>Earnings (EPS)</th><th>EPS Growth</th><th>Rev Growth</th><th>P/B Ratio</th></tr>"
        
        for _, r in cat_df.iterrows():
            table_html += f"<tr>"
            table_html += f"<td class='ticker-col'>{r['Ticker']}</td>"
            table_html += f"<td>{r['Price']}</td>"
            table_html += f"<td>{r['P/E']}</td>"
            table_html += f"<td>{r['EPS']}</td>"
            
            # Simple formatting logic for colors if needed (Green vs red), kept neutral for readability here!
            table_html += f"<td>{r['EPS_Gro']}</td>"
            table_html += f"<td>{r['Rev_Gro']}</td>"
            table_html += f"<td>{r['PB']}</td>"
            table_html += "</tr>"
            
        table_html += "</table><br><br>" # Spacer between custom sections
        
        st.markdown(table_html, unsafe_allow_html=True)
