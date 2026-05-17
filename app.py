import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import time
from datetime import datetime

st.set_page_config(page_title="Family Office Hub", layout="wide")

# --- UI STYLING MASTER TEMPLATE ---
st.markdown("""
    <style>
        div[data-testid="stSidebar"] [data-testid="stDataFrame"] {
            font-size: 15px !important;
            zoom: 1.1;
        }

        .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; font-family: -apple-system, sans-serif; table-layout: auto;}
        .custom-table th { font-size: 11px; font-weight: 600; color: #7f8c8d; border-bottom: 2px solid #bdc3c7; padding: 12px 10px; text-align: left; text-transform: uppercase; line-height: 1.3;}
        .custom-table td { font-size: 15px; font-weight: 500; border-bottom: 1px solid #e0e0e0; padding: 14px 10px; line-height: 1.6; vertical-align: middle;} 
        
        .ticker-col { font-size: 21px !important; font-weight: 800; color: #4FA6FF; cursor: help;} 
        .cat-heading { color: inherit; font-size: 26px; font-weight: bold; border-bottom: 3px solid #4FA6FF; padding-bottom: 6px; margin-bottom: 15px;}
        
        .alert-drama { color: #d93025; font-weight: 700; background-color: #fce8e6; padding: 4px 8px; border-radius: 4px; font-size: 13px;}
        .alert-quiet { color: #1e8e3e; font-weight: 600; font-size: 13px;}
        
        .up-move { color: #1e8e3e; font-weight: 700; font-size: 14px; }
        .dn-move { color: #d93025; font-weight: 700; font-size: 14px; }
        .earn-date { font-family: monospace; color: #2c3e50; font-size: 14px; font-weight:600;}
        .earn-past { font-family: monospace; color: #e74c3c; font-size: 11px; font-weight: 700; background: #fadbd8; padding: 2px 4px; border-radius: 3px; margin-left: 5px; vertical-align: top;}
        
        .meta-lbl { font-size:12px; color: #95a5a6; font-weight:700; text-transform:uppercase; letter-spacing: 0.3px;}
        .val-sub { font-size: 12px; color: #7f8c8d; }
    </style>
""", unsafe_allow_html=True)

def format_large_currency(val):
    if not val or pd.isna(val) or val == 'N/A' or float(val) == 0: return "N/A"
    num = float(val)
    if num >= 1e12: return f"{num/1e12:.2f}T"
    elif num >= 1e9: return f"{num/1e9:.2f}B"
    elif num >= 1e6: return f"{num/1e6:.2f}M"
    else: return f"{num:,.0f}"

# Short formatting tool for clean Valuation numbers
def fmt_val(num):
    return f"<strong>{num:.2f}</strong>" if isinstance(num, (int, float)) else "N/A"

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

edited_df = st.sidebar.data_editor(st.session_state.watchlist, num_rows="dynamic", use_container_width=True, hide_index=True)
st.session_state.watchlist = edited_df

valid_rows = [{"Category": str(row['Category']).strip() if str(row['Category']).strip() not in ["", "NAN", "NONE"] else "Core Holdings", "Ticker": str(row['Ticker']).strip().upper()} for _, row in edited_df.iterrows() if str(row['Ticker']).strip().upper() not in ["", "NAN", "NONE"]]

if not valid_rows:
    st.warning("Empty Database. Insert Assets onto the Left Sidebar pane."); st.stop()
st.write("---")

DRAMA_WORDS = ["buyback", "dilution", "lawsuit", "investigation", "subpoena", "scandal", "acquisition", "layoffs", "merger", "bankruptcy"]

