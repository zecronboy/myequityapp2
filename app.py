import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import time
from datetime import datetime

st.set_page_config(page_title="Family Office Hub", layout="wide")

# --- UI STYLING MASTER TEMPLATE (Upgraded Sidebar Sizes & New Grids!) ---
st.markdown("""
    <style>
        /* Increase the Font Size of the Sidebar Editable Watchlist Spreadsheet */
        div[data-testid="stSidebar"] [data-testid="stDataFrame"] {
            font-size: 14px !important;
            zoom: 1.05;
        }

        /* Financial Data Custom Table CSS */
        .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; font-family: -apple-system, sans-serif; }
        .custom-table th { font-size: 11px; font-weight: 600; color: #7f8c8d; border-bottom: 2px solid #bdc3c7; padding: 10px; text-align: left; text-transform: uppercase; line-height: 1.3;}
        .custom-table td { font-size: 14px; font-weight: 400; border-bottom: 1px solid #e0e0e0; padding: 12px 10px; line-height: 1.5; vertical-align: middle;}
        
        /* The Assets! */
        .ticker-col { font-size: 20px !important; font-weight: 800; color: #4FA6FF; } 
        .cat-heading { color: inherit; font-size: 26px; font-weight: bold; border-bottom: 3px solid #4FA6FF; padding-bottom: 6px; margin-bottom: 15px;}
        
        /* AI Keyword Coloring */
        .alert-drama { color: #d93025; font-weight: 700; background-color: #fce8e6; padding: 3px 6px; border-radius: 4px; font-size: 13px;}
        .alert-quiet { color: #1e8e3e; font-weight: 600; font-size: 13px;}
        
        /* Specialized Formats */
        .up-move { color: #1e8e3e; font-weight: 700; font-size: 13px; }
        .dn-move { color: #d93025; font-weight: 700; font-size: 13px; }
        .earn-date { font-family: monospace; color: #2c3e50; font-size: 14px;}
        .earn-past { font-family: monospace; color: #e74c3c; font-size: 13px; font-weight: 600; background: #fadbd8; padding: 2px 4px; border-radius: 4px; margin-left: 4px;}
        .meta-lbl { font-size:12px; color: #7f8c8d; font-weight:bold; }
    </style>
""", unsafe_allow_html=True)

# Math formatter specifically for trillion / billion / million scales (e.g. Market Cap)
def format_large_currency(val):
    if not val or pd.isna(val) or val == 'N/A' or float(val) == 0: return "N/A"
    num = float(val)
    if num >= 1e12: return f"{num/1e12:.2f}T"
    elif num >= 1e9: return f"{num/1e9:.2f}B"
    elif num >= 1e6: return f"{num/1e6:.2f}M"
    else: return f"{num:,.0f}"


st.title("💼 Family Office Command Center")
st.write("Track institutional parameters, analyze forward sentiment catalogs, and predict market events.")

# --- MODULE 1: THE MANUAL CATEGORY & WATCHLIST EDITOR ---
st.sidebar.header("📝 Book Ledger")
st.sidebar.caption("Organize targets visually. Tap table cells directly to make edits.")

if "watchlist" not in st.session_state:
    st.session_state.watchlist = pd.DataFrame({
        "Category": ["Artificial Intelligence", "Artificial Intelligence", "Fintech Innovation", "Industrial Value", "Commodities / Def."],
        "Ticker": ["NVDA", "AAPL", "SQ", "GE", "XOM"]
    })

edited_df = st.sidebar.data_editor(
    st.session_state.watchlist, num_rows="dynamic", use_container_width=True, hide_index=True
)
st.session_state.watchlist = edited_df

valid_rows = []
for _, row in edited_df.iterrows():
    cat = str(row['Category']).strip()
    tick = str(row['Ticker']).strip().upper()
    if tick not in ["", "NAN", "NONE"]:
        if cat in ["", "NAN", "NONE"]: cat = "Core Holdings"
        valid_rows.append({"Category": cat, "Ticker": tick})

if not valid_rows:
    st.warning("Empty Database. Insert Assets onto the Left Sidebar pane."); st.stop()
st.write("---")

DRAMA_WORDS = ["buyback", "dilution", "lawsuit", "investigation", "subpoena", "scandal", "acquisition", "layoffs", "merger", "bankruptcy"]

