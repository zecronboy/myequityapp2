import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import time
from datetime import datetime
import google.generativeai as genai
from pytrends.request import TrendReq

st.set_page_config(page_title="Family Office Hub", layout="wide")

st.markdown("""
    <style>
        div[data-testid="stSidebar"] [data-testid="stDataFrame"] { font-size: 15px !important; zoom: 1.1; }
        .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; font-family: -apple-system, sans-serif; table-layout: auto;}
        .custom-table th { font-size: 11px; font-weight: 600; color: #7f8c8d; border-bottom: 2px solid #bdc3c7; padding: 12px 10px; text-align: left; text-transform: uppercase; line-height: 1.3;}
        .custom-table td { font-size: 14px; font-weight: 500; border-bottom: 1px solid #e0e0e0; padding: 14px 10px; line-height: 1.5; vertical-align: middle;} 
        .ticker-col { font-size: 21px !important; font-weight: 800; color: #4FA6FF; cursor: help;} 
        .cat-heading { color: inherit; font-size: 24px; font-weight: bold; border-bottom: 3px solid #4FA6FF; padding-bottom: 6px; margin-bottom: 15px;}
        .up-move { color: #1e8e3e; font-weight: 700; }
        .dn-move { color: #d93025; font-weight: 700; }
        .earn-date { font-family: monospace; color: #2c3e50; font-size: 13px; font-weight:600;}
        .earn-past { color: #e74c3c; font-size: 12px; font-weight: 600; background: #fadbd8; padding: 2px 4px; border-radius: 4px; margin-left: 3px;}
        .meta-lbl { font-size:12px; color: #95a5a6; font-weight:700; text-transform:uppercase; letter-spacing: 0.3px;}
        .ai-text { font-size: 12.5px; line-height: 1.5; color: #444; background-color: rgba(142,68,173,0.06); padding: 8px 10px; border-left: 4px solid #8e44ad; border-radius: 3px; font-style: italic;}
    </style>
""", unsafe_allow_html=True)

def format_large_currency(val):
    if not val or pd.isna(val) or val == 'N/A' or float(val) == 0: return "N/A"
    num = float(val)
    if num >= 1e12: return f"{num/1e12:.2f}T"
    elif num >= 1e9: return f"{num/1e9:.2f}B"
    elif num >= 1e6: return f"{num/1e6:.2f}M"
    else: return f"{num:,.0f}"

def fmt_val(num):
    return f"<strong>{num:.2f}</strong>" if isinstance(num, (int, float)) else "N/A"

st.title("💼 Family Office Command Center")
st.write("Track parameters, query AI logic algorithms, and index mass mindshare volume.")

st.sidebar.header("📝 Book Ledger")
if "watchlist" not in st.session_state:
    st.session_state.watchlist = pd.DataFrame({"Category": ["Artificial Intelligence", "Optical Communications", "Fintech Innovation", "Commodities / Def."], "Ticker": ["NVDA", "AAOI", "SQ", "XOM"]})

edited_df = st.sidebar.data_editor(st.session_state.watchlist, num_rows="dynamic", use_container_width=True, hide_index=True)
valid_rows = [{"Category": str(r['Category']).strip() if str(r['Category']).strip() not in ["", "NAN", "NONE"] else "Unsorted", "Ticker": str(r['Ticker']).strip().upper()} for _, r in edited_df.iterrows() if str(r['Ticker']).strip().upper() not in ["", "NAN", "NONE"]]

if not valid_rows:
    st.stop()
st.write("---")

