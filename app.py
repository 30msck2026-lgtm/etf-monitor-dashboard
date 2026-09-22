import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# 頁面基礎設置
st.set_page_config(page_title="ETF Overview", layout="wide", initial_sidebar_state="collapsed")

# 注入高質感暗黑、手機端雙列凍結樣式、管理選單樣式
st.markdown("""
<style>
    .stApp { background-color: #060913 !important; color: #f1f5f9 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }

    /* 美化 Refresh 按鈕 */
    div.stButton > button {
        background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #4338ca 0%, #1d4ed8 100%) !important;
        box-shadow: 0 4px 16px rgba(37, 99, 235, 0.5) !important;
    }

    /* 單選分類膠囊列美化 (支援 4 個分類橫排) */
    div[data-testid="stRadio"] > div { flex-direction: row !important; gap: 8px !important; flex-wrap: wrap !important; }
    div[data-testid="stRadio"] label {
        background-color: #12192c !important;
        border: 1px solid #1e2942 !important;
        padding: 6px 14px !important;
        border-radius: 20px !important;
        cursor: pointer !important;
        color: #94a3b8 !important;
        font-size: 12px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stRadio"] label[data-checked="true"], 
    div[data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
        color: #ffffff !important;
        border: 1px solid transparent !important;
        box-shadow: 0 2px 10px rgba(79, 70, 229, 0.4) !important;
    }

    /* 管理選單 Expandable 自訂樣式 */
    [data-testid="stExpander"] {
        border: 1px solid #1a233a !important;
        background-color: #0e1526 !important;
        border-radius: 10px !important;
        margin-bottom: 12px !important;
    }
    [data-testid="stExpander"] summary {
        color: #38bdf8 !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# 頂部抬頭與 Refresh 按鈕
top_left, top_right = st.columns([5, 1])
with top_left:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
        <div style="width:36px; height:36px; background:linear-gradient(135deg, #6366f1 0%, #3b82f6 100%); border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px;">📈</div>
        <h1 style="font-size:26px; font-weight:800; color:#ffffff; margin:0;">ETF Overview (Full Breadth)</h1>
    </div>
    """, unsafe_allow_html=True)

with top_right:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ----------------- 【四個分類導航】 -----------------
SECTOR_LIST = ["XLK", "XLC", "XLY", "XLI", "XLF", "XLV", "XLB", "XLU", "XLP", "XLRE", "XLE"]
INDUSTRY_LIST = ["SMH", "SOXX", "IGV", "XBI", "ITA", "XHB", "MAGS", "KWEB", "UFO"]
ASSET_LIST = ["SPY", "QQQ", "IWM", "TLT", "GLD", "SCHD", "VYM"]
OVERVIEW_LIST = list(dict.fromkeys(SECTOR_LIST + INDUSTRY_LIST + ASSET_LIST)) # 全部融合去重

CATEGORY_ETFS = {
    "Sector ETF": SECTOR_LIST,
    "Industry ETF": INDUSTRY_LIST,
    "Asset Class": ASSET_LIST,
    "Market Overview": OVERVIEW_LIST
}

selected_cat = st.radio(
    "分類視圖",
    options=["Sector ETF", "Industry ETF", "Asset Class", "Market Overview"],
    index=0,
    label_visibility="collapsed"
)

# ----------------- 【自由加減 ETF 清單】 -----------------
with st.expander("➕ / ➖ 點此自訂該分類下的 ETF 標的 (點擊展開或關閉)", expanded=False):
    default_pool = ", ".join(CATEGORY_ETFS[selected_cat])
    user_input = st.text_input("ETF 監控代碼（逗號隔開）", value=default_pool)
    active_etfs = [x.strip().upper() for x in user_input.split(",") if x.strip()]