# --- MODULE 2: ULTRA-DENSE INSTITUTIONAL PIPELINES ---
if st.button("🔄 Command: Sync High-Density Fundamental Matrix", use_container_width=True):
    with st.spinner("Executing broad API pulls & financial calendar reconciliations..."):
        
        API_KEY = st.secrets["FINNHUB_KEY"]
        data_outputs = []
        progress_bar = st.progress(0)
        
        for idx, row in enumerate(valid_rows):
            cat, t = row["Category"], row["Ticker"]
            try:
                prof_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={t}&token={API_KEY}"
                quote_url = f"https://finnhub.io/api/v1/quote?symbol={t}&token={API_KEY}"
                earn_url = f"https://finnhub.io/api/v1/stock/earnings?symbol={t}&token={API_KEY}" # EPS SURPRISES 
                
                prof_data, quote_data = requests.get(prof_url).json(), requests.get(quote_url).json()
                earn_json = requests.get(earn_url).json() 

                stock = yf.Ticker(t)
                yf_info = stock.info 
                
                # ------ MARKET DATA CALCULATION PHASE ------ 
                # 1. Prices and Deltas
                price, prev_close = quote_data.get('c'), quote_data.get('pc')
                
                # Hybrid failsafe 
                if price is None or price == 0 or "error" in quote_data: 
                    price, prev_close = yf_info.get('currentPrice') or yf_info.get('regularMarketPrice'), yf_info.get('previousClose')
                
                delta_str = ""
                if price and prev_close:
                    move, pct_move = price - prev_close, ((price - prev_close)/prev_close) * 100
                    icon, m_cls = ("▲", "up-move") if move > 0 else ("▼", "dn-move")
                    delta_str = f"<br><span class='{m_cls}'>{icon} {abs(move):.2f} ({move/prev_close * 100:+.2f}%)</span>"

                # 2. Currency Setup & Formatters 
                currency_raw = yf_info.get('currency', 'USD')
                currency_sym = "$" if currency_raw in ['USD', 'CAD'] else ("£" if currency_raw == "GBP" else "HK$")
                price_f = f"<strong>{currency_sym}{price:,.2f}</strong>{delta_str}" if price else "N/A"
                
                # 3. Market Cap Fetcher 
                mcap_raw = yf_info.get('marketCap') or (prof_data.get('marketCapitalization', 0) * 1000000)
                mcap = f"<strong>{currency_sym}{format_large_currency(mcap_raw)}</strong>"
                
                # 4. Multi-PE Valuations 
                metric_url = f"https://finnhub.io/api/v1/stock/metric?symbol={t}&metric=all&token={API_KEY}"
                metrics = requests.get(metric_url).json().get('metric', {})
                pe_ttm = metrics.get('peTTM', yf_info.get('trailingPE'))
                pe_fwd = yf_info.get('forwardPE', metrics.get('peNormalizedAnnual'))
                pe_combined = f"<span class='meta-lbl'>TTM:</span> {f'{pe_ttm:.1f}' if isinstance(pe_ttm, float) else '-'}<br>" \
                              f"<span class='meta-lbl'>FWD:</span> {f'{pe_fwd:.1f}' if isinstance(pe_fwd, float) else '-'}"
                              
                # 5. Elite EPS Engine (Grabbing Past actuals vs current actual vs surprises)
                eps_latest_v, eps_prev_v, eps_diff = None, None, None 
                
                if isinstance(earn_json, list) and len(earn_json) > 0:
                    eps_latest_v, eps_diff = earn_json[0].get('actual'), earn_json[0].get('surprisePercent')
                    if len(earn_json) > 1:
                        eps_prev_v = earn_json[1].get('actual')
                
                if eps_latest_v:
                    diff_cls, s_pref = ("up-move", "Beat by") if (eps_diff and eps_diff >= 0) else ("dn-move", "Missed")
                    eps_comp = f"<span class='meta-lbl'>Q(0):</span> <strong>${eps_latest_v:.2f}</strong> <span class='{diff_cls}' style='font-size:12px;'>( {s_pref} {abs(eps_diff):.1f}% )</span><br>" if eps_diff else f"<span class='meta-lbl'>Latest Q:</span> {eps_latest_v}<br>"
                    eps_comp += f"<span class='meta-lbl' style='font-size:11px'>Q(-1): ${eps_prev_v:.2f}</span>" if eps_prev_v else ""
                else: 
                    eps_comp = "-" # If the stock (Intl etc.) has no EPS surprise record available free!

                # 6. Advanced Revenue Traces 
                tot_rev = format_large_currency(yf_info.get('totalRevenue'))
                rev_yoy = metrics.get('revenueGrowthTTMYoy') or yf_info.get('revenueGrowth', 0)*100
                rev_qoq = metrics.get('revenueGrowthQuarterlyYoy') or yf_info.get('quarterlyRevenueGrowth', 0)*100 

                rev_comp = f"<span class='meta-lbl'>Gross: </span>{currency_sym}{tot_rev}<br>" if tot_rev != "N/A" else "Data Rstrct<br>"
                rev_comp += f"<span class='meta-lbl'>Y/Y:</span> {f'{rev_yoy:.1f}%' if rev_yoy else '-'} <span style='color:grey'>|</span> " \
                            f"<span class='meta-lbl'>Q/Q:</span> {f'{rev_qoq:.1f}%' if rev_qoq else '-'}"

                # 7. Calendars with Event Marking! 
                earn_ts = yf_info.get('earningsTimestamp') 
                if earn_ts:
                    earn_dt = datetime.utcfromtimestamp(earn_ts)
                    is_past = earn_dt < datetime.utcnow()
                    status_lbl = "<span class='earn-past'>PAST</span>" if is_past else ""
                    earn_date_str = f"<span class='earn-date'>{earn_dt.strftime('%b %d, %Y')}</span><br>{status_lbl}"
                else: earn_date_str = "<span class='meta-lbl'>Unlisted</span>"

                # 8. Sentiments Scraping Engine 
                try:
                    news_data = stock.news
                    found_drama = list(set([word.title() for h in [n.get('title', '').lower() for n in news_data] for word in DRAMA_WORDS if word in h])) if news_data else []
                    drama_alert = f"<span class='alert-drama'>🚨: {', '.join(found_drama)}</span>" if found_drama else f"<span class='alert-quiet'>✅ Baseline Hype</span>"
                except: drama_alert = "Unknown"
                
                # --- SAVING COMPRESSED MASTER DICTIONARY --- 
                data_outputs.append({
                    "Category": cat, "Ticker": t, "MktCap": mcap,
                    "PriceBox": price_f, "PEBox": pe_combined,
                    "EPSBox": eps_comp, "RevBox": rev_comp,
                    "Earnings": earn_date_str, "Sentiment": drama_alert
                })
                
            except Exception as e: # Full bypass string failure safely  
                data_outputs.append({ "Category": cat, "Ticker": t, "MktCap": "ERR", "PriceBox": "Route Error", "PEBox": "-", "EPSBox": "-", "RevBox": "-", "Earnings": "-", "Sentiment": "-"})
            
            progress_bar.progress((idx + 1) / len(valid_rows))
            time.sleep(0.4) 
            
        progress_bar.empty(); st.session_state.master_df = pd.DataFrame(data_outputs)
        st.success(f"Dashboard synchronized! Acquired dense tracking nodes across {len(valid_rows)} Assets.")


