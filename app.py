import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup

# 頁面基礎設置
st.set_page_config(page_title="ETF Overview", layout="wide", initial_sidebar_state="collapsed")

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

# ----------------- 【自由加減 ETF 清單】 -----------------
with st.expander("➕ / ➖ 點此管理監控 ETF 清單 (點擊展開或關閉)", expanded=False):
    default_tickers = "XLK, XLC, XLY, XLI, XLF, XLV, XLB, XLU, XLP, XLRE, XLE, SMH, IGV, SOXX, SCHD, VYM"
    user_input = st.text_input("輸入你想監控的 ETF 代號（逗號隔開，支援任意美股 ETF）", value=default_tickers)
    selected_etfs = [x.strip().upper() for x in user_input.split(",") if x.strip()]

# 預設基礎板塊名稱字典（作為友好顯示）
SECTOR_NAMES = {
    "XLK": "資訊科技 (Tech)", "XLC": "通訊服務 (Comm)", "XLY": "非必需消費 (Discr)",
    "XLI": "工業製造 (Ind)", "XLF": "金融服務 (Fin)", "XLV": "醫療保健 (Health)",
    "XLB": "原物料 (Materials)", "XLU": "公用事業 (Utils)", "XLP": "必需消費 (Staples)",
    "XLRE": "房地產 (Real Est)", "XLE": "能源板塊 (Energy)", "SMH": "半導體 (Semis)",
    "SOXX": "半導體 (Semis)", "IGV": "軟體科技 (Software)", "SCHD": "美股高息 (Dividend)",
    "VYM": "高股息率 (High Div)", "QQQ": "納指科技 (Nasdaq)", "IWM": "小型股 (Russell)"
}

# 自動聯網抓取任意 ETF 的前 10 大成分股
@st.cache_data(ttl=86400) # 成分股名單每日快取一次
def get_etf_holdings_auto(ticker):
    try:
        # 方法 A: 嘗試使用 yfinance 原生持股介面
        etf_obj = yf.Ticker(ticker)
        try:
            holdings_df = etf_obj.funds_data.top_holdings
            if holdings_df is not None and not holdings_df.empty:
                syms = [s.replace(".", "-") for s in holdings_df.index.tolist() if isinstance(s, str)]
                if len(syms) >= 5:
                    return syms[:10]
        except Exception:
            pass

        # 方法 B: 備用爬蟲抓取 Yahoo Finance Holdings 頁面
        url = f"https://finance.yahoo.com/quote/{ticker}/holdings"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            tickers_found = []
            for a in links:
                href = a['href']
                if "/quote/" in href and not href.endswith(f"/quote/{ticker}"):
                    sym = href.split("/quote/")[1].split("?")[0].replace(".", "-").strip().upper()
                    if sym and sym.isalpha() and len(sym) <= 5 and sym != ticker:
                        if sym not in tickers_found:
                            tickers_found.append(sym)
                if len(tickers_found) >= 10:
                    break
            if len(tickers_found) >= 5:
                return tickers_found[:10]
    except Exception:
        pass
    return []

def calc_breadth_at_idx(c_df, constituents, idx):
    cnt_20, cnt_50, cnt_200 = 0, 0, 0
    valid_count = 0
    for c in constituents:
        if c in c_df:
            s = c_df[c].dropna()
            if len(s) > abs(idx) + 150:
                valid_count += 1
                sub_s = s.iloc[:len(s)+idx] if idx < 0 else s
                last_p = sub_s.iloc[-1]
                if last_p > sub_s.ewm(span=20, adjust=False).mean().iloc[-1]: cnt_20 += 1
                if last_p > sub_s.ewm(span=50, adjust=False).mean().iloc[-1]: cnt_50 += 1
                if last_p > sub_s.ewm(span=200, adjust=False).mean().iloc[-1]: cnt_200 += 1
    if valid_count == 0:
        return None
    return (cnt_20/valid_count)*100, (cnt_50/valid_count)*100, (cnt_200/valid_count)*100

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
        
        # 標籤顯示
        sector_display = SECTOR_NAMES.get(ticker, f"ETF ({ticker})")
        
        # 自動聯網尋找成分股
        constituents = get_etf_holdings_auto(ticker)
        
        b_now_str = "N/A"
        chg_1w_str = chg_1m_str = chg_2m_str = chg_3m_str = "-"
        ew_ret = "- / - / -"
        
        if constituents:
            c_df = yf.download(constituents, period="2y", interval="1d", progress=False)['Close']
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

            ew1 = [((c_df[c].iloc[-1]/c_df[c].iloc[-21]-1)*100) for c in constituents if c in c_df and len(c_df[c].dropna())>=21]
            ew2 = [((c_df[c].iloc[-1]/c_df[c].iloc[-42]-1)*100) for c in constituents if c in c_df and len(c_df[c].dropna())>=42]
            ew3 = [((c_df[c].iloc[-1]/c_df[c].iloc[-63]-1)*100) for c in constituents if c in c_df and len(c_df[c].dropna())>=63]
            
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
    return results

with st.spinner("⚡ 正在自動辨識成分股並重算市場寬度指標..."):
    items = fetch_dashboard_data(selected_etfs)

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
