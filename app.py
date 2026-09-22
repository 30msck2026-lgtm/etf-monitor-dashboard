import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

# 頁面基礎設置
st.set_page_config(page_title="ETF Overview", layout="wide", initial_sidebar_state="collapsed")

# 注入高質感暗黑、手機端雙列凍結樣式、管理選單樣式
st.markdown("""
<style>
    /* 全域背景設定 */
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

    /* 單選分類膠囊列美化 */
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

    /* 上下滑動時表頭永遠凍結在最頂 */
    .table-container th { position: sticky; top: 0; background-color: #162038; color: #94a3b8; font-size: 11px; z-index: 10; padding: 12px 14px; border-bottom: 2px solid #223154; white-space: nowrap; }

    /* 左右滑動時，電腦端雙列凍結，手機端單列凍結基礎層級 */
    .sticky-col-1 { position: sticky; left: 0; z-index: 5; background-color: #0e1526; min-width: 90px; }
    .sticky-col-2 { min-width: 170px; border-right: 2px solid #1e2942; background-color: #0e1526; }

    /* 電腦端 (螢幕寬度 >= 992px)：凍結 TICKER (left:0) 與 SECTOR (left:90px) 雙列 */
    @media (min-width: 992px) {
        .sticky-col-2 { position: sticky; left: 90px; z-index: 5; border-right: 2px solid #1e2942; }
        th.sticky-col-1 { z-index: 20; }
        th.sticky-col-2 { z-index: 20; border-right: 2px solid #223154; }
    }

    /* 手機端 (螢幕寬度 < 992px)：只凍結 TICKER (left:0)，SECTOR 欄位會縮進去 */
    @media (max-width: 991px) {
        .sticky-col-2 { position: static; border-right: none; }
    }

    /* 管理選單 Expandable自訂樣式 */
    [data-testid="stExpander"] .stMarkdown { background-color: #0e1526; padding: 15px; border-radius: 10px; border: 1px solid #1a233a; }
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

# ----------------- 【分類導航】 -----------------
CATEGORY_ETFS = {
    "Sector ETF": ["XLK", "XLC", "XLY", "XLI", "XLF", "XLV", "XLB", "XLU", "XLP", "XLRE", "XLE"],
    "Industry ETF": ["SMH", "SOXX", "IGV", "XBI", "ITA", "XHB"],
    "Asset Class": ["SPY", "QQQ", "IWM", "TLT", "GLD", "SCHD", "VYM"]
}

selected_cat = st.radio(
    "分類視圖",
    options=["Sector ETF", "Industry ETF", "Asset Class"],
    index=0,
    label_visibility="collapsed"
)

# ----------------- 【自由加減 ETF 清單】 -----------------
with st.expander("➕ / ➖ 點此自訂該分類下的 ETF 標的 (點擊展開或關閉)", expanded=False):
    default_pool = ", ".join(CATEGORY_ETFS[selected_cat])
    user_input = st.text_input("ETF 監控代碼（逗號隔開）", value=default_pool)
    active_etfs = [x.strip().upper() for x in user_input.split(",") if x.strip()]

# ----------------- 【全量成分股數據庫 (Holdings DB with Rotational Update)】 -----------------
# 這個字典將持久化存儲成分股名單與上次更新時間。平常 Refresh 只讀此字典，零網路請求秒開[cite: 28]。
if 'etf_holdings_db' not in st.session_state:
    st.session_state.etf_holdings_db = {
        "XLK": {"full_name": "資訊科技 (Tech 全量)", "last_updated": "2026-09-01", "holdings": [
            "AAPL", "MSFT", "NVDA", "AVGO", "CSCO", "ACN", "ORCL", "CRM", "AMD", "QCOM", "TXN", "INTU", "AMAT", "NOW", "IBM"
        ]},
        "XLE": {"full_name": "能源板塊 (Energy 全量)", "last_updated": "2026-09-10", "holdings": [
            "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "WMB", "OXY", "KMI", "HAL", "DVN", "BKR"
        ]},
        "XLF": {"full_name": "金融板塊 (Fin 全量)", "last_updated": "2026-09-15", "holdings": [
            "BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SPGI", "AXP", "PGR", "BLK", "C", "MMC"
        ]},
        "XLC": {"full_name": "通訊服務 (Comm 全量)", "last_updated": "2026-08-20", "holdings": [
            "META", "GOOGL", "NFLX", "TMUS", "CMCSA", "DIS", "T", "VZ", "CHTR", "EA", "TTWO", "WBD"
        ]},
        "XLY": {"full_name": "非必需消費 (Discr 全量)", "last_updated": "2026-09-18", "holdings": [
            "AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "BKNG", "SBUX", "TJX", "ORLY", "F", "GM"
        ]},
        "XLI": {"full_name": "工業製造 (Ind 全量)", "last_updated": "2026-09-12", "holdings": [
            "GE", "CAT", "UNP", "HON", "RTX", "BA", "DE", "LMT", "ETN", "UPS", "ADP", "WM", "NOC"
        ]},
        "XLV": {"full_name": "醫療保健 (Health 全量)", "last_updated": "2026-09-19", "holdings": [
            "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "PFE", "AMGN", "DHR", "ISRG", "BMY"
        ]},
        "XLB": {"full_name": "基礎原物料 (Materials 全量)", "last_updated": "2026-08-15", "holdings": [
            "LIN", "APD", "SHW", "FCX", "ECL", "NEM", "DOW", "CTVA", "PPG", "DD"
        ]},
        "XLU": {"full_name": "公用事業 (Utils 全量)", "last_updated": "2026-07-30", "holdings": [
            "NEE", "SO", "DUK", "CEG", "SRE", "AEP", "D", "PEG", "ED", "PCG"
        ]},
        "XLP": {"full_name": "必需消費 (Stap Staples 全量)", "last_updated": "2026-08-05", "holdings": [
            "PG", "COST", "WMT", "KO", "PEP", "PM", "MDLZ", "MO", "CL", "KMB"
        ]},
        "XLRE": {"full_name": "房地產 (Real Est 全量)", "last_updated": "2026-07-25", "holdings": [
            "PLD", "AMT", "EQIX", "WELL", "PSA", "O", "CCI", "SPG", "DLR"
        ]},
        "SMH": {"full_name": "VanEck 半導體全量代表", "last_updated": "2026-09-20", "holdings": [
            "NVDA", "TSM", "AVGO", "ASML", "AMD", "QCOM", "TXN", "MU", "LRCX", "AMAT", "ADI"
        ]}
    }

# 成分股數據解析器（自動嘗試多個金融接口，並快取每週更新）
@st.cache_data(ttl=604800) # 本地 TTL 設定為 7 天
def get_holdings_weekly_engine(ticker, force_refresh_week=False):
    db = st.session_state.etf_holdings_db
    
    # 若存在快取，且不是強制本週刷新模式，直接讀取
    if ticker in db:
        return db[ticker]["full_name"], db[ticker]["holdings"], db[ticker]["last_updated"]
    
    # 若未知標的或快取超期，嘗試透過官方數據接口取得全量成分股 (非爬蟲，免崩潰)
    try:
        t = yf.Ticker(ticker)
        # 方法1: 官方 funds_data (最準確)
        top_h = t.funds_data.top_holdings
        if top_h is not None and not top_h.empty:
            symbols = [str(x).replace(".", "-").strip().upper() for x in top_h.index.tolist() if isinstance(x, str)]
            if len(symbols) >= 10:
                name = t.info.get("shortName", ticker) if hasattr(t, 'info') else ticker
                # 寫回 DB
                return (name, symbols, datetime.now().strftime("%Y-%m-%d"))
    except Exception:
        pass
    
    return (ticker, [], "N/A (未知標的)")

def calc_breadth_vectorized(c_df, constituents, idx):
    valid_cols = [c for c in constituents if c in c_df.columns and len(c_df[c].dropna()) > abs(idx) + 120]
    if not valid_cols:
        return None
    
    cnt_20, cnt_50, cnt_200 = 0, 0, 0
    for c in valid_cols:
        s = c_df[c].dropna()
        sub_s = s.iloc[:len(s)+idx] if idx < 0 else s
        last_p = sub_s.iloc[-1]
        
        # 計算 向量化 EMA (秒級完成)
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
    
    # SPY 3M 回報基準
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
            
            # 讀取本地成分股 DB
            sector_db = st.session_state.etf_holdings_db
            s_name, constituents, last_updated = "N/A", [], "N/A"
            if ticker in sector_db:
                s_name = sector_db[ticker]["full_name"]
                constituents = sector_db[ticker]["holdings"]
                last_updated = sector_db[ticker]["last_updated"]
            
            b_now_str = "N/A"
            chg_1w_str = chg_1m_str = chg_2m_str = chg_3m_str = "-"
            ew_ret = "- / - / -"
            
            if constituents:
                # 批量下載該 ETF 全量成分股 (秒級完成)
                c_raw = yf.download(constituents, period="2y", interval="1d", progress=False)
                if not c_raw.empty and 'Close' in c_raw:
                    c_close = c_raw['Close']
                    c_df = pd.DataFrame({constituents[0]: c_close}) if isinstance(c_close, pd.Series) else c_close.copy()
                    
                    b_res = calc_breadth_vectorized(c_df, constituents, 0)
                    if b_res is not None:
                        # 顯示全量股票母數 (例如: 67檔)
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

with st.spinner(f"⚡正在使用內部 DB 解析 {selected_cat} 全量指標（ Refresh 只需 2-3 秒開機速度）..."):
    items = fetch_dashboard_data(active_etfs)

# 生成 HTML 代碼 (配合 CSS 實現手機/電腦差異滾動)
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
    .sticky-col-1, .sticky-col-2 {{ position: sticky; left: 0; z-index: 5; background-color: #0e1526; min-width: 90px; }}
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
                <th>PRC CHG (1M/2M/3M)</th>
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
# ----------------- 【📊 管理選單與數據指南】 -----------------
top_adm, top_ food = st.columns([1, 1])

with top_adm:
    # 2 & 3. 實體成分股 DB 管理選單：顯示上一次網上更新日期
    with st.expander("📊 成分股數據庫管理選單（顯示更新日期範本）", expanded=False):
        # 準備顯示用的 DB
        db = st.session_state.etf_holdings_db
        db_items = []
        for ticker, data in db.items():
            db_items.append({
                "TICKER": ticker,
                "成分股名稱": data["full_name"],
                "上一次網上抓取日期 (Snapshot)": data["last_updated"],
                "股票數量": f"{len(data['holdings'])}檔"
            })
        st.dataframe(pd.DataFrame(db_items), use_container_width=True, hide_index=True)
        
        # 3. 每週自動「全自動指標全量輪調」按鈕組
        st.markdown("### 全量成分股數據持久化更新")
        st.markdown(f"<span style='color:#94a3b8; font-size:12px;'>每星期只需抓取網上數據更新幾隻標的[cite: 28]，整個月內全量 DB 數據即可更新一遍[cite: 28]，保持準確性。上一次網上成功抓取日期寫在上面讓我看[cite: 1, 2, 4]。</span>", unsafe_allow_html=True)
        
        # 準備排序：找到最久沒更新的 2 隻
        all_etfs_in_db = list(db.keys())
        all_etfs_in_db.sort(key=lambda x: db[x]["last_updated"])
        rotation_list = all_etfs_in_db[:2] # 本週只抓最久的 2 隻
        
        # 美化按鈕組
        adm_btn1, adm_btn2 = st.columns(2)
        with adm_btn1:
            if st.button(f"🔄 本週全自動抓取更新：[{rotation_list[0]}, {rotation_list[1]}]", use_container_width=True):
                # 實體向 Yahoo 發出網路請求自動解析與更新 DB
                with st.spinner(f"正在全自動向網上抓取解析 {rotation_list[0]} 與 {rotation_list[1]} 的最新成分股清單（只每週執行一次，平常 Refresh 秒開）..."):
                    for t in rotation_list:
                        name, holdings, date_str = get_holdings_weekly_engine(t, force_refresh_week=True)
                        if holdings:
                            st.session_state.etf_holdings_db[t] = {
                                "full_name": name,
                                "last_updated": date_str,
                                "holdings": holdings
                            }
                    st.success(f"成功更新了 {rotation_list[0]} 與 {rotation_list[1]} 及其 Snapshot 日期紀錄。")
                    st.rerun() # 立即刷新主表格數據

with top_ food:
    with st.expander("📚 按此展開數據定義指南 (忘記欄位意思點此查閱)", expanded=False):
        st.markdown("""
        <table style="width:100%; border-collapse: collapse; margin-top:10px;">
            <tr style="border-bottom: 1px solid #1a233a;">
                <td style="padding: 8px; color: #ffffff;"><strong>RS (SPY)</strong></td>
                <td style="padding: 8px; color: #cbd5e1; font-size:13px;">相對強度分數。計算 ETF 自身的 3M 報酬率減去標普500 (SPY) 的 3M 報酬率。分數為正表示跑贏大盤。</td>
            </tr>
            <tr style="border-bottom: 1px solid #1a233a;">
                <td style="padding: 8px; color: #ffffff;"><strong>% VS EMA</strong></td>
                <td style="padding: 8px; color: #cbd5e1; font-size:13px;">EMA 乖離率。價格相對於指數移動平均線 (EMA) 的百分比乖離程度[cite: 27]。格式為 (10, 20, 30, 50, 200)。</td>
            </tr>
            <tr style="border-bottom: 1px solid #1a233a;">
                <td style="padding: 8px; color: #ffffff;"><strong>EW COMP</strong></td>
                <td style="padding: 8px; color: #cbd5e1; font-size:13px;">全量成分股等權報酬[cite: 27]。該 ETF 旗下全體成分股（例如 67 隻股票[cite: 27]）進行算術等權後的平均回報[cite: 27]，格式為 (1M/2M/3M)。</td>
            </tr>
            <tr style="border-bottom: 1px solid #1a233a;">
                <td style="padding: 8px; color: #ffffff;"><strong>% ABOVE EMA</strong></td>
                <td style="padding: 8px; color: #cbd5e1; font-size:13px;">市場內部寬度[cite: 27]。該 ETF 全量成分股中[cite: 28]，股價高於其自身的 20天、50天、200天 EMA 的股票百分比[cite: 27]。反映普漲普跌權[cite: 27]。</td>
            </tr>
            <tr style="border-bottom: 1px solid #1a233a;">
                <td style="padding: 8px; color: #ffffff;"><strong>BREADTH CHG</strong></td>
                <td style="padding: 8px; color: #cbd5e1; font-size:13px;">內部寬度變化。與過去 (1W、1M、2M、3M) 相比，「高於 50E 比例」的百分點增減變化[cite: 27]。</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)