# --- MODULE 3: THE HTML "PRO GRID" VIEWER ---
if 'master_df' in st.session_state:
    mdf = st.session_state.master_df
    
    unique_cats = []
    for row in valid_rows:
        if row["Category"] not in unique_cats: unique_cats.append(row["Category"])
            
    for category in unique_cats:
        st.markdown(f"<div class='cat-heading'>{category}</div>", unsafe_allow_html=True)
        cat_df = mdf[mdf['Category'] == category]
        
        # New Expanded Dense HTML Headers layout (Mkt Cap #1 metric slot)
        table_html = "<table class='custom-table'>"
        table_html += "<tr><th style='width: 10%'>Asset Class</th><th style='width: 9%'>Mkt Cap</th><th>Price Action & Delta</th><th style='width: 13%'>P/E (TTM/FWD)</th><th style='width: 18%'>E.P.S & WallSt Hit</th><th>Gross Rev Trajectory</th><th style='width: 13%'>Catalyst<br>(Earning Dt.)</th><th>A.I Headline Sentiment</th></tr>"
        
        for _, r in cat_df.iterrows():
            table_html += f"<tr>"
            table_html += f"<td class='ticker-col'>{r['Ticker']}</td>"
            table_html += f"<td>{r['MktCap']}</td>"
            table_html += f"<td>{r['PriceBox']}</td>"
            table_html += f"<td>{r['PEBox']}</td>"
            table_html += f"<td>{r['EPSBox']}</td>"
            table_html += f"<td>{r['RevBox']}</td>"
            table_html += f"<td style='line-height:1.7'>{r['Earnings']}</td>"
            table_html += f"<td>{r['Sentiment']}</td>"
            table_html += "</tr>"
            
        table_html += "</table><br>" 
        st.markdown(table_html, unsafe_allow_html=True)
