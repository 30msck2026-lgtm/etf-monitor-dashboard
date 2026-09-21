import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="ETF Overview", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background-color: #060913 !important; color: #f1f5f9 !important; }
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

    div.stButton > button {
        background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
    }

    div[data-testid="stRadio"] > div { flex-direction: row !important; gap: 10px !important; }
    div[data-testid="stRadio"] label {
        background-color: #12192c !important;
        border: 1px solid #1e2942 !important;
        padding: 6px 18px !important;
        border-radius: 20px !important;
        cursor: pointer !important;
        color: #94a3b8 !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stRadio"] label[data-checked="true"], 
    div[data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
        color: #ffffff !important;
        border: 1px solid transparent !important;
        box-shadow: 0 2px 10px rgba(79, 70, 229, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

top_left, top_right = st.columns([5, 1])
with top_left:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
        <div style="width:36px; height:36px; background:linear-gradient(135deg, #6366f1 0%, #3b82f6 100%); border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px;">📈</div>
        <h1 style="font-size:26px; font-weight:800; color:#ffffff; margin:0;">ETF Overview (Full Breadth)</h1>
    </div>
    """, unsafe_allow_html=True)

with top_right:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

CATEGORY_ETFS = {
    "Sector ETF": ["XLK", "XLC", "XLY", "XLI", "XLF", "XLV", "XLB", "XLU", "XLP", "XLRE", "XLE"],
    "Industry ETF": ["SMH", "SOXX", "IGV", "XBI", "ITA", "XHB", "MAGS"],
    "Asset Class": ["SPY", "QQQ", "IWM", "SCHD", "VYM"],
    "Market Overview": ["XLK", "XLC", "XLY", "XLI", "XLF", "XLV", "XLB", "XLU", "XLP", "XLRE", "XLE", "SMH", "SOXX", "IGV", "SCHD", "VYM"]
}

selected_cat = st.radio(
    "分類視圖",
    options=["Sector ETF", "Industry ETF", "Asset Class", "Market Overview"],
    index=0,
    label_visibility="collapsed"
)

with st.expander("➕ / ➖ 點此自訂該分類下的 ETF 標的 (點擊展開或關閉)", expanded=False):
    default_pool = ", ".join(CATEGORY_ETFS[selected_cat])
    user_input = st.text_input("ETF 監控代碼（逗號隔開）", value=default_pool)
    active_etfs = [x.strip().upper() for x in user_input.split(",") if x.strip()]

# 全量持股名單庫（涵蓋板塊與行業實際完整組成成分股）
FULL_ETF_UNIVERSE = {
    "XLK": ("科技板塊 (Tech 全量)", [
        "AAPL", "MSFT", "NVDA", "AVGO", "CSCO", "ACN", "ORCL", "CRM", "AMD", "QCOM", "TXN", "INTU", 
        "AMAT", "NOW", "IBM", "ADI", "LRCX", "MU", "PANW", "KLAC", "SNPS", "CDNS", "CRWD", "FTNT", 
        "MCHP", "APH", "TEL", "NXPI", "MSI", "ROP", "ANSS", "ON", "MPWR", "KEYS", "IT", "FSLR", "GLW", 
        "CDW", "HPQ", "TDY", "WDC", "HPE", "NTAP", "STX", "PTC", "ZBRA", "SWKS", "TRMB", "GEN", "AKAM"
    ]),
    "XLE": ("能源板塊 (Energy 全量)", [
        "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "WMB", "OXY", "KMI", "HAL", "DVN", 
        "BKR", "FANG", "HES", "TRGP", "EQT", "CTRA", "MRO", "APA", "OVV"
    ]),
    "XLF": ("金融板塊 (Fin 全量)", [
        "BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SPGI", "AXP", "PGR", "CB", "BLK", 
        "C", "MMC", "SCHW", "ICE", "MCO", "AON", "AJG", "TRV", "PNC", "AFL", "USB", "BK", "ALL", 
        "MET", "COF", "PRU", "AIG", "HIG", "ACGL", "FITB", "WTW", "MTB", "TROW", "BRO", "DFS", "RJF"
    ]),
    "XLC": ("通訊服務 (Comm 全量)", [
        "META", "GOOGL", "GOOG", "NFLX", "TMUS", "CMCSA", "DIS", "T", "VZ", "CHTR", "EA", "TTWO", 
        "WBD", "OMC", "IPG", "FOXA", "FOX", "NWSA", "NWS", "MTCH", "LYV"
    ]),
    "XLY": ("非必需消費 (Discr 全量)", [
        "AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "BKNG", "SBUX", "TJX", "ORLY", "AZO", "MAR", 
        "LULU", "HLT", "CMG", "ROST", "F", "GM", "DHI", "LEN", "YUM", "EBAY", "KMX", "APTV", "GPC"
    ]),
    "XLI": ("工業製造 (Ind 全量)", [
        "GE", "CAT", "UNP", "HON", "RTX", "BA", "DE", "LMT", "ETN", "UPS", "ADP", "WM", "GD", 
        "ITW", "NOC", "CSX", "NSC", "PCAR", "EMR", "PH", "FDX", "CARR", "CTAS", "TDG", "TT", "JCI"
    ]),
    "XLV": ("醫療保健 (Health 全量)", [
        "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "PFE", "AMGN", "DHR", "ISRG", "BMY", 
        "SYK", "VRTX", "MDT", "GILD", "ELV", "CI", "REGN", "BSX", "ZTS", "BDX", "BIIB", "HCA"
    ]),
    "XLB": ("基礎原物料 (Materials 全量)", [
        "LIN", "APD", "SHW", "FCX", "ECL", "NEM", "DOW", "CTVA", "PPG", "DD", "VMC", "MLM", 
        "ALB", "CF", "FMC", "MOS", "IFF", "EMN", "CE"
    ]),
    "XLU": ("公用事業 (Utils 全量)", [
        "NEE", "SO", "DUK", "CEG", "SRE", "AEP", "D", "PEG", "ED", "PCG", "EXC", "XEL", "EIX", 
        "WEC", "DTE", "PPL", "ES", "AEE", "CMS", "CNP"
    ]),
    "XLP": ("必需消費 (Staples 全量)", [
        "PG", "COST", "WMT", "KO", "PEP", "PM", "MDLZ", "MO", "CL", "KMB", "STZ", "GIS", "SYY", 
        "ADM", "KDP", "HSY", "KR", "K", "TSN", "CLX", "CAG"
    ]),
    "XLRE": ("房地產 (Real Est 全量)", [
        "PLD", "AMT", "EQIX", "WELL", "PSA", "O", "CCI", "SPG", "DLR", "CSGP", "VICI", "SBAC", 
        "AVB", "EQR", "WY", "EXR", "INVH", "MAA", "ARE", "UDR"
    ]),
    "SOXX": ("費城半導體 30 檔全量", [
        "NVDA", "AVGO", "AMD", "QCOM", "TXN", "INTC", "ADI", "MU", "LRCX", "KLAC", "AMAT", 
        "ASML", "TSM", "MRVL", "NXPI", "MCHP", "MPWR", "ON", "TER", "ENTG", "SWKS", "QRVO"
    ]),
    "SMH": ("VanEck 半導體 25 檔全量", [
        "NVDA", "TSM", "AVGO", "ASML", "AMD", "QCOM", "TXN", "MU", "LRCX", "AMAT", "ADI", 
        "KLAC", "INTC", "MRVL", "NXPI", "MCHP", "CDNS", "SNPS", "ARM", "MPWR"
    ]),
    "MAGS": ("七巨頭 (Magnificent 7 全量)", [
        "NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "TSLA"
    ]),
    "IGV": ("擴展軟體科技 (全量代表)", [
        "MSFT", "CRM", "ORCL", "ADBE", "NOW", "INTU", "PLTR", "PANW", "SNOW", "WDAY", "CRWD", 
        "FTNT", "DDOG", "TEAM", "MDB", "ZS", "HUBS", "NET", "APP", "DOCU"
    ]),
    "XBI": ("標普生物科技 (全量代表)", [
        "VRTX", "REGN", "BIIB", "ALNY", "MRNA", "ILMN", "INCY", "CRSP", "EXAS", "IONS", "BGNE", 
        "SGEN", "ROIV", "NVAX", "RARE", "SRPT", "HALO", "BMRN"
    ]),
    "UFO": ("Procure 太空產業 (全量代表)", [
        "RKLB", "LMT", "LHX", "NOC", "RTX", "IRDM", "SESG", "VSAT", "PL", "GSAT", "ASTS", "BA"
    ]),
    "SCHD": ("道瓊美股高息 (全量權重)", [
        "AVGO", "CSCO", "HD", "TXN", "PFE", "AMGN", "PEP", "CVX", "ABBV", "KO", "MRK", "BMY", 
        "UPS", "LMT", "BLK", "ADP", "EOG", "GILD", "VZ"
    ]),
    "VYM": ("先鋒高股息 (全量權重)", [
        "JPM", "XOM", "JNJ", "PG", "HD", "CVX", "MRK", "ABBV", "BAC", "WFC", "CSCO", "PFE", 
        "KO", "PEP", "T", "VZ", "MCD", "BMY"
    ])
}

def calc_breadth_vectorized(c_df, constituents, idx):
    valid_cols = [c for c in constituents if c in c_df.columns and len(c_df[c].dropna()) > abs(idx) + 120]
    if not valid_cols:
        return None
    
    cnt_20, cnt_50, cnt_200 = 0, 0, 0
    for c in valid_cols:
        s = c_df[c].dropna()
        sub_s = s.iloc[:len(s)+idx] if idx < 0 else s
        last_p = sub_s.iloc[-1]
        
        e20 = sub_s.ewm(span=20, adjust=False).mean().iloc[-1]
        e50 = sub_s.ewm(span=50, adjust=False).mean().iloc[-1]
        span_200 = 200 if len(sub_s) >= 200 else len(sub_s)
        e200 = sub_s.ewm(span=span_200, adjust=False).mean().iloc[-1]
        
        if last_p > e20: cnt_20 += 1
        if last_p > e50: cnt_50 += 1
        if last_p > e200: cnt_200 += 1
        
    n = len(valid_cols)
    return (cnt_20/n)*100, (cnt_50/n)*100, (cnt_200/n)*100, n

@st.cache_data(ttl=1800)
def fetch_dashboard_data(tickers):
    results = []
    
    # 基準 SPY 報酬
    spy_ret_3m = 0
    try:
        spy_raw = yf.download("SPY", period="1y", interval="1d", progress=False)
        spy_close = spy_raw['Close']
        if isinstance(spy_close, pd.DataFrame): spy_close = spy_close.iloc[:, 0]
        if len(spy_close) >= 63:
            spy_ret_3m = (spy_close.iloc[-1] / spy_close.iloc[-63] - 1)
    except Exception:
        pass

    for ticker in tickers:
        try:
            raw = yf.download(ticker, period="1y", interval="1d", progress=False)
            if raw.empty or 'Close' not in raw: continue
            
            series = raw['Close']
            if isinstance(series, pd.DataFrame): series = series.iloc[:, 0]
            series = series.dropna()
            if len(series) < 120: continue
            
            cur_p = series.iloc[-1]
            e10 = series.ewm(span=10, adjust=False).mean().iloc[-1]
            e20 = series.ewm(span=20, adjust=False).mean().iloc[-1]
            e30 = series.ewm(span=30, adjust=False).mean().iloc[-1]
            e50 = series.ewm(span=50, adjust=False).mean().iloc[-1]
            span_200 = 200 if len(series) >= 200 else len(series)
            e200 = series.ewm(span=span_200, adjust=False).mean().iloc[-1]
            ma150 = series.rolling(window=150, min_periods=100).mean().iloc[-1]
            
            p_1m = (cur_p / series.iloc[-21] - 1) * 100 if len(series) >= 21 else 0
            p_2m = (cur_p / series.iloc[-42] - 1) * 100 if len(series) >= 42 else 0
            p_3m = (cur_p / series.iloc[-63] - 1) * 100 if len(series) >= 63 else 0
            
            rs_score = ((p_3m / 100) - spy_ret_3m) * 100
            trend_status = "UP ▲" if (cur_p > e50 and e20 > e50) else ("DOWN ▼" if (cur_p < e50 and e20 < e50) else "RNG ◼")
            
            # 取得全量成分股
            sector_name, constituents = FULL_ETF_UNIVERSE.get(ticker, (f"自訂標的 ({ticker})", []))
            
            # 如果未知，備用抓取其所有可獲得持股
            if not constituents:
                try:
                    t_obj = yf.Ticker(ticker)
                    top_h = t_obj.funds_data.top_holdings
                    if top_h is not None and not top_h.empty:
                        constituents = [str(x).replace(".", "-").strip().upper() for x in top_h.index.tolist() if isinstance(x, str)]
                except Exception:
                    pass

            b_now_str = "N/A"
            chg_1w_str = chg_1m_str = chg_2m_str = chg_3m_str = "-"
            ew_ret = "- / - / -"
            
            if constituents:
                # 一次性批量下載該 ETF 全量成分股歷史日線
                c_raw = yf.download(constituents, period="2y", interval="1d", progress=False)
                if not c_raw.empty and 'Close' in c_raw:
                    c_close = c_raw['Close']
                    c_df = pd.DataFrame({constituents[0]: c_close}) if isinstance(c_close, pd.Series) else c_close.copy()
                    
                    b_res = calc_breadth_vectorized(c_df, constituents, 0)
                    if b_res is not None:
                        b_now_str = f"{b_res[0]:.0f}%, {b_res[1]:.0f}%, {b_res[2]:.0f}% ({b_res[3]}檔)"
                        
                        b_1w = calc_breadth_vectorized(c_df, constituents, -5)
                        b_1m = calc_breadth_vectorized(c_df, constituents, -21)
                        b_2m = calc_breadth_vectorized(c_df, constituents, -42)
                        b_3m = calc_breadth_vectorized(c_df, constituents, -63)
                        
                        if b_1w: chg_1w_str = f"{(b_res[1] - b_1w[1]):+.1f}%"
                        if b_1m: chg_1m_str = f"{(b_res[1] - b_1m[1]):+.1f}%"
                        if b_2m: chg_2m_str = f"{(b_res[1] - b_2m[1]):+.1f}%"
                        if b_3m: chg_3m_str = f"{(b_res[1] - b_3m[1]):+.1f}%"

                    # 計算全體成分股算術等權回報
                    ew1, ew2, ew3 = [], [], []
                    for c in constituents:
                        if c in c_df.columns:
                            sc = c_df[c].dropna()
                            if len(sc) >= 21: ew1.append((sc.iloc[-1] / sc.iloc[-21] - 1) * 100)
                            if len(sc) >= 42: ew2.append((sc.iloc[-1] / sc.iloc[-42] - 1) * 100)
                            if len(sc) >= 63: ew3.append((sc.iloc[-1] / sc.iloc[-63] - 1) * 100)
                    
                    if ew1:
                        ew_ret = f"{np.mean(ew1):+.1f}% / {np.mean(ew2):+.1f}% / {np.mean(ew3):+.1f}%"

            results.append({
                "ticker": ticker,
                "sector": sector_name,
                "price": f"${cur_p:.2f}",
                "trend": trend_status,
                "rs": f"{rs_score:+.1f}",
                "ema_all": f"{(cur_p/e10-1)*100:+.1f}%, {(cur_p/e20-1)*100:+.1f}%, {(cur_p/e30-1)*100:+.1f}%, {(cur_p/e50-1)*100:+.1f}%, {(cur_p/e200-1)*100:+.1f}%",
                "ma30w": f"{(cur_p/ma150-1)*100:+.1f}%",
                "price_ret": f"{p_1m:+.1f}% / {p_2m:+.1f}% / {p_3m:+.1f}%",
                "ew_ret": ew_ret,
                "breadth": b_now_str,
                "chg_1w": chg_1w_str,
                "chg_1m": chg_1m_str,
                "chg_2m": chg_2m_str,
                "chg_3m": chg_3m_str
            })
        except Exception:
            continue
            
    return results

with st.spinner(f"⚡ 正在加載 {selected_cat} 全量成分股並計算市場寬度..."):
    items = fetch_dashboard_data(active_etfs)

table_rows = ""
for it in items:
    trend_color = "#10b981" if "UP" in it["trend"] else ("#ef4444" if "DOWN" in it["trend"] else "#94a3b8")
    trend_bg = "rgba(16, 185, 129, 0.15)" if "UP" in it["trend"] else ("rgba(239, 68, 68, 0.15)" if "DOWN" in it["trend"] else "rgba(148, 163, 184, 0.15)")
    rs_color = "#10b981" if not it["rs"].startswith("-") else "#f43f5e"

    def get_color(val):
        if val == "-": return "#94a3b8"
        return "#10b981" if not val.startswith("-") else "#f43f5e"

    table_rows += f"""
    <tr>
        <td class="sticky-col-1"><span class="ticker-pill">{it['ticker']}</span></td>
        <td class="sticky-col-2">{it['sector']}</td>
        <td style="font-weight:700; color:#fff;">{it['price']}</td>
        <td><span style="background-color:{trend_bg}; color:{trend_color}; padding:3px 8px; border-radius:5px; font-weight:700; font-size:12px;">{it['trend']}</span></td>
        <td style="font-weight:600; color:{rs_color};">{it['rs']}</td>
        <td style="color:#cbd5e1; white-space:nowrap;">{it['ema_all']}</td>
        <td style="color:#cbd5e1;">{it['ma30w']}</td>
        <td style="color:#cbd5e1; white-space:nowrap;">{it['price_ret']}</td>
        <td style="color:#a5b4fc; white-space:nowrap;">{it['ew_ret']}</td>
        <td style="color:#38bdf8; font-weight:700; white-space:nowrap;">{it['breadth']}</td>
        <td style="color:{get_color(it['chg_1w'])}; font-weight:600;">{it['chg_1w']}</td>
        <td style="color:{get_color(it['chg_1m'])}; font-weight:600;">{it['chg_1m']}</td>
        <td style="color:{get_color(it['chg_2m'])}; font-weight:600;">{it['chg_2m']}</td>
        <td style="color:{get_color(it['chg_3m'])}; font-weight:600;">{it['chg_3m']}</td>
    </tr>
    """

full_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    * {{ box-sizing: border-box; }}
    body {{
        margin: 0;
        background-color: #060913;
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    
    .table-container {{
        width: 100%;
        max-height: 750px;
        overflow: auto;
        border: 1px solid #1a233a;
        border-radius: 12px;
        background-color: #0e1526;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }}

    table {{
        border-collapse: separate;
        border-spacing: 0;
        width: max-content;
        min-width: 100%;
        text-align: left;
    }}

    th {{
        position: sticky;
        top: 0;
        background-color: #162038;
        color: #94a3b8;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        padding: 12px 14px;
        border-bottom: 2px solid #223154;
        white-space: nowrap;
        z-index: 10;
    }}

    td {{
        padding: 12px 14px;
        font-size: 13px;
        color: #cbd5e1;
        border-bottom: 1px solid #141c30;
        white-space: nowrap;
        background-color: #0e1526;
    }}

    tr:hover td {{ background-color: #141e34 !important; }}

    .sticky-col-1 {{
        position: sticky;
        left: 0;
        z-index: 5;
        background-color: #0e1526;
        min-width: 90px;
    }}
    .sticky-col-2 {{
        position: sticky;
        left: 90px;
        z-index: 5;
        background-color: #0e1526;
        min-width: 170px;
        border-right: 2px solid #1e2942;
    }}

    th.sticky-col-1 {{ z-index: 20; background-color: #162038; }}
    th.sticky-col-2 {{ z-index: 20; background-color: #162038; border-right: 2px solid #223154; }}

    .ticker-pill {{
        background-color: #2563eb;
        color: #fff;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 800;
        font-size: 13px;
    }}

    .sub-head {{
        background-color: #111a2e;
        color: #38bdf8;
        font-size: 10px;
        text-align: center;
        border-left: 1px solid #1e2942;
    }}
</style>
</head>
<body>

<div class="table-container">
    <table>
        <thead>
            <tr>
                <th class="sticky-col-1">TICKER</th>
                <th class="sticky-col-2">SECTOR / INDUSTRY</th>
                <th>PRICE</th>
                <th>TREND</th>
                <th>RS (SPY)</th>
                <th>% VS EMA (10, 20, 30, 50, 200)</th>
                <th>% VS 30W MA</th>
                <th>PRICE CHG (1M/2M/3M)</th>
                <th>EW COMP (1M/2M/3M)</th>
                <th>% ABOVE EMA (20/50/200)</th>
                <th class="sub-head">1W BREADTH CHG</th>
                <th class="sub-head">1M BREADTH CHG</th>
                <th class="sub-head">2M BREADTH CHG</th>
                <th class="sub-head">3M BREADTH CHG</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>
</div>

</body>
</html>
"""

components.html(full_html, height=800, scrolling=False)
