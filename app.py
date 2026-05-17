import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import time
from datetime import datetime

st.set_page_config(page_title="Family Office Hub", layout="wide")

# --- CUSTOM CSS: Fixed Header Visibility + Expanding Columns ---
st.markdown("""
    <style>
        .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; font-family: -apple-system, sans-serif; }
        .custom-table th { font-size: 11px; font-weight: 600; color: #888; border-bottom: 2px solid #555; padding: 10px; text-align: left; text-transform: uppercase; }
        .custom-table td { font-size: 16px; font-weight: 400; border-bottom: 1px solid #ddd; padding: 12px 10px; }
        .ticker-col { font-size: 24px !important; font-weight: 800; color: #4FA6FF; } 
        /* The header 'color: inherit;' prevents the white-text bug on light mode themes! */
        .cat-heading { color: inherit; font-size: 24px; font-weight: bold; border-bottom: 2px solid #4FA6FF; padding-bottom: 8px; margin-bottom: 15px;}
        
        .alert-drama { color: #d93025; font-weight: 700; background-color: #fce8e6; padding: 3px 8px; border-radius: 4px; font-size: 13px;}
        .alert-quiet { color: #1e8e3e; font-weight: 600; font-size: 14px;}
        .earn-date { font-family: monospace; color: #555;}
    </style>
""", unsafe_allow_html=True)


st.title("💼 Family Office Command Center")
st.write("Track custom portfolios, analyze sentiment catalysts, and prepare for earnings events.")

# --- MODULE 1: CUSTOM PORTFOLIO EDITOR ---
st.sidebar.header("📝 Custom Portfolio Editor")
st.sidebar.caption("Organize your book manually. Just type a new category to create a fresh group!")

if "watchlist" not in st.session_state:
    st.session_state.watchlist = pd.DataFrame({
        "Category": ["Magnificent 7", "Magnificent 7", "Legacy Tech", "Energy Sector", "Global Equities"],
        "Ticker": ["AAPL", "TSLA", "MSFT", "XOM", "3750.HK"] # Changed out standard for an oil co. to test!
    })

edited_df = st.sidebar.data_editor(
    st.session_state.watchlist,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True
)
st.session_state.watchlist = edited_df

valid_rows = []
for index, row in edited_df.iterrows():
    cat = str(row['Category']).strip()
    tick = str(row['Ticker']).strip().upper()
    if tick not in ["", "NAN", "NONE"]:
        if cat in ["", "NAN", "NONE"]: cat = "Uncategorized"
        valid_rows.append({"Category": cat, "Ticker": tick})

if not valid_rows:
    st.warning("Your watchlist is empty! Add categories and tickers in the sidebar.")
    st.stop()
    
st.write("---")

# --- TRIGGER WORD LIBRARY FOR AI SCRAPING ---
# We are hunting for these exact words in recent news releases
DRAMA_WORDS = ["buyback", "dilution", "lawsuit", "investigation", "resigns", "subpoena", "scandal", "acquisition", "layoffs", "antitrust"]