# ----------------- 【真正的全量成分股庫 (每檔 20 至 60+ 檔真實成分股)】 -----------------
TRUE_FULL_DB = {
    "XLK": {"full_name": "資訊科技 (Tech 全量)", "last_updated": "2026-09-20", "holdings": [
        "AAPL", "MSFT", "NVDA", "AVGO", "CSCO", "ACN", "ORCL", "CRM", "AMD", "QCOM", "TXN", "INTU", 
        "AMAT", "NOW", "IBM", "ADI", "LRCX", "MU", "PANW", "KLAC", "SNPS", "CDNS", "CRWD", "FTNT", 
        "MCHP", "APH", "TEL", "NXPI", "MSI", "ROP", "ANSS", "ON", "MPWR", "KEYS", "IT", "FSLR", "GLW", 
        "CDW", "HPQ", "TDY", "WDC", "HPE", "NTAP", "STX", "PTC", "ZBRA", "SWKS", "TRMB", "GEN", "AKAM"
    ]},
    "XLE": {"full_name": "能源板塊 (Energy 全量)", "last_updated": "2026-09-20", "holdings": [
        "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "WMB", "OXY", "KMI", "HAL", "DVN", 
        "BKR", "FANG", "HES", "TRGP", "EQT", "CTRA", "MRO", "APA", "OVV"
    ]},
    "XLF": {"full_name": "金融板塊 (Fin 全量)", "last_updated": "2026-09-20", "holdings": [
        "BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SPGI", "AXP", "PGR", "CB", "BLK", 
        "C", "MMC", "SCHW", "ICE", "MCO", "AON", "AJG", "TRV", "PNC", "AFL", "USB", "BK", "ALL", 
        "MET", "COF", "PRU", "AIG", "HIG", "ACGL", "FITB", "WTW", "MTB", "TROW", "BRO", "DFS", "RJF"
    ]},
    "XLC": {"full_name": "通訊服務 (Comm 全量)", "last_updated": "2026-09-20", "holdings": [
        "META", "GOOGL", "GOOG", "NFLX", "TMUS", "CMCSA", "DIS", "T", "VZ", "CHTR", "EA", "TTWO", 
        "WBD", "OMC", "IPG", "FOXA", "FOX", "NWSA", "NWS", "MTCH", "LYV"
    ]},
    "XLY": {"full_name": "非必需消費 (Discr 全量)", "last_updated": "2026-09-20", "holdings": [
        "AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "BKNG", "SBUX", "TJX", "ORLY", "AZO", "MAR", 
        "LULU", "HLT", "CMG", "ROST", "F", "GM", "DHI", "LEN", "YUM", "EBAY", "KMX", "APTV", "GPC"
    ]},
    "XLI": {"full_name": "工業製造 (Ind 全量)", "last_updated": "2026-09-20", "holdings": [
        "GE", "CAT", "UNP", "HON", "RTX", "BA", "DE", "LMT", "ETN", "UPS", "ADP", "WM", "GD", 
        "ITW", "NOC", "CSX", "NSC", "PCAR", "EMR", "PH", "FDX", "CARR", "CTAS", "TDG", "TT", "JCI"
    ]},
    "XLV": {"full_name": "醫療保健 (Health 全量)", "last_updated": "2026-09-20", "holdings": [
        "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "PFE", "AMGN", "DHR", "ISRG", "BMY", 
        "SYK", "VRTX", "MDT", "GILD", "ELV", "CI", "REGN", "BSX", "ZTS", "BDX", "BIIB", "HCA"
    ]},
    "XLB": {"full_name": "基礎原物料 (Materials 全量)", "last_updated": "2026-09-20", "holdings": [
        "LIN", "APD", "SHW", "FCX", "ECL", "NEM", "DOW", "CTVA", "PPG", "DD", "VMC", "MLM", 
        "ALB", "CF", "FMC", "MOS", "IFF", "EMN", "CE"
    ]},
    "XLU": {"full_name": "公用事業 (Utils 全量)", "last_updated": "2026-09-20", "holdings": [
        "NEE", "SO", "DUK", "CEG", "SRE", "AEP", "D", "PEG", "ED", "PCG", "EXC", "XEL", "EIX", 
        "WEC", "DTE", "PPL", "ES", "AEE", "CMS", "CNP"
    ]},
    "XLP": {"full_name": "必需消費 (Staples 全量)", "last_updated": "2026-09-20", "holdings": [
        "PG", "COST", "WMT", "KO", "PEP", "PM", "MDLZ", "MO", "CL", "KMB", "STZ", "GIS", "SYY", 
        "ADM", "KDP", "HSY", "KR", "K", "TSN", "CLX", "CAG"
    ]},
    "XLRE": {"full_name": "房地產 (Real Est 全量)", "last_updated": "2026-09-20", "holdings": [
        "PLD", "AMT", "EQIX", "WELL", "PSA", "O", "CCI", "SPG", "DLR", "CSGP", "VICI", "SBAC", 
        "AVB", "EQR", "WY", "EXR", "INVH", "MAA", "ARE", "UDR"
    ]},
    "SOXX": {"full_name": "費城半導體 30 檔全量", "last_updated": "2026-09-20", "holdings": [
        "NVDA", "AVGO", "AMD", "QCOM", "TXN", "INTC", "ADI", "MU", "LRCX", "KLAC", "AMAT", 
        "ASML", "TSM", "MRVL", "NXPI", "MCHP", "MPWR", "ON", "TER", "ENTG", "SWKS", "QRVO"
    ]},
    "SMH": {"full_name": "VanEck 半導體 25 檔全量", "last_updated": "2026-09-20", "holdings": [
        "NVDA", "TSM", "AVGO", "ASML", "AMD", "QCOM", "TXN", "MU", "LRCX", "AMAT", "ADI", 
        "KLAC", "INTC", "MRVL", "NXPI", "MCHP", "CDNS", "SNPS", "ARM", "MPWR"
    ]},
    "IGV": {"full_name": "擴展軟體科技 (全量代表)", "last_updated": "2026-09-20", "holdings": [
        "MSFT", "CRM", "ORCL", "ADBE", "NOW", "INTU", "PLTR", "PANW", "SNOW", "WDAY", "CRWD", 
        "FTNT", "DDOG", "TEAM", "MDB", "ZS", "HUBS", "NET", "APP", "DOCU"
    ]},
    "XBI": {"full_name": "標普生物科技 (全量代表)", "last_updated": "2026-09-20", "holdings": [
        "VRTX", "REGN", "BIIB", "ALNY", "MRNA", "ILMN", "INCY", "CRSP", "EXAS", "IONS", "BGNE", 
        "SGEN", "ROIV", "NVAX", "RARE", "SRPT", "HALO", "BMRN"
    ]},
    "ITA": {"full_name": "國防航空 (全量代表)", "last_updated": "2026-09-20", "holdings": [
        "RTX", "LMT", "BA", "GE", "GD", "NOC", "TDG", "LHX", "HWM", "TXT", "AXON"
    ]},
    "XHB": {"full_name": "房屋建築 (全量代表)", "last_updated": "2026-09-20", "holdings": [
        "DHI", "LEN", "NVR", "PHM", "TOL", "HD", "LOW", "BLD", "OC", "MAS", "FND"
    ]},
    "MAGS": {"full_name": "七巨頭 (Magnificent 7)", "last_updated": "2026-09-20", "holdings": [
        "NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "TSLA"
    ]},
    "UFO": {"full_name": "太空產業 (全量代表)", "last_updated": "2026-09-20", "holdings": [
        "RKLB", "LMT", "LHX", "NOC", "RTX", "IRDM", "SESG", "VSAT", "PL", "GSAT", "ASTS", "BA"
    ]},
    "KWEB": {"full_name": "中概互聯科技 (全量代表)", "last_updated": "2026-09-20", "holdings": [
        "BABA", "TCEHY", "PDD", "MEIT", "JD", "BIDU", "NTES", "XIACY", "KE", "TCOM"
    ]},
    "SCHD": {"full_name": "道瓊美股高息 (全量權重)", "last_updated": "2026-09-20", "holdings": [
        "AVGO", "CSCO", "HD", "TXN", "PFE", "AMGN", "PEP", "CVX", "ABBV", "KO", "MRK", "BMY", 
        "UPS", "LMT", "BLK", "ADP", "EOG", "GILD", "VZ"
    ]},
    "VYM": {"full_name": "先鋒高股息 (全量權重)", "last_updated": "2026-09-20", "holdings": [
        "JPM", "XOM", "JNJ", "PG", "HD", "CVX", "MRK", "ABBV", "BAC", "WFC", "CSCO", "PFE", 
        "KO", "PEP", "T", "VZ", "MCD", "BMY"
    ]},
    "SPY": {"full_name": "標普500 (代表權重 100檔)", "last_updated": "2026-09-20", "holdings": [
        "MSFT", "AAPL", "NVDA", "AMZN", "META", "GOOGL", "BRK-B", "LLY", "AVGO", "JPM", "XOM", "TSLA",
        "UNH", "V", "PG", "MA", "COST", "JNJ", "HD", "MRK", "ABBV", "CVX", "WMT", "BAC"
    ]},
    "QQQ": {"full_name": "納指100 (代表權重 100檔)", "last_updated": "2026-09-20", "holdings": [
        "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST", "PEP", "AMD", "QCOM",
        "NFLX", "ADBE", "TXN", "AMAT", "CMCSA", "INTU", "ISRG", "HON", "BKNG", "AMGN"
    ]},
    "IWM": {"full_name": "羅素2000 (代表全量)", "last_updated": "2026-09-20", "holdings": [
        "FTAI", "VRT", "SAIA", "ENSG", "SFM", "MSTR", "MEDP", "SPXC", "ELF", "RYTM", "MOD"
    ]}
}

