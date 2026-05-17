import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import time
from datetime import datetime
import google.generativeai as genai
import plotly.graph_objects as go
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
        .earn-past { color: #e74c3c; font-size: 11px; font-weight: 700; background: #fadbd8; padding: 2px 5px; border-radius: 4px; margin-left: 3px; vertical-align: top;}
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
    return f"<strong>{num:.2f}</strong>" if isinstance(num, (int, float)) else "-"

st.title("💼 Family Office Command Center")
st.write("Track parameters, query AI logic algorithms, and index mass mindshare volume.")

st.sidebar.header("📝 Book Ledger")
if "watchlist" not in st.session_state:
    st.session_state.watchlist = pd.DataFrame({"Category": ["Optical Communications", "Alternative Energy", "Alternative Energy"], "Ticker": ["AAOI", "ENPH", "SEDG"]})

edited_df = st.sidebar.data_editor(st.session_state.watchlist, num_rows="dynamic", use_container_width=True, hide_index=True)
valid_rows = [{"Category": str(r['Category']).strip() if str(r['Category']).strip() not in ["", "NAN", "NONE"] else "Unsorted", "Ticker": str(r['Ticker']).strip().upper()} for _, r in edited_df.iterrows() if str(r['Ticker']).strip().upper() not in ["", "NAN", "NONE"]]

if not valid_rows:
    st.stop()
st.write("---")

if st.button("🔄 Sync Intelligence Pipeline & Core Market Feed", use_container_width=True):
    with st.spinner("Downloading fundamental spreadsheets & running data parsers... (Avg wait: 4 sec / stock)"):
        
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

        for idx, row in enumerate(valid_rows):
            cat, t = row["Category"], row["Ticker"]
            ai_was_pinged = False 
            
            try:
                prof_data = requests.get(f"https://finnhub.io/api/v1/stock/profile2?symbol={t}&token={API_KEY}").json() if API_KEY else {}
                quote_data = requests.get(f"https://finnhub.io/api/v1/quote?symbol={t}&token={API_KEY}").json() if API_KEY else {}
                earn_json = requests.get(f"https://finnhub.io/api/v1/stock/earnings?symbol={t}&token={API_KEY}").json() if API_KEY else []
                metrics = requests.get(f"https://finnhub.io/api/v1/stock/metric?symbol={t}&metric=all&token={API_KEY}").json().get('metric', {}) if API_KEY else {}

                stock = yf.Ticker(t)
                yf_info = stock.info 
                co_name = str(prof_data.get('name') or yf_info.get('shortName') or "Asset").replace("'", "&apos;") 
                
                # Prices and Capitalizations
                price, prev_close = quote_data.get('c') or yf_info.get('currentPrice') or 0, quote_data.get('pc') or yf_info.get('previousClose')
                delta_str = ""
                if price and prev_close and price > 0 and prev_close > 0:
                    move = price - prev_close
                    icon, m_cls = ("▲", "up-move") if move > 0 else ("▼", "dn-move")
                    delta_str = f"<br><span class='{m_cls}'>{icon} {abs(move):.2f} ({move/prev_close * 100:+.2f}%)</span>"

                currency_sym = "$" if yf_info.get('currency', 'USD') in ['USD', 'CAD'] else ("£" if yf_info.get('currency', 'USD') == "GBP" else "HK$")
                price_f = f"<strong>{currency_sym}{price:,.2f}</strong>{delta_str}" if price else "N/A"
                mcap = format_large_currency(yf_info.get('marketCap') or (prof_data.get('marketCapitalization', 0) * 1000000))
                
                # ----- MODULE FIX: VALUATIONS RESTORED (PE/PEG/PB/PS) -----
                pe_ttm = metrics.get('peTTM', yf_info.get('trailingPE'))
                pe_fwd = yf_info.get('forwardPE', metrics.get('peNormalizedAnnual'))
                peg_ttm = yf_info.get('trailingPegRatio') 
                peg_fwd = yf_info.get('pegRatio')         
                pb_val = metrics.get('pbAnnual', yf_info.get('priceToBook'))
                ps_val = metrics.get('psTTM', yf_info.get('priceToSalesTrailing12Months'))
                
                pe_combined = f"<span class='meta-lbl'>P/E (T|F): </span>{fmt_val(pe_ttm)} <span style='color:#ccc; padding: 0 4px;'>|</span> {fmt_val(pe_fwd)}<br>" \
                              f"<span class='meta-lbl'>PEG (T|F): </span>{fmt_val(peg_ttm)} <span style='color:#ccc; padding: 0 4px;'>|</span> {fmt_val(peg_fwd)}<br>" \
                              f"<div style='margin-top:2px;'><span class='meta-lbl'>P/B:</span> {fmt_val(pb_val)} <span style='color:#ccc; padding: 0 4px;'>|</span> <span class='meta-lbl'>P/S:</span> {fmt_val(ps_val)}</div>"
                              
                # ----- NEW QUARTERLY PULSE ENGINE: (Rev/Margin Data Math) -----
                eps_actual, eps_diff = None, None 
                if isinstance(earn_json, list) and len(earn_json) > 0 and 'actual' in earn_json[0]:
                    eps_actual, eps_diff = earn_json[0].get('actual'), earn_json[0].get('surprisePercent')
                eps_box = f"<span class='meta-lbl'>EPS: </span>{f'<strong>${eps_actual:.2f}</strong>' if eps_actual else '-'}" + \
                          (f" <span class='{'up-move' if eps_diff and eps_diff > 0 else 'dn-move'}' style='font-size:11.5px;'>( {eps_diff:+.1f}% )</span>" if eps_diff else "")
                
                # Revenue / Profit Logics! 
                q_rev_val, q_margin, q_margin_qoq = None, None, None
                try: 
                    qf_df = stock.quarterly_financials
                    if not qf_df.empty:
                        if 'Total Revenue' in qf_df.index: q_rev_val = qf_df.loc['Total Revenue'].iloc[0]
                        
                        # Hard QoQ margin Math dynamically extracted! 
                        if 'Total Revenue' in qf_df.index and 'Net Income' in qf_df.index:
                            rev_0, net_0 = qf_df.loc['Total Revenue'].iloc[0], qf_df.loc['Net Income'].iloc[0]
                            if pd.notna(rev_0) and rev_0 != 0 and pd.notna(net_0): q_margin = (net_0 / rev_0) * 100
                            
                            if len(qf_df.columns) > 1:
                                rev_1, net_1 = qf_df.loc['Total Revenue'].iloc[1], qf_df.loc['Net Income'].iloc[1]
                                if pd.notna(rev_1) and rev_1 != 0 and pd.notna(net_1):
                                    q_margin_qoq = q_margin - ((net_1 / rev_1) * 100) # Margin percentage shift (e.g. up +200 bps)
                except: pass

                # Fallback to older records if sheet incomplete!
                if q_margin is None and yf_info.get('profitMargins'): q_margin = yf_info.get('profitMargins') * 100
                marg_str = f"<strong>{q_margin:.1f}%</strong>" if q_margin is not None else "-"
                marg_qoq_str = f" <span class='{'up-move' if q_margin_qoq > 0 else 'dn-move'}' style='font-size:11.5px;'>( {q_margin_qoq:+.1f}% QoQ )</span>" if q_margin_qoq is not None else ""
                marg_box = f"<div style='margin-top:2px;'><span class='meta-lbl'>NET MRG: </span>{marg_str}{marg_qoq_str}</div>"

                # Rev Str Formats
                yoy, qoq = (metrics.get('revenueGrowthTTMYoy') or yf_info.get('revenueGrowth', 0)*100), (metrics.get('revenueGrowthQuarterlyYoy') or yf_info.get('quarterlyRevenueGrowth', 0)*100)
                yoy_qoq_s = f"(Y: <span style='color:#333;font-weight:700'>{f'{yoy:+.1f}%' if yoy else '-'}</span> <span style='color:grey; font-weight:100;'>|</span> Q: <span style='color:#333;font-weight:700'>{f'{qoq:+.1f}%' if qoq else '-'}</span>)"
                rev_str = f"<strong>{currency_sym}{format_large_currency(q_rev_val)}</strong>" if q_rev_val else "-"
                rev_box = f"<div style='margin-top:2px;'><span class='meta-lbl'>REV (Q): </span>{rev_str} <span style='font-size:11.5px;color:#7f8c8d;font-weight:600;'>{yoy_qoq_s}</span></div>"

                # Pulse Assembler 
                pulse_col = f"{eps_box}{rev_box}{marg_box}"


                # Date Formatting! 
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
                    hype_html += f"<span class='meta-lbl'>Reddit Heat: </span> <strong>{c} Posts</strong> (<span class='{h_clr}'>{sent}</span>)<br>"
                else: hype_html += f"<span class='meta-lbl'>Reddit Heat: </span> Quiet<br>"

                ai_take = ""
                if GEMINI_KEY and ai_model is not None:
                    try:
                        raw_headlines = [h.get('title') for h in stock.news][:6] if hasattr(stock, 'news') and stock.news else []
                        if len(raw_headlines) > 0:
                            prompt = f"Analyze these live financial headlines for {t}: {raw_headlines}. In exactly one brief sentence, describe the narrative currently taking place. Then attach one space, and output exactly one tag wrapped in brackets based on the sentiment: [BULLISH], [BEARISH], or [NEUTRAL]."
                            response = ai_model.generate_content(prompt)
                            ai_was_pinged = True
                            try: ai_take = response.text.replace('\n', ' ').strip()
                            except ValueError: ai_take = "Halted by Google Cloud Safety guardrails."
                        else: ai_take = f"Quiet cycle: No public actionable corporate press releases filed recently."
                    except Exception as e:
                        if "429" in str(e) or "quota" in str(e).lower(): ai_take = "Rate limited by Generative ceilings (Traffic overload)."
                        else: ai_take = "Data routing exception encountered."
                else: ai_take = "Module requires Generative Studio parameters on host deployment!"

                data_outputs.append({
                    "Category": cat, "Ticker": t, "Name": co_name, "MCAP_PRC": f"<strong>{mcap}</strong><br><br>{price_f}", 
                    "VALS": pe_combined, "PULSE": pulse_col, 
                    "Earnings": earn_date_str, "Mindshare": hype_html, "AI_Brief": f"<div class='ai-text'>✨ {ai_take}</div>"
                })
            except Exception:
                data_outputs.append({ "Category": cat, "Ticker": t, "Name": "Fail", "MCAP_PRC": "Error", "VALS": "-", "PULSE": "-", "Earnings": "-", "Mindshare": "-", "AI_Brief": "-"})
            
            progress_bar.progress((idx + 1) / len(valid_rows))
            if ai_was_pinged: time.sleep(4.2)
            else: time.sleep(0.5)
            
        progress_bar.empty()
        st.session_state.master_df = pd.DataFrame(data_outputs)


if 'master_df' in st.session_state:
    mdf = st.session_state.master_df
    
    unique_cats = []
    unique_tickers_list = []
    for row in valid_rows:
        if row["Category"] not in unique_cats: unique_cats.append(row["Category"])
        if row["Ticker"] not in unique_tickers_list: unique_tickers_list.append(row["Ticker"])
            
    # REVISED HTML DEPLOYER FOR "DUAL FINANCE" MATRICES!
    for category in unique_cats:
        st.markdown(f"<div class='cat-heading'>{category}</div>", unsafe_allow_html=True)
        cat_df = mdf[mdf['Category'] == category]
        
        table_html = "<table class='custom-table'>"
        # Added Width-Rules ensuring margins, PE arrays, etc remain mathematically balanced onscreen. 
        table_html += "<tr><th style='width: 7%'>Asset</th><th style='width: 12%'>Mkt Cap & Pricing</th><th style='width: 15%'>Valuations Engine</th><th style='width: 18%'>The Quarterly Pulse (YoY/QoQ)</th><th style='width: 10%'>Events</th><th style='width: 13%'>Crowd Trackers</th><th>🧠 Generative Sector Logic</th></tr>"
        
        for _, r in cat_df.iterrows():
            table_html += f"<tr>"
            table_html += f"<td class='ticker-col' title='System Tracking Name: {r['Name']}'>{r['Ticker']}</td>" 
            table_html += f"<td>{r['MCAP_PRC']}</td>"
            table_html += f"<td>{r['VALS']}</td>"
            table_html += f"<td>{r['PULSE']}</td>"
            table_html += f"<td style='line-height:1.7'>{r['Earnings']}</td>"
            table_html += f"<td>{r['Mindshare']}</td>"
            table_html += f"<td>{r['AI_Brief']}</td>"
            table_html += "</tr>"
            
        table_html += "</table><br>" 
        st.markdown(table_html, unsafe_allow_html=True)
    
    st.write("---")
    st.markdown("<div class='cat-heading'>🌍 Search Intensity Metrics (Trailing 12-Mo Catalyst Runways)</div>", unsafe_allow_html=True)
    
    try:
        trends_target_group = unique_tickers_list[:5] 
        st.caption(f"Charting real-world algorithmic internet data-interest shifts relative to trailing baseline levels ({trends_target_group})")
        pytrends = TrendReq(hl='en-US', tz=360, timeout=10)
        
        # TIMEFRAME FIX SECURED ('today 12-m' directly extracts pure 365D views from cloud servers).
        pytrends.build_payload(kw_list=trends_target_group, cat=0, timeframe='today 12-m')
        
        trend_df = pytrends.interest_over_time()
        
        if not trend_df.empty:
            if 'isPartial' in trend_df.columns:
                trend_df = trend_df.drop(columns=['isPartial'])
                
            fig = go.Figure()
            colors = ['#1f77b4', '#d62728', '#ff7f0e', '#2ca02c', '#9467bd']
            
            for idx, col in enumerate(trend_df.columns):
                fig.add_trace(go.Scatter(
                    x=trend_df.index, y=trend_df[col], 
                    mode='lines', name=col,
                    line=dict(color=colors[idx % len(colors)], width=2.5)
                ))
            
            fig.update_layout(
                height=450,
                margin=dict(l=20, r=40, t=20, b=20),
                hovermode="x unified",
                yaxis=dict(title='1YR High=100 Scale Index', showgrid=True, gridcolor='rgba(200,200,200, 0.2)', fixedrange=False),
                xaxis=dict(showgrid=False, fixedrange=False),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
            
        else:
            st.warning("Query response null. Intensity algorithms below chartable scale data bounds on timeframe selected.")

    except Exception as t_err:
        pass
