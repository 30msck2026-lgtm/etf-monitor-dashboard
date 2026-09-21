import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 頁面標題與佈局
st.set_page_config(page_title="財報日更新表", layout="wide", initial_sidebar_state="collapsed")

# 注入科技深色樣式
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    div[data-testid="stMetric"] {
        background-color: #161f30;
        border: 1px solid #2d3748;
        padding: 12px;
        border-radius: 10px;
    }
    .metric-card {
        background-color: #161f30;
        border: 1px solid #232d42;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .badge-up { color: #10b981; font-weight: bold; }
    .badge-down { color: #f43f5e; font-weight: bold; }
    .badge-neutral { color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# 頂部導航
col_t1, col_t2 = st.columns([4, 1])
with col_t1:
    st.markdown("## 財報日更新表")
    st.caption("US Sector/Industry ETF Trend, Relative Strength & Internal Breadth Monitor")
with col_t2:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 側邊欄：自由增減 ETF
st.sidebar.subheader("監控標的管理")
default_etfs = "XLK, XLC, XLY, XLI, XLF, XLV, XLB, XLU, XLP, XLRE, XLE, SMH"
user_input = st.sidebar.text_area("ETF 代號清單 (以逗號隔開)", default_etfs)
selected_etfs = [x.strip().upper() for x in user_input.split(",") if x.strip()]

# 預設各板塊權重成分股（用於計算內部寬度）
BREADTH_PROXIES = {
    "XLK": ["AAPL", "MSFT", "NVDA", "AVGO", "CSCO", "ACN", "ORCL", "ADBE", "CRM", "AMD"],
    "XLC": ["META", "GOOGL", "NFLX", "TMUS", "CMCSA", "DIS", "EA", "TTWO"],
    "XLY": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "BKNG"],
    "XLI": ["GE", "CAT", "UNP", "HON", "RTX", "BA", "DE", "LMT"],
    "XLF": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS"],
    "XLV": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "PFE"],
    "XLB": ["LIN", "APD", "SHW", "FCX", "ECL", "NEM", "DOW"],
    "XLU": ["NEE", "SO", "DUK", "CEG", "SRE", "AEP", "D"],
    "XLP": ["PG", "COST", "WMT", "KO", "PEP", "PM", "MDLZ"],
    "XLRE": ["PLD", "AMT", "EQIX", "WELL", "PSA", "O", "CCI"],
    "XLE": ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX"],
    "SMH": ["NVDA", "TSM", "AVGO", "ASML", "AMD", "QCOM", "TXN", "MU"]
}

def calc_breadth_at_index(c_df, constituents, idx):
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
def fetch_all_metrics(tickers):
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
        
        rs_status = "領先 ▲" if (p_3m / 100) > spy_ret_3m else "落後 ▼"
        trend = "多頭 ▲" if (cur_p > e50 and e20 > e50) else ("空頭 ▼" if (cur_p < e50 and e20 < e50) else "整理 ◼")
        
        # 內部寬度與多週期變化
        constituents = BREADTH_PROXIES.get(ticker, [])
        b_now = (0, 0, 0)
        chg_1w = chg_1m = chg_2m = chg_3m = "+0.0%"
        ew_ret = "0.0% / 0.0% / 0.0%"
        
        if constituents:
            c_df = yf.download(constituents, period="2y", interval="1d", progress=False)['Close']
            b_now = calc_breadth_at_index(c_df, constituents, 0)
            b_1w = calc_breadth_at_index(c_df, constituents, -5)
            b_1m = calc_breadth_at_index(c_df, constituents, -21)
            b_2m = calc_breadth_at_index(c_df, constituents, -42)
            b_3m = calc_breadth_at_index(c_df, constituents, -63)
            
            # 以 50 EMA 寬度變化為代表
            chg_1w = f"{(b_now[1] - b_1w[1]):+.1f}%"
            chg_1m = f"{(b_now[1] - b_1m[1]):+.1f}%"
            chg_2m = f"{(b_now[1] - b_2m[1]):+.1f}%"
            chg_3m = f"{(b_now[1] - b_3m[1]):+.1f}%"

            # 等權報酬
            ew1 = np.mean([(c_df[c].iloc[-1]/c_df[c].iloc[-21]-1)*100 for c in constituents if c in c_df])
            ew2 = np.mean([(c_df[c].iloc[-1]/c_df[c].iloc[-42]-1)*100 for c in constituents if c in c_df])
            ew3 = np.mean([(c_df[c].iloc[-1]/c_df[c].iloc[-63]-1)*100 for c in constituents if c in c_df])
            ew_ret = f"{ew1:+.1f}% / {ew2:+.1f}% / {ew3:+.1f}%"

        results.append({
            "Ticker": ticker,
            "Price": round(cur_p, 2),
            "Trend": trend,
            "RS (vs SPY)": rs_status,
            "% vs 10/20/30E": f"{(cur_p/e10-1)*100:+.1f}% / {(cur_p/e20-1)*100:+.1f}% / {(cur_p/e30-1)*100:+.1f}%",
            "% vs 50/200E": f"{(cur_p/e50-1)*100:+.1f}% / {(cur_p/e200-1)*100:+.1f}%",
            "% vs 30W MA": f"{(cur_p/ma150-1)*100:+.1f}%",
            "價格 (1M/2M/3M)": f"{p_1m:+.1f}% / {p_2m:+.1f}% / {p_3m:+.1f}%",
            "等權 (1M/2M/3M)": ew_ret,
            "% > 20/50/200 EMA": f"{b_now[0]:.0f}% / {b_now[1]:.0f}% / {b_now[2]:.0f}%",
            "寬度變動 (1W/1M/2M/3M)": f"{chg_1w} | {chg_1m} | {chg_2m} | {chg_3m}",
            "raw_b200": b_now[2]
        })
    return pd.DataFrame(results)

with st.spinner("正在加載與計算內部寬度數據..."):
    df_data = fetch_all_metrics(selected_etfs)

if not df_data.empty:
    tab1, tab2 = st.tabs(["💻 電腦完整表格", "📱 手機重點卡片"])

    with tab1:
        st.dataframe(df_data.drop(columns=["raw_b200"]), use_container_width=True, hide_index=True)

    with tab2:
        for _, row in df_data.iterrows():
            badge_color = "badge-up" if "多頭" in row["Trend"] else ("badge-down" if "空頭" in row["Trend"] else "badge-neutral")
            st.markdown(f"""
            <div class="metric-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0;">{row['Ticker']} <span style="font-size:14px; color:#94a3b8;">${row['Price']}</span></h3>
                    <span class="{badge_color}">{row['Trend']} ({row['RS (vs SPY)']})</span>
                </div>
                <div style="margin-top:8px; font-size:12px; line-height:1.7;">
                    <b>vs 10/20/30 EMA:</b> {row['% vs 10/20/30E']}<br>
                    <b>vs 50/200 EMA:</b> {row['% vs 50/200E']} | <b>30W MA:</b> {row['% vs 30W MA']}<br>
                    <b>價格回報 (1M/2M/3M):</b> {row['價格 (1M/2M/3M)']}<br>
                    <b>等權回報 (1M/2M/3M):</b> {row['等權 (1M/2M/3M)']}<br>
                    <b>成分股寬度 (> 20/50/200 EMA):</b> <span style="color:#38bdf8;">{row['% > 20/50/200 EMA']}</span><br>
                    <b>寬度變動 (1W/1M/2M/3M):</b> {row['寬度變動 (1W/1M/2M/3M)']}
                </div>
            </div>
            """, unsafe_allow_html=True)
