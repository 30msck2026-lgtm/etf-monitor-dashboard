import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np

# 頁面基礎設置
st.set_page_config(page_title="ETF Overview", layout="wide", initial_sidebar_state="collapsed")

# 隱藏 Streamlit 原生多餘空白
st.markdown("""
<style>
    .stApp { background-color: #060913 !important; color: #f1f5f9 !important; }
    header[data-testid="stHeader"] { background: transparent !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# 頂部抬頭與 Refresh 按鈕
top_left, top_right = st.columns([5, 1])
with top_left:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
        <div style="width:36px; height:36px; background:linear-gradient(135deg, #6366f1 0%, #3b82f6 100%); border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px;">📈</div>
        <h1 style="font-size:26px; font-weight:800; color:#ffffff; margin:0;">ETF Overview</h1>
    </div>
    <div style="display:flex; gap:10px; margin-bottom:12px;">
        <span style="background:linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%); color:white; padding:5px 16px; border-radius:20px; font-size:12px; font-weight:600;">Sector ETF</span>
        <span style="background-color:#12192c; color:#94a3b8; border:1px solid #1e2942; padding:5px 16px; border-radius:20px; font-size:12px; font-weight:600;">Industry ETF</span>
        <span style="background-color:#12192c; color:#94a3b8; border:1px solid #1e2942; padding:5px 16px; border-radius:20px; font-size:12px; font-weight:600;">Asset Class</span>
        <span style="background-color:#12192c; color:#94a3b8; border:1px solid #1e2942; padding:5px 16px; border-radius:20px; font-size:12px; font-weight:600;">Market Overview</span>
    </div>
    """, unsafe_allow_html=True)

with top_right:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ----------------- 【直接在介面加減 ETF】 -----------------
with st.expander("➕ / ➖ 點此管理監控 ETF 清單 (點擊展開或關閉)", expanded=False):
    default_tickers = "XLK, XLC, XLY, XLI, XLF, XLV, XLB, XLU, XLP, XLRE, XLE, SMH"
    user_input = st.text_input("輸入你想監控的 ETF 代號（逗號隔開）", value=default_tickers)
    selected_etfs = [x.strip().upper() for x in user_input.split(",") if x.strip()]

SECTOR_MAP = {
    "XLK": ("資訊科技 (Tech)", ["AAPL", "MSFT", "NVDA", "AVGO", "CSCO", "ACN", "ORCL", "CRM", "AMD"]),
    "XLC": ("通訊服務 (Comm)", ["META", "GOOGL", "NFLX", "TMUS", "CMCSA", "DIS", "EA"]),
    "XLY": ("非必需消費 (Discr)", ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "BKNG"]),
    "XLI": ("工業製造 (Ind)", ["GE", "CAT", "UNP", "HON", "RTX", "BA", "DE", "LMT"]),
    "XLF": ("金融服務 (Fin)", ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS"]),
    "XLV": ("醫療保健 (Health)", ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "PFE"]),
    "XLB": ("原物料 (Materials)", ["LIN", "APD", "SHW", "FCX", "ECL", "NEM", "DOW"]),
    "XLU": ("公用事業 (Utils)", ["NEE", "SO", "DUK", "CEG", "SRE", "AEP"]),
    "XLP": ("必需消費 (Staples)", ["PG", "COST", "WMT", "KO", "PEP", "PM"]),
    "XLRE": ("房地產 (Real Est)", ["PLD", "AMT", "EQIX", "WELL", "PSA", "O"]),
    "XLE": ("能源板塊 (Energy)", ["XOM", "CVX", "COP", "EOG", "SLB", "MPC"]),
    "SMH": ("半導體 (Semis)", ["NVDA", "TSM", "AVGO", "ASML", "AMD", "QCOM", "TXN", "MU"])
}

def calc_breadth_at_idx(c_df, constituents, idx):
    cnt_20, cnt_50, cnt_200 = 0, 0, 0
    total = len(constituents)
    for c in constituents:
        if c in c_df:
            s = c_df[c].dropna()
            if len(s) > abs(idx) + 200:
                sub_s = s.iloc[:len(s)+idx] if idx < 0 else s
                last_p = sub_s.iloc[-1]
                if last_p > sub_s.ewm(span=20, adjust=False).mean().iloc[-1]: cnt_20 += 1
                if last_p > sub_s.ewm(span=50, adjust=False).mean().iloc[-1]: cnt_50 += 1
                if last_p > sub_s.ewm(span=200, adjust=False).mean().iloc[-1]: cnt_200 += 1
    return (cnt_20/total)*100, (cnt_50/total)*100, (cnt_200/total)*100