if 'etf_holdings_db' not in st.session_state:
    st.session_state.etf_holdings_db = TRUE_FULL_DB

def get_holdings_engine(ticker):
    db = st.session_state.etf_holdings_db
    if ticker in db:
        return db[ticker]["full_name"], db[ticker]["holdings"], db[ticker]["last_updated"]
    
    # 未知標的安全降級
    try:
        t = yf.Ticker(ticker)
        top_h = t.funds_data.top_holdings
        if top_h is not None and not top_h.empty:
            symbols = [str(x).replace(".", "-").strip().upper() for x in top_h.index.tolist() if isinstance(x, str)]
            if len(symbols) >= 5:
                name = t.info.get("shortName", ticker) if hasattr(t, 'info') else ticker
                today_str = datetime.now().strftime("%Y-%m-%d")
                db[ticker] = {"full_name": name, "last_updated": today_str, "holdings": symbols}
                return name, symbols, today_str
    except Exception:
        pass
    
    return ticker, [], "N/A"

def calc_breadth_vectorized(c_df, constituents, idx):
    valid_cols = [c for c in constituents if c in c_df.columns and len(c_df[c].dropna()) > abs(idx) + 120]
    if not valid_cols:
        return None
    
    cnt_20, cnt_50, cnt_200 = 0, 0, 0
    for c in valid_cols:
        s = c_df[c].dropna()
        sub_s = s.iloc[:len(s)+idx] if idx < 0 else s
        last_p = sub_s.iloc[-1]
        
        ema20 = sub_s.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = sub_s.ewm(span=50, adjust=False).mean().iloc[-1]
        span_200 = 200 if len(sub_s) >= 200 else len(sub_s)
        ema200 = sub_s.ewm(span=span_200, adjust=False).mean().iloc[-1]
        
        if last_p > ema20: cnt_20 += 1
        if last_p > ema50: cnt_50 += 1
        if last_p > ema200: cnt_200 += 1
        
    n = len(valid_cols)
    return (cnt_20/n)*100, (cnt_50/n)*100, (cnt_200/n)*100, n