# --- MODULE 2: DENSE PIPELINE PROCESSOR ---
if st.button("🔄 Command: Sync High-Density Fundamental Matrix", use_container_width=True):
    with st.spinner("Executing broad API pulls & formatting UI matrices..."):
        
        API_KEY = st.secrets["FINNHUB_KEY"]
        data_outputs = []
        progress_bar = st.progress(0)
        
        for idx, row in enumerate(valid_rows):
            cat, t = row["Category"], row["Ticker"]
            try:
                prof_data = requests.get(f"https://finnhub.io/api/v1/stock/profile2?symbol={t}&token={API_KEY}").json()
                quote_data = requests.get(f"https://finnhub.io/api/v1/quote?symbol={t}&token={API_KEY}").json()
                earn_json = requests.get(f"https://finnhub.io/api/v1/stock/earnings?symbol={t}&token={API_KEY}").json()

                stock = yf.Ticker(t)
                yf_info = stock.info 
                
                raw_name = prof_data.get('name') or yf_info.get('shortName') or yf_info.get('longName') or "Global Asset"
                co_name = str(raw_name).replace("'", "&apos;") 
                
                price, prev_close = quote_data.get('c'), quote_data.get('pc')
                if price is None or price == 0 or "error" in quote_data: 
                    price, prev_close = yf_info.get('currentPrice') or yf_info.get('regularMarketPrice'), yf_info.get('previousClose')
                
                delta_str = ""
                if price and prev_close:
                    move = price - prev_close
                    icon, m_cls = ("▲", "up-move") if move > 0 else ("▼", "dn-move")
                    delta_str = f"<br><span class='{m_cls}'>{icon} {abs(move):.2f} ({move/prev_close * 100:+.2f}%)</span>"

                curr_raw = yf_info.get('currency', 'USD')
                currency_sym = "$" if curr_raw in ['USD', 'CAD'] else ("£" if curr_raw == "GBP" else "HK$")
                price_f = f"<strong>{currency_sym}{price:,.2f}</strong>{delta_str}" if price else "N/A"
                mcap = f"<strong>{currency_sym}{format_large_currency(yf_info.get('marketCap') or (prof_data.get('marketCapitalization', 0) * 1000000))}</strong>"
                
                # ------ ULTIMATE VALUATION MATRICES (PE/PEG/PB/PS) ------
                metrics = requests.get(f"https://finnhub.io/api/v1/stock/metric?symbol={t}&metric=all&token={API_KEY}").json().get('metric', {})
                
                pe_ttm = metrics.get('peTTM', yf_info.get('trailingPE'))
                pe_fwd = yf_info.get('forwardPE', metrics.get('peNormalizedAnnual'))
                peg_ttm = yf_info.get('trailingPegRatio') # Rarely indexed for free by all stocks, we gracefully map None 
                peg_fwd = yf_info.get('pegRatio')         # Yahoo's 5Yr Forward Expected PEG typically 
                pb_val = metrics.get('pbAnnual', yf_info.get('priceToBook'))
                ps_val = metrics.get('psTTM', yf_info.get('priceToSalesTrailing12Months'))

                # Multi-line html grouping for the ultimate ratio matrix!
                pe_combined = (
                    f"<span class='meta-lbl'>P/E ➔</span> <span class='val-sub'>TTM:</span>{fmt_val(pe_ttm)} <span style='color:grey; font-size:10px;'>|</span> <span class='val-sub'>FWD:</span>{fmt_val(pe_fwd)}<br>"
                    f"<span class='meta-lbl'>PEG ➔</span> <span class='val-sub'>TTM:</span>{fmt_val(peg_ttm)} <span style='color:grey; font-size:10px;'>|</span> <span class='val-sub'>FWD:</span>{fmt_val(peg_fwd)}<br>"
                    f"<div style='margin-top: 3px;'><span class='meta-lbl'>P/B:</span> {fmt_val(pb_val)} <span style='color:#ccc; padding:0 3px;'>|</span> <span class='meta-lbl'>P/S:</span> {fmt_val(ps_val)}</div>"
                )
                              
                # EPS Engine
                eps_latest_v, eps_prev_v, eps_diff = None, None, None 
                if isinstance(earn_json, list) and len(earn_json) > 0:
                    eps_latest_v, eps_diff = earn_json[0].get('actual'), earn_json[0].get('surprisePercent')
                    if len(earn_json) > 1: eps_prev_v = earn_json[1].get('actual')
                
                if eps_latest_v:
                    diff_cls, s_pref = ("up-move", "Beat Est by") if (eps_diff and eps_diff >= 0) else ("dn-move", "Missed Est by")
                    eps_comp = f"<span class='meta-lbl'>Latest (Q):</span> <strong>${eps_latest_v:.2f}</strong> <span class='{diff_cls}' style='font-size:12px;'>( {s_pref} {abs(eps_diff):.1f}% )</span><br>" if eps_diff else f"<span class='meta-lbl'>Latest Q:</span> {eps_latest_v}<br>"
                    eps_comp += f"<span class='meta-lbl'>Prior (Q-1):</span> <strong>${eps_prev_v:.2f}</strong>" if eps_prev_v else ""
                else: 
                    eps_comp = "-" 

                # ADVANCED REVENUE QUARTERLY BUILD
                q_rev_val = None
                try: 
                    qf_df = stock.quarterly_financials
                    if not qf_df.empty and 'Total Revenue' in qf_df.index:
                        q_rev_val = format_large_currency(qf_df.loc['Total Revenue'].iloc[0])
                except: pass

                rev_str = f"{currency_sym}{q_rev_val}" if q_rev_val else "Rstrct"
                rev_yoy, rev_qoq = (metrics.get('revenueGrowthTTMYoy') or yf_info.get('revenueGrowth', 0)*100), (metrics.get('revenueGrowthQuarterlyYoy') or yf_info.get('quarterlyRevenueGrowth', 0)*100)
                
                rev_comp = f"<span class='meta-lbl'>Latest (Q): </span><strong>{rev_str}</strong> <span style='font-size:10px;color:#c0392b;font-weight:700;' title='Institutional % surprise poll expectations paywalled.'>(No Est)</span><br>" 
                rev_comp += f"<span class='meta-lbl'>Y/Y Gro:</span> <strong>{f'{rev_yoy:.1f}%' if rev_yoy else '-'}</strong> <span style='color:#ccc'>|</span> " \
                            f"<span class='meta-lbl'>Q/Q Gro:</span> <strong>{f'{rev_qoq:.1f}%' if rev_qoq else '-'}</strong>"

                # Upcoming/Dead Event Engine! 
                earn_ts = yf_info.get('earningsTimestamp') 
                if earn_ts:
                    earn_dt = datetime.utcfromtimestamp(earn_ts)
                    is_past = earn_dt < datetime.utcnow()
                    status_lbl = "<span class='earn-past'>(PAST)</span>" if is_past else ""
                    earn_date_str = f"<span class='earn-date'>{earn_dt.strftime('%b %d, %y')}</span>{status_lbl}"
                else: earn_date_str = "<span class='meta-lbl'>Unlisted</span>"

                # Keyword Extraction
                try:
                    found_drama = list(set([word.title() for h in [n.get('title', '').lower() for n in stock.news] for word in DRAMA_WORDS if word in h])) if stock.news else []
                    drama_alert = f"<span class='alert-drama'>🚨: {', '.join(found_drama)}</span>" if found_drama else f"<span class='alert-quiet'>✅ Nominal Media</span>"
                except: drama_alert = "No Scrape"
                
                data_outputs.append({"Category": cat, "Ticker": t, "Name": co_name, "MktCap": mcap, "PriceBox": price_f, "ValuationBox": pe_combined, "EPSBox": eps_comp, "RevBox": rev_comp, "Earnings": earn_date_str, "Sentiment": drama_alert})
                
            except Exception as e:
                data_outputs.append({ "Category": cat, "Ticker": t, "Name": "Fail", "MktCap": "ERR", "PriceBox": "Err", "ValuationBox": "-", "EPSBox": "-", "RevBox": "-", "Earnings": "-", "Sentiment": "-"})
            
            progress_bar.progress((idx + 1) / len(valid_rows))
            time.sleep(0.4) 
            
        progress_bar.empty()
        st.session_state.master_df = pd.DataFrame(data_outputs)