@st.cache_data(ttl=1800)
def fetch_dashboard_data(tickers):
    results = []
    spy = yf.download("SPY", period="1y", interval="1d", progress=False)['Close']
    spy_ret_3m = (spy.iloc[-1] / spy.iloc[-63] - 1).values[0] if len(spy) >= 63 else 0

    for ticker in tickers:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)['Close']
        if df.empty or len(df) < 200:
            continue
        
        series = df.iloc[:, 0] if isinstance(df, pd.DataFrame) else df
        cur_p = series.iloc[-1]
        
        e10 = series.ewm(span=10, adjust=False).mean().iloc[-1]
        e20 = series.ewm(span=20, adjust=False).mean().iloc[-1]
        e30 = series.ewm(span=30, adjust=False).mean().iloc[-1]
        e50 = series.ewm(span=50, adjust=False).mean().iloc[-1]
        e200 = series.ewm(span=200, adjust=False).mean().iloc[-1]
        ma150 = series.rolling(window=150).mean().iloc[-1]
        
        p_1m = (cur_p / series.iloc[-21] - 1) * 100 if len(series) >= 21 else 0
        p_2m = (cur_p / series.iloc[-42] - 1) * 100 if len(series) >= 42 else 0
        p_3m = (cur_p / series.iloc[-63] - 1) * 100 if len(series) >= 63 else 0
        
        rs_score = ((p_3m / 100) - spy_ret_3m) * 100
        trend_status = "UP ▲" if (cur_p > e50 and e20 > e50) else ("DOWN ▼" if (cur_p < e50 and e20 < e50) else "RNG ◼")
        
        sector_name, constituents = SECTOR_MAP.get(ticker, (ticker, []))
        b_now = (0, 0, 0)
        chg_1w = chg_1m = chg_2m = chg_3m = 0.0
        ew_ret = "- / - / -"
        
        if constituents:
            c_df = yf.download(constituents, period="2y", interval="1d", progress=False)['Close']
            b_now = calc_breadth_at_idx(c_df, constituents, 0)
            b_1w = calc_breadth_at_idx(c_df, constituents, -5)
            b_1m = calc_breadth_at_idx(c_df, constituents, -21)
            b_2m = calc_breadth_at_idx(c_df, constituents, -42)
            b_3m = calc_breadth_at_idx(c_df, constituents, -63)
            
            chg_1w = b_now[1] - b_1w[1]
            chg_1m = b_now[1] - b_1m[1]
            chg_2m = b_now[1] - b_2m[1]
            chg_3m = b_now[1] - b_3m[1]

            ew1 = np.mean([(c_df[c].iloc[-1]/c_df[c].iloc[-21]-1)*100 for c in constituents if c in c_df])
            ew2 = np.mean([(c_df[c].iloc[-1]/c_df[c].iloc[-42]-1)*100 for c in constituents if c in c_df])
            ew3 = np.mean([(c_df[c].iloc[-1]/c_df[c].iloc[-63]-1)*100 for c in constituents if c in c_df])
            ew_ret = f"{ew1:+.1f}% / {ew2:+.1f}% / {ew3:+.1f}%"

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
            "breadth": f"{b_now[0]:.0f}%, {b_now[1]:.0f}%, {b_now[2]:.0f}%",
            "chg_1w": f"{chg_1w:+.1f}%",
            "chg_1m": f"{chg_1m:+.1f}%",
            "chg_2m": f"{chg_2m:+.1f}%",
            "chg_3m": f"{chg_3m:+.1f}%"
        })
    return results

with st.spinner("⚡ 正在計算市場寬度與多週期均線指標..."):
    items = fetch_dashboard_data(selected_etfs)

# 生成單一表格數據行（結合雙向凍結）
table_rows = ""
for it in items:
    trend_color = "#10b981" if "UP" in it["trend"] else ("#ef4444" if "DOWN" in it["trend"] else "#94a3b8")
    trend_bg = "rgba(16, 185, 129, 0.15)" if "UP" in it["trend"] else ("rgba(239, 68, 68, 0.15)" if "DOWN" in it["trend"] else "rgba(148, 163, 184, 0.15)")
    rs_color = "#10b981" if not it["rs"].startswith("-") else "#f43f5e"

    w1_color = "#10b981" if not it["chg_1w"].startswith("-") else "#f43f5e"
    m1_color = "#10b981" if not it["chg_1m"].startswith("-") else "#f43f5e"
    m2_color = "#10b981" if not it["chg_2m"].startswith("-") else "#f43f5e"
    m3_color = "#10b981" if not it["chg_3m"].startswith("-") else "#f43f5e"

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
        <td style="color:{w1_color}; font-weight:600;">{it['chg_1w']}</td>
        <td style="color:{m1_color}; font-weight:600;">{it['chg_1m']}</td>
        <td style="color:{m2_color}; font-weight:600;">{it['chg_2m']}</td>
        <td style="color:{m3_color}; font-weight:600;">{it['chg_3m']}</td>
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
    
    /* 雙向滾動容器：固定高度產生垂直捲軸，超出寬度產生水平捲軸 */
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

    /* 1. 上下滑動時表頭永遠凍結在最頂 */
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

    /* 2. 左右滾動時，左側 Ticker 與 Sector 永遠凍結固定在左邊 */
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
        min-width: 140px;
        border-right: 2px solid #1e2942;
    }}

    /* 頂角交叉處層級最高，避免滾動覆蓋 */
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

    /* 分組次表頭美化 */
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

# 以獨立全功能容器渲染
components.html(full_html, height=800, scrolling=False)