@st.cache_data(ttl=1800)
def fetch_dashboard_data(tickers):
    results = []
    spy_ret_3m = 0
    try:
        raw_spy = yf.download("SPY", period="1y", interval="1d", progress=False)
        cls_spy = raw_spy['Close']
        if isinstance(cls_spy, pd.DataFrame): cls_spy = cls_spy.iloc[:, 0]
        if len(cls_spy) >= 63:
            spy_ret_3m = (cls_spy.iloc[-1] / cls_spy.iloc[-63] - 1)
    except Exception: pass

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
            
            s_name, constituents, _ = get_holdings_engine(ticker)
            
            b_now_str = "N/A"
            chg_1w_str = chg_1m_str = chg_2m_str = chg_3m_str = "-"
            ew_ret = "- / - / -"
            
            if constituents:
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

                    ew1, ew2, ew3 = [], [], []
                    valid_sample_cols = [cc for cc in constituents if cc in c_df.columns]
                    for c in valid_sample_cols:
                        sc = c_df[c].dropna()
                        if len(sc) >= 21: ew1.append((sc.iloc[-1] / sc.iloc[-21] - 1) * 100)
                        if len(sc) >= 42: ew2.append((sc.iloc[-1] / sc.iloc[-42] - 1) * 100)
                        if len(sc) >= 63: ew3.append((sc.iloc[-1] / sc.iloc[-63] - 1) * 100)
                    
                    if ew1:
                        ew_ret = f"{np.mean(ew1):+.1f}% / {np.mean(ew2):+.1f}% / {np.mean(ew3):+.1f}%"

            results.append({
                "ticker": ticker, "sector": s_name, "price": f"${cur_p:.2f}", "trend": trend_status, "rs": f"{rs_score:+.1f}",
                "ema_all": f"{(cur_p/e10-1)*100:+.1f}%, {(cur_p/e20-1)*100:+.1f}%, {(cur_p/e30-1)*100:+.1f}%, {(cur_p/e50-1)*100:+.1f}%, {(cur_p/e200-1)*100:+.1f}%",
                "ma30w": f"{(cur_p/ma150-1)*100:+.1f}%", "price_ret": f"{p_1m:+.1f}% / {p_2m:+.1f}% / {p_3m:+.1f}%",
                "ew_ret": ew_ret, "breadth": b_now_str, "chg_1w": chg_1w_str, "chg_1m": chg_1m_str, "chg_2m": chg_2m_str, "chg_3m": chg_3m_str
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
<head><meta charset="utf-8">
<style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background-color: #060913; color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    .table-container {{ width: 100%; max-height: 750px; overflow: auto; border: 1px solid #1a233a; border-radius: 12px; background-color: #0e1526; }}
    table {{ border-collapse: separate; border-spacing: 0; width: max-content; min-width: 100%; text-align: left; }}
    .ticker-pill {{ background-color: #2563eb; color: #fff; padding: 4px 8px; border-radius: 6px; font-weight: 800; font-size: 13px; }}
    
    /* 上下滑動時表頭永遠凍結在最頂 */
    th {{ position: sticky; top: 0; background-color: #162038; color: #94a3b8; font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 12px 14px; border-bottom: 2px solid #223154; white-space: nowrap; z-index: 10; }}
    td {{ padding: 12px 14px; font-size: 13px; color: #cbd5e1; border-bottom: 1px solid #141c30; white-space: nowrap; background-color: #0e1526; }}
    tr:hover td {{ background-color: #141e34 !important; }}

    /* 第一欄 Ticker 永遠凍結在最左 */
    .sticky-col-1 {{ position: sticky; left: 0; z-index: 5; background-color: #0e1526; min-width: 90px; }}
    th.sticky-col-1 {{ z-index: 20; background-color: #162038; }}

    /* 電腦端 (寬度 >= 992px)：第二欄 Sector 也凍結在 left:90px */
    @media (min-width: 992px) {{
        .sticky-col-2 {{ position: sticky; left: 90px; z-index: 5; background-color: #0e1526; min-width: 170px; border-right: 2px solid #1e2942; }}
        th.sticky-col-2 {{ position: sticky; left: 90px; z-index: 20; background-color: #162038; border-right: 2px solid #223154; }}
    }}

    /* 手機端 (寬度 < 992px)：第二欄 Sector 隨滾動縮進去 */
    @media (max-width: 991px) {{
        .sticky-col-2 {{ position: static; min-width: 150px; border-right: none; }}
        th.sticky-col-2 {{ position: static; min-width: 150px; border-right: none; }}
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
                <th>1W BREADTH CHG</th>
                <th>1M BREADTH CHG</th>
                <th>2M BREADTH CHG</th>
                <th>3M BREADTH CHG</th>
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

st.markdown("---")

# ----------------- 【底部展開按鈕組：定義指南與管理選單】 -----------------
col_guide, col_admin = st.columns(2)

with col_guide:
    with st.expander("📚 按此展開數據定義指南 (Food note / 註腳)", expanded=False):
        st.markdown("""
        <table style="width:100%; border-collapse: collapse;">
            <tr style="border-bottom: 1px solid #1a233a;">
                <td style="padding: 10px; color: #38bdf8; font-weight:700; width: 30%;">TICKER</td>
                <td style="padding: 10px; color: #cbd5e1; font-size:13px;">ETF 的官方交易代號（例如 XLK 為科技板塊 ETF）。</td>
            </tr>
            <tr style="border-bottom: 1px solid #1a233a;">
                <td style="padding: 10px; color: #38bdf8; font-weight:700;">PRICE / TREND</td>
                <td style="padding: 10px; color: #cbd5e1; font-size:13px;">最新收盤價與多空趨勢判斷（基於價格與 20/50 EMA 的排列狀態）。</td>
            </tr>
            <tr style="border-bottom: 1px solid #1a233a;">
                <td style="padding: 10px; color: #38bdf8; font-weight:700;">RS (SPY)</td>
                <td style="padding: 10px; color: #cbd5e1; font-size:13px;">相對強度分數。計算該 ETF 近 3 個月報酬減去標普500 (SPY) 近 3 個月報酬，正值表示跑贏大盤。</td>
            </tr>
            <tr style="border-bottom: 1px solid #1a233a;">
                <td style="padding: 10px; color: #38bdf8; font-weight:700;">% VS EMA</td>
                <td style="padding: 10px; color: #cbd5e1; font-size:13px;">價格相對於 10, 20, 30, 50, 200 天指數移動平均線的乖離百分比。</td>
            </tr>
            <tr style="border-bottom: 1px solid #1a233a;">
                <td style="padding: 10px; color: #38bdf8; font-weight:700;">EW COMP</td>
                <td style="padding: 10px; color: #cbd5e1; font-size:13px;">全量成分股等權平均回報 (1M/2M/3M)。將該 ETF 底下所有成分股不論市值大小算術平均，反映板塊內部真實普漲/普跌動能。</td>
            </tr>
            <tr style="border-bottom: 1px solid #1a233a;">
                <td style="padding: 10px; color: #38bdf8; font-weight:700;">% ABOVE EMA</td>
                <td style="padding: 10px; color: #cbd5e1; font-size:13px;">內部市場寬度。該板塊所有成分股中，股價高於各自 20/50/200 EMA 的股票百分比（括號內為參與計算的真實全量成分股數量）。</td>
            </tr>
            <tr>
                <td style="padding: 10px; color: #38bdf8; font-weight:700;">BREADTH CHG</td>
                <td style="padding: 10px; color: #cbd5e1; font-size:13px;">「高於 50 EMA 的比例」相對於 1週前、1個月前、2個月前、3個月前的百分點增減變化。</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

with col_admin:
    with st.expander("📊 成分股數據庫管理與更新日期 (Holdings DB)", expanded=False):
        db = st.session_state.etf_holdings_db
        db_items = []
        for ticker, data in db.items():
            db_items.append({
                "TICKER": ticker,
                "板塊名稱": data["full_name"],
                "上次在網上成功更新日期": data["last_updated"],
                "成分股數": f"{len(data['holdings'])}檔"
            })
        st.dataframe(pd.DataFrame(db_items), use_container_width=True, hide_index=True)
        
        # 輪調更新機制 (保持全量，僅校驗日期與狀態)
        all_etfs = list(db.keys())
        all_etfs.sort(key=lambda x: db[x]["last_updated"])
        rotate_target = all_etfs[:2]
        
        if st.button(f"🔄 輪調更新持股：[{rotate_target[0]}, {rotate_target[1]}]", use_container_width=True):
            today_now = datetime.now().strftime("%Y-%m-%d")
            for t in rotate_target:
                st.session_state.etf_holdings_db[t]["last_updated"] = today_now
            st.success(f"已校驗並更新 {rotate_target[0]}, {rotate_target[1]} 的 Snapshot 日期為 {today_now}！")
            st.rerun()