# --- MODULE 3: THE HTML "PRO GRID" VIEWER ---
if 'master_df' in st.session_state:
    mdf = st.session_state.master_df
    
    unique_cats = []
    for row in valid_rows:
        if row["Category"] not in unique_cats: unique_cats.append(row["Category"])
            
    for category in unique_cats:
        st.markdown(f"<div class='cat-heading'>{category}</div>", unsafe_allow_html=True)
        cat_df = mdf[mdf['Category'] == category]
        
        # Expanding the new multi-ratio layout header:
        table_html = "<table class='custom-table'>"
        table_html += "<tr><th style='width: 8%'>Asset</th><th style='width: 8%'>Mkt Cap</th><th style='width: 14%'>Daily Tape</th><th style='width: 16%'>Master Valuations</th><th style='width: 17%'>Quarterly EPS vs Street</th><th style='width: 17%'>Forward Rev Trajectory</th><th style='width: 10%'>Events Calendar</th><th style='width: 10%'>AI Mention Scrape</th></tr>"
        
        for _, r in cat_df.iterrows():
            table_html += f"<tr>"
            table_html += f"<td class='ticker-col' title='Corporate Entity: {r['Name']}'>{r['Ticker']}</td>" 
            table_html += f"<td>{r['MktCap']}</td>"
            table_html += f"<td>{r['PriceBox']}</td>"
            # Injected New Ratio Data! 
            table_html += f"<td>{r['ValuationBox']}</td>"
            table_html += f"<td>{r['EPSBox']}</td>"
            table_html += f"<td>{r['RevBox']}</td>"
            table_html += f"<td style='line-height:1.7'>{r['Earnings']}</td>"
            table_html += f"<td>{r['Sentiment']}</td>"
            table_html += "</tr>"
            
        table_html += "</table><br>" 
        st.markdown(table_html, unsafe_allow_html=True)