# --- MODULE 2: HYBRID ENGINE + SCRAPER ---
if st.button("🔄 Sync Live Quotes & Scout For Media Catalysts", use_container_width=True):
    with st.spinner("Connecting to primary feeds & launching web-scrapers for media sentiment..."):
        
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
                
                # We spin up the Yahoo scraper for Earnings & News Drama either way!
                stock = yf.Ticker(t)
                
                # --- SCRAPE MODULE 1: Next Earnings Dates ---
                earn_ts = stock.info.get('earningsTimestamp') if hasattr(stock, 'info') else None
                if earn_ts:
                    earn_date_str = datetime.utcfromtimestamp(earn_ts).strftime('%b %d, %Y')
                else:
                    earn_date_str = "Unknown"
                    
                # --- SCRAPE MODULE 2: Headline Sentiment Mining ---
                try:
                    news_data = stock.news
                    recent_headlines = [n.get('title', '') for n in news_data] if news_data else []
                    
                    found_drama = []
                    for hl in recent_headlines:
                        for word in DRAMA_WORDS:
                            if word.lower() in hl.lower() and word.title() not in found_drama:
                                found_drama.append(word.title())
                                
                    if found_drama:
                        # Formats beautiful warning boxes 
                        drama_alert = f"<span class='alert-drama'>🚨 Alerts: {', '.join(found_drama)}</span>"
                    else:
                        drama_alert = f"<span class='alert-quiet'>✅ Routine News</span>"
                except Exception:
                    drama_alert = "<span style='color:grey; font-size: 13px;'>No News Found</span>"


                # Check routing condition 
                if not prof_data or "error" in quote_data or quote_data.get('c', 0) == 0:
                    try:
                        info = stock.info 
                        price = info.get('currentPrice') or info.get('regularMarketPrice')
                        curr = info.get('currency', 'USD')
                        currency_sym = "HK$" if curr == "HKD" else ("£" if curr == "GBP" else "$")
                        
                        pe = info.get('trailingPE')
                        eps = info.get('trailingEps')
                        eps_growth = (info.get('earningsGrowth') * 100) if info.get('earningsGrowth') else None
                        rev_growth = (info.get('revenueGrowth') * 100) if info.get('revenueGrowth') else None
                    except Exception:
                        hist = stock.history(period="1d")
                        if not hist.empty:
                            price = float(hist['Close'].iloc[-1])
                            currency_sym, pe, eps, eps_growth, rev_growth = "", None, None, None, None
                        else:
                            raise Exception("Fail")
                else:
                    metric_url = f"https://finnhub.io/api/v1/stock/metric?symbol={t}&metric=all&token={API_KEY}"
                    metrics_data = requests.get(metric_url).json().get('metric', {})
                    price = quote_data.get('c')
                    curr = prof_data.get('currency', 'USD')
                    currency_sym = "HK$" if curr == "HKD" else ("£" if curr == "GBP" else "$")
                    
                    pe = metrics_data.get('peTTM')
                    eps = metrics_data.get('epsTTM')
                    eps_growth = metrics_data.get('epsGrowthTTMYoy')
                    rev_growth = metrics_data.get('revenueGrowthTTMYoy')
                
                # Combine Everything!
                data_outputs.append({
                    "Category": cat, "Ticker": t,
                    "Price": f"{currency_sym}{price:,.2f}" if price else "N/A",
                    "P/E": f"{pe:.1f}" if isinstance(pe, (int, float)) else "N/A",
                    "EPS": f"{currency_sym}{eps:.2f}" if isinstance(eps, (int, float)) else "N/A",
                    "EPS_Gro": f"{eps_growth:.1f}%" if isinstance(eps_growth, (int, float)) else "N/A",
                    "Rev_Gro": f"{rev_growth:.1f}%" if isinstance(rev_growth, (int, float)) else "N/A",
                    "Earnings": f"<span class='earn-date'>{earn_date_str}</span>",
                    "Sentiment": drama_alert
                })
                
            except Exception as e:
                data_outputs.append({
                    "Category": cat, "Ticker": t, "Price": "ERROR",
                    "P/E": "-", "EPS": "-", "EPS_Gro": "-", "Rev_Gro": "-", "Earnings": "-", "Sentiment": "API Down"
                })
            
            progress_bar.progress((idx + 1) / len(valid_rows))
            time.sleep(0.3) 
            
        progress_bar.empty()
        st.session_state.master_df = pd.DataFrame(data_outputs)
        st.success(f"Dashboard synchronized! Event Calendars & Scrapers updated {len(valid_rows)} positions.")

# --- MODULE 3: THE WIDENED PRO GRID VIEWER ---
if 'master_df' in st.session_state:
    mdf = st.session_state.master_df
    unique_cats = []
    for cat in valid_rows:
        if cat["Category"] not in unique_cats:
            unique_cats.append(cat["Category"])
            
    for category in unique_cats:
        st.markdown(f"<div class='cat-heading'>{category}</div>", unsafe_allow_html=True)
        cat_df = mdf[mdf['Category'] == category]
        
        # New Expanded HTML Headers matching the layout
        table_html = "<table class='custom-table'>"
        table_html += "<tr><th>Target Asset</th><th>Last Price</th><th>P/E (TTM)</th><th>EPS</th><th>EPS Gro</th><th>Rev Gro</th><th>Upcm. Earnings</th><th>Recent Media Mentions</th></tr>"
        
        for _, r in cat_df.iterrows():
            table_html += f"<tr>"
            table_html += f"<td class='ticker-col'>{r['Ticker']}</td>"
            table_html += f"<td>{r['Price']}</td>"
            table_html += f"<td>{r['P/E']}</td>"
            table_html += f"<td>{r['EPS']}</td>"
            table_html += f"<td>{r['EPS_Gro']}</td>"
            table_html += f"<td>{r['Rev_Gro']}</td>"
            
            # The Event / Date Injection Columns
            table_html += f"<td>{r['Earnings']}</td>"
            table_html += f"<td>{r['Sentiment']}</td>"
            table_html += "</tr>"
            
        table_html += "</table><br><br>" 
        st.markdown(table_html, unsafe_allow_html=True)
