import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np

# 頁面基礎設置
st.set_page_config(page_title="ETF Overview", layout="wide", initial_sidebar_state="collapsed")

# 注入高質感樣式並隱藏右上角預設的 Share / 三個點選單
st.markdown("""
<style>
    .stApp { background-color: #060913 !important; color: #f1f5f9 !important; }
    
    /* 隱藏原生頁眉與右上角干擾按鈕 */
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

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

    /* 單選按鈕組美化為分類膠囊列 (Pills) */
    div[data-testid="stRadio"] > div {
        flex-direction: row !important;
        gap: 10px !important;
    }
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

# 頂部抬頭與 Refresh 按鈕
top_left, top_right = st.columns([5, 1])
with top_left:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
        <div style="width:36px; height:36px; background:linear-gradient(135deg, #6366f1 0%, #3b82f6 100%); border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px;">📈</div>
        <h1 style="font-size:26px; font-weight:800; color:#ffffff; margin:0;">ETF Overview</h1>
    </div>
    """, unsafe_allow_html=True)

with top_right:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ----------------- 【可點擊的真實分類導航】 -----------------
CATEGORY_ETFS = {
    "Sector ETF": ["XLK", "XLC", "XLY", "XLI", "XLF", "XLV", "XLB", "XLU", "XLP", "XLRE", "XLE"],
    "Industry ETF": ["SMH", "SOXX", "IGV", "XBI", "ITA", "XHB", "KBE"],
    "Asset Class": ["SPY", "QQQ", "IWM", "TLT", "GLD", "SCHD", "VYM"],
    "Market Overview": ["XLK", "XLC", "XLY", "XLI", "XLF", "XLV", "XLB", "XLU", "XLP", "XLRE", "XLE", "SMH", "SOXX", "IGV", "SCHD", "VYM"]
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
    user_input = st.text_input("ETF 監控代碼（用逗號隔開）", value=default_pool)
    active_etfs = [x.strip().upper() for x in user_input.split(",") if x.strip()]

# 全面擴充持股字典
ETF_HOLDINGS_DB = {
    "XLK": ("資訊科技 (Tech)", ["AAPL", "MSFT", "NVDA", "AVGO", "CSCO", "ACN", "ORCL", "CRM", "AMD", "QCOM"]),
    "XLC": ("通訊服務 (Comm)", ["META", "GOOGL", "NFLX", "TMUS", "CMCSA", "DIS", "EA", "TTWO"]),
    "XLY": ("非必需消費 (Discr)", ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "BKNG", "SBUX", "TJX"]),
    "XLI": ("工業製造 (Ind)", ["GE", "CAT", "UNP", "HON", "RTX", "BA", "DE", "LMT", "ETN", "UPS"]),
    "XLF": ("金融板塊 (Fin)", ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP"]),
    "XLV": ("醫療保健 (Health)", ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "PFE", "AMGN"]),
    "XLB": ("基礎原物料 (Materials)", ["LIN", "APD", "SHW", "FCX", "ECL", "NEM", "DOW", "CTVA"]),
    "XLU": ("公用事業 (Utils)", ["NEE", "SO", "DUK", "CEG", "SRE", "AEP", "D", "PEG"]),
    "XLP": ("必需消費 (Staples)", ["PG", "COST", "WMT", "KO", "PEP", "PM", "MDLZ", "MO", "CL"]),
    "XLRE": ("房地產 (Real Est)", ["PLD", "AMT", "EQIX", "WELL", "PSA", "O", "CCI", "SPG"]),
    "XLE": ("能源板塊 (Energy)", ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO"]),
    "SMH": ("半導體 (VanEck Semis)", ["NVDA", "TSM", "AVGO", "ASML", "AMD", "QCOM", "TXN", "MU", "LRCX", "AMAT"]),
    "SOXX": ("費城半導體 (iShares Semis)", ["NVDA", "AVGO", "AMD", "QCOM", "TXN", "INTC", "ADI", "MU", "LRCX", "KLAC"]),
    "IGV": ("軟體科技 (Software)", ["MSFT", "CRM", "ORCL", "ADBE", "NOW", "INTU", "PLTR", "PANW", "SNOW"]),
    "XBI": ("生物科技 (Biotech)", ["VRTX", "REGN", "BIIB", "ALNY", "MRNA", "ILMN", "INCY"]),
    "ITA": ("國防航空 (Aerospace)", ["RTX", "LMT", "BA", "GE", "GD", "NOC", "TDG"]),
    "XHB": ("房屋建築 (Homebuilders)", ["DHI", "LEN", "NVR", "PHM", "TOL", "HD", "LOW"]),
    "KBE": ("銀行板塊 (Banks)", ["JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC"]),
    "SCHD": ("美股高息 (US Dividend)", ["AVGO", "CSCO", "HD", "TXN", "PFE", "AMGN", "PEP", "CVX", "ABBV", "KO"]),
    "VYM": ("高股息率 (High Div)", ["JPM", "XOM", "JNJ", "PG", "HD", "CVX", "MRK", "ABBV", "BAC", "WFC"]),
    "SPY": ("標普500 (S&P 500)", ["MSFT", "AAPL", "NVDA", "AMZN", "META", "GOOGL", "BRK-B", "LLY", "AVGO", "JPM"]),
    "QQQ": ("納指100 (Nasdaq 100)", ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST"]),
    "IWM": ("羅素2000 (Small Cap)", ["FTAI", "VRT", "SAIA", "ENSG", "FN", "SFM", "MSTR", "MEDP"]),
    "TLT": ("20年+美債 (Treasury)", ["ZB=F", "ZN=F"]),
    "GLD": ("黃金信託 (Gold Trust)", ["GC=F"])
}

def calc_breadth_at_idx(c_df, constituents, idx):
    cnt_20, cnt_50, cnt_200 = 0, 0, 0
    valid_count = 0
    for c in constituents:
        if c in c_df.columns:
            s = c_df[c].dropna()
            if len(s) > abs(idx) + 120:
                valid_count += 1
                sub_s = s.iloc[:len(s)+idx] if idx < 0 else s
                last_p = sub_s.iloc[-1]
                ema20 = sub_s.ewm(span=20, adjust=False).mean().iloc[-1]
                ema50 = sub_s.ewm(span=50, adjust=False).mean().iloc[-1]
                span_200 = 200 if len(sub_s) >= 200 else len(sub_s)
                ema200 = sub_s.ewm(span=span_200, adjust=False).mean().iloc[-1]
                
                if last_p > ema20: cnt_20 += 1
                if last_p > ema50: cnt_50 += 1
                if last_p > ema200: cnt_200 += 1
    if valid_count == 0:
        return None
    return (cnt_20/valid_count)*100, (cnt_50/valid_count)*100, (cnt_200/valid_count)*100

@st.cache_data(ttl=1800)
def fetch_dashboard_data(tickers):
    results = []
    spy_ret_3m = 0
    try:
        spy_raw = yf.download("SPY", period="1y", interval="1d", progress=False)
        spy_close = spy_raw['Close']
        if isinstance(spy_close, pd.DataFrame):
            spy_close = spy_close.iloc[:, 0]
        if len(spy_close) >= 63:
            spy_ret_3m = (spy_close.iloc[-1] / spy_close.iloc[-63] - 1)
    except Exception:
        pass

    for ticker in tickers:
        try:
            raw = yf.download(ticker, period="1y", interval="1d", progress=False)
            if raw.empty or 'Close' not in raw:
                continue
            
            series = raw['Close']
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            series = series.dropna()
            if len(series) < 120:
                continue
            
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
            
            sector_display, constituents = ETF_HOLDINGS_DB.get(ticker, (f"標的 ({ticker})", []))
            
            b_now_str = "N/A"
            chg_1w_str = chg_1m_str = chg_2m_str = chg_3m_str = "-"
            ew_ret = "- / - / -"
            
            if constituents:
                c_raw = yf.download(constituents, period="2y", interval="1d", progress=False)
                if not c_raw.empty and 'Close' in c_raw:
                    c_close = c_raw['Close']
                    c_df = pd.DataFrame({constituents[0]: c_close}) if isinstance(c_close, pd.Series) else c_close.copy()
                    
                    b_now = calc_breadth_at_idx(c_df, constituents, 0)
                    if b_now is not None:
                        b_now_str = f"{b_now[0]:.0f}%, {b_now[1]:.0f}%, {b_now[2]:.0f}%"
                        b_1w = calc_breadth_at_idx(c_df, constituents, -5)
                        b_1m = calc_breadth_at_idx(c_df, constituents, -21)
                        b_2m = calc_breadth_at_idx(c_df, constituents, -42)
                        b_3m = calc_breadth_at_idx(c_df, constituents, -63)
                        
                        if b_1w: chg_1w_str = f"{(b_now[1] - b_1w[1]):+.1f}%"
                        if b_1m: chg_1m_str = f"{(b_now[1] - b_1m[1]):+.1f}%"
                        if b_2m: chg_2m_str = f"{(b_now[1] - b_2m[1]):+.1f}%"
                        if b_3m: chg_3m_str = f"{(b_now[1] - b_3m[1]):+.1f}%"

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
                "sector": sector_display,
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

with st.spinner(f"⚡ 正在加載 {selected_cat} 數據並計算指標..."):
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

    tr:hover td {{
        background-color: #141e34 !important;
    }}

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
        min-width: 150px;
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