if st.button("🔄 Sync Intelligence Pipeline & Core Market Feed", use_container_width=True):
    with st.spinner("Downloading financial footprints & establishing stable LLM cadence... (May take 30+ secs depending on book size)"):
        
        API_KEY = st.secrets.get("FINNHUB_KEY", "")
        GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
        
        ai_model = None
        if GEMINI_KEY:
            try:
                genai.configure(api_key=GEMINI_KEY)
                available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                chosen_model = 'gemini-1.5-flash'
                for vm in available:
                    if 'gemini-1.5' in vm or 'gemini-flash' in vm or 'gemini-pro' in vm:
                        chosen_model = vm
                        break
                ai_model = genai.GenerativeModel(chosen_model.replace("models/", ""))
            except: pass

        data_outputs = []
        progress_bar = st.progress(0)
        
        wsb_lookup = {}
        try:
            wsb_json = requests.get("https://tradestie.com/api/v1/apps/reddit", timeout=5).json()
            for tick in wsb_json: wsb_lookup[tick['ticker']] = tick
        except: pass
        
        pytrends = TrendReq(hl='en-US', tz=360, timeout=5)

        for idx, row in enumerate(valid_rows):
            cat, t = row["Category"], row["Ticker"]
            ai_was_pinged = False # Tracking marker
            
            try:
                prof_data = requests.get(f"https://finnhub.io/api/v1/stock/profile2?symbol={t}&token={API_KEY}").json() if API_KEY else {}
                quote_data = requests.get(f"https://finnhub.io/api/v1/quote?symbol={t}&token={API_KEY}").json() if API_KEY else {}
                earn_json = requests.get(f"https://finnhub.io/api/v1/stock/earnings?symbol={t}&token={API_KEY}").json() if API_KEY else []
                metrics = requests.get(f"https://finnhub.io/api/v1/stock/metric?symbol={t}&metric=all&token={API_KEY}").json().get('metric', {}) if API_KEY else {}

                stock = yf.Ticker(t)
                yf_info = stock.info 
                co_name = str(prof_data.get('name') or yf_info.get('shortName') or "Asset").replace("'", "&apos;") 
                
                price, prev_close = quote_data.get('c') or yf_info.get('currentPrice') or 0, quote_data.get('pc') or yf_info.get('previousClose')
                delta_str = ""
                if price and prev_close and price > 0 and prev_close > 0:
                    move = price - prev_close
                    icon, m_cls = ("▲", "up-move") if move > 0 else ("▼", "dn-move")
                    delta_str = f"<br><span class='{m_cls}'>{icon} {abs(move):.2f} ({move/prev_close * 100:+.2f}%)</span>"

                currency_sym = "$" if yf_info.get('currency', 'USD') in ['USD', 'CAD'] else ("£" if yf_info.get('currency', 'USD') == "GBP" else "HK$")
                price_f = f"<strong>{currency_sym}{price:,.2f}</strong>{delta_str}" if price else "N/A"
                mcap = format_large_currency(yf_info.get('marketCap') or (prof_data.get('marketCapitalization', 0) * 1000000))
                
                pe_combined = f"<span class='meta-lbl'>PE: </span>{fmt_val(metrics.get('peTTM', yf_info.get('trailingPE')))} <span style='color:#ccc'>|</span> {fmt_val(yf_info.get('forwardPE'))}<br>" \
                              f"<span class='meta-lbl'>PG: </span>{fmt_val(yf_info.get('trailingPegRatio'))} <span style='color:#ccc'>|</span> {fmt_val(yf_info.get('pegRatio'))}"
                              
                eps_actual, eps_diff = None, None 
                if isinstance(earn_json, list) and len(earn_json) > 0 and 'actual' in earn_json[0]:
                    eps_actual, eps_diff = earn_json[0].get('actual'), earn_json[0].get('surprisePercent')
                eps_box = f"<span class='meta-lbl'>EPS: </span>{f'${eps_actual:.2f}' if eps_actual else '-'}" + \
                          (f" <span class='{'up-move' if eps_diff and eps_diff > 0 else 'dn-move'}' style='font-size:11px;'>( {eps_diff:+.1f}% )</span>" if eps_diff else "")
                
                try: 
                    q_rev = format_large_currency(stock.quarterly_financials.loc['Total Revenue'].iloc[0]) if not stock.quarterly_financials.empty else None
                except: q_rev = None
                rev_box = f"<br><span class='meta-lbl'>REV: </span>{currency_sym}{q_rev if q_rev else '-'}<br><span class='meta-lbl'>Y/Y: </span>{(metrics.get('revenueGrowthTTMYoy') or yf_info.get('revenueGrowth', 0)*100):.1f}%"

                earn_ts = yf_info.get('earningsTimestamp') 
                if earn_ts:
                    utc_dt = datetime.utcfromtimestamp(earn_ts)
                    is_p = utc_dt < datetime.utcnow()
                    earn_date_str = f"<span class='earn-date'>{utc_dt.strftime('%b %d')}</span> <span class='earn-past'>{'(Past)' if is_p else ''}</span>"
                else: earn_date_str = "-"

                hype_html = ""
                if t in wsb_lookup:
                    c, sent = wsb_lookup[t]['no_of_comments'], wsb_lookup[t]['sentiment']
                    h_clr = "up-move" if sent == "Bullish" else "dn-move"
                    hype_html += f"<span class='meta-lbl'>WSB/Reddit: </span> <strong>{c} Mentions</strong> (<span class='{h_clr}'>{sent}</span>)<br>"
                else: hype_html += f"<span class='meta-lbl'>WSB/Reddit: </span> Quiet / Null<br>"
                
                try:
                    pytrends.build_payload([t], cat=0, timeframe='now 7-d', geo='')
                    g_data = pytrends.interest_over_time()
                    hype_html += f"<span class='meta-lbl'>G-Trends 7D: </span> <strong>{g_data[t].iloc[-1]} / 100</strong>"
                except: 
                    # If this gets completely banned by google shared IP we gracefully hide the error text
                    pass 

                # ====== OPTIMIZED GEMINI AI MODULE ======
                ai_take = ""
                if GEMINI_KEY and ai_model is not None:
                    try:
                        raw_headlines = [h.get('title') for h in stock.news][:6] if hasattr(stock, 'news') and stock.news else []
                        
                        # SMART AI PREVENTER: Don't spend google quota requests on assets with ZERO news today!
                        if len(raw_headlines) > 0:
                            prompt = f"Analyze these live financial headlines for {t}: {raw_headlines}. In exactly one brief sentence, describe the narrative currently taking place. Then attach one space, and output exactly one tag wrapped in brackets based on the sentiment: [BULLISH], [BEARISH], or [NEUTRAL]."
                            response = ai_model.generate_content(prompt)
                            ai_was_pinged = True
                            
                            try: ai_take = response.text.replace('\n', ' ').strip()
                            except ValueError: ai_take = "Halted by Google Cloud Safety guardrails."
                        else: ai_take = f"Quiet cycle: 0 actionable corporate press releases filed for {t}."
                        
                    except Exception as e:
                        if "429" in str(e) or "quota" in str(e).lower(): ai_take = "Rate limited by 15 req/min AI Ceiling (Slow down queries)."
                        else: ai_take = "Data routing exception encountered."
                else:
                    ai_take = "Module requires Valid Gemini Studio configuration string."

                data_outputs.append({
                    "Category": cat, "Ticker": t, "Name": co_name, "MCAP_PRC": f"<strong>{mcap}</strong><br><br>{price_f}", 
                    "FINS": f"{pe_combined}<br><div style='border-top:1px dashed #ccc; padding-top: 3px; margin-top: 3px;'>{eps_box}{rev_box}</div>",
                    "Earnings": earn_date_str, "Mindshare": hype_html, "AI_Brief": f"<div class='ai-text'>✨ {ai_take}</div>"
                })
            except Exception:
                data_outputs.append({ "Category": cat, "Ticker": t, "Name": "Fail", "MCAP_PRC": "Error", "FINS": "-", "Earnings": "-", "Mindshare": "-", "AI_Brief": "-"})
            
            progress_bar.progress((idx + 1) / len(valid_rows))
            
            # --- PERFECTING THE SPEED BUMPS ---
            # To adhere STRICTLY to Gemini's hard 4.0 second per cycle rule without penalizing offline stocks
            if ai_was_pinged:
                time.sleep(4.2)
            else:
                time.sleep(0.5)
            
        progress_bar.empty()
        st.session_state.master_df = pd.DataFrame(data_outputs)


if 'master_df' in st.session_state:
    mdf = st.session_state.master_df
    unique_cats = []
    for row in valid_rows:
        if row["Category"] not in unique_cats: unique_cats.append(row["Category"])
            
    for category in unique_cats:
        st.markdown(f"<div class='cat-heading'>{category}</div>", unsafe_allow_html=True)
        cat_df = mdf[mdf['Category'] == category]
        
        table_html = "<table class='custom-table'>"
        table_html += "<tr><th style='width: 8%'>Asset</th><th style='width: 12%'>Cap & Daily Price</th><th style='width: 17%'>Valuations & Core Metrics</th><th style='width: 10%'>Earning Catalyst</th><th style='width: 18%'>Mindshare Trackers</th><th>🧠 Generative AI Analysis Pipeline</th></tr>"
        
        for _, r in cat_df.iterrows():
            table_html += f"<tr>"
            table_html += f"<td class='ticker-col' title='Corporate Entity Verification: {r['Name']}'>{r['Ticker']}</td>" 
            table_html += f"<td>{r['MCAP_PRC']}</td>"
            table_html += f"<td>{r['FINS']}</td>"
            table_html += f"<td style='line-height:1.7'>{r['Earnings']}</td>"
            table_html += f"<td>{r['Mindshare']}</td>"
            table_html += f"<td>{r['AI_Brief']}</td>"
            table_html += "</tr>"
            
        table_html += "</table><br>" 
        st.markdown(table_html, unsafe_allow_html=True)
