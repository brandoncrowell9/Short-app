import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="FINA3343 Analysis App 1",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Wall Street Research Dashboard theme
st.markdown("""
<style>
    .stApp {
        background-color: #0B1525;
        color: #EAF1F8;
    }

    [data-testid="stSidebar"] {
        background-color: #142238;
        border-right: 1px solid #2B4059;
    }

    h1, h2, h3 {
        color: #F2F6FC !important;
        font-family: Arial, sans-serif;
    }

    h1 {
        font-size: 2.4rem !important;
        font-weight: 800 !important;
        letter-spacing: -1px;
    }

    [data-testid="stMetric"] {
        background-color: #172940;
        border: 1px solid #2B4059;
        border-radius: 14px;
        padding: 20px;
    }

    [data-testid="stMetricValue"] {
        color: #49D9C4;
        font-weight: 750;
    }

    [data-testid="stMetricLabel"] {
        color: #A9BCD1;
    }

    div.stButton > button {
        background-color: #147D80;
        color: white;
        border-radius: 8px;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #2B4059;
        border-radius: 10px;
    }

    hr {
        border-color: #2B4059;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(
    "<span style='color:#49D9C4;"
    "font-weight:700;letter-spacing:2px;'>"
    "FINANCIAL STATEMENT RESEARCH / FINA 3343"
    "</span>",
    unsafe_allow_html=True
)

st.title("FINA3343 Analysis App 1")

st.caption(
    "Equity Research Dashboard | "
    "Profitability • Valuation • Earnings Quality"
)

st.divider()

@st.cache_data
def load_data():
    data = pd.read_csv("universe.csv")
    required = ["ticker", "name", "sector", "market_cap", "STA", "Scaled_NOA", "GPA", "BM"]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise ValueError("Missing CSV columns: " + ", ".join(missing))
    for c in ["market_cap", "STA", "Scaled_NOA", "GPA", "BM"]:
        data[c] = pd.to_numeric(data[c], errors="coerce")
    data = data[(data["ticker"] != "NVDA") & (data["sector"] != "Financial Services")]
    data = data.dropna(subset=["ticker", "sector"]).drop_duplicates("ticker").copy()
    data.loc[data["BM"] <= 0, "BM"] = np.nan
    return data

try:
    original = load_data()
except Exception as e:
    st.error(f"Could not load universe.csv: {e}")
    st.stop()

st.sidebar.header("Screening filters")
sectors = sorted(original["sector"].unique().tolist())
selected = st.sidebar.multiselect("Sectors", sectors, default=sectors)
cap = st.sidebar.slider("Minimum market cap ($ billions)", 0.0, 100.0, 0.0, 1.0)
sta_pct = st.sidebar.slider("SELL: STA percentile", 50, 95, 80, 5)
noa_pct = st.sidebar.slider("SELL: NOA percentile", 50, 95, 80, 5)
flags_needed = st.sidebar.slider("SELL: minimum red flags", 1, 2, 2)
gpa_pct = st.sidebar.slider("BUY: GPA percentile rank", 50, 95, 70, 5)
bm_pct = st.sidebar.slider("BUY: B/M percentile rank", 50, 95, 70, 5)

df = original[original["sector"].isin(selected) & (original["market_cap"] >= cap * 1e9)].copy()
if df.empty:
    st.warning("No companies match these sector and market-cap filters.")
    st.stop()

# Percentiles are recalculated within the selected universe.
sta_cut = df["STA"].quantile(sta_pct / 100)
noa_cut = df["Scaled_NOA"].quantile(noa_pct / 100)
df["STA_flag"] = df["STA"].notna() & (df["STA"] >= sta_cut)
df["NOA_flag"] = df["Scaled_NOA"].notna() & (df["Scaled_NOA"] >= noa_cut)
df["red_flags"] = df["STA_flag"].astype(int) + df["NOA_flag"].astype(int)
sell = df.dropna(subset=["STA", "Scaled_NOA"])
sell = sell[sell["red_flags"] >= flags_needed].sort_values(["red_flags", "STA"], ascending=False)

# BUY uses a different set of measures from SELL.
buy = df.dropna(subset=["GPA", "BM"]).copy()
buy = buy[buy["BM"] > 0].copy()
buy["GPA_rank"] = buy["GPA"].rank(pct=True)
buy["BM_rank"] = buy["BM"].rank(pct=True)
buy["BUY_score"] = (buy["GPA_rank"] + buy["BM_rank"]) / 2
buy = buy[(buy["GPA_rank"] >= gpa_pct / 100) & (buy["BM_rank"] >= bm_pct / 100)]
buy = buy.sort_values("BUY_score", ascending=False)

c1, c2, c3 = st.columns(3)
c1.metric("Companies screened", len(df))
c2.metric("Potential SELL", len(sell))
c3.metric("Potential BUY", len(buy))

left, right = st.columns(2)
with left:
    st.subheader("Potential SELL candidates")
    st.dataframe(sell[["ticker", "name", "sector", "STA", "Scaled_NOA", "red_flags"]], hide_index=True, use_container_width=True)
with right:
    st.subheader("Potential BUY candidates")
    st.dataframe(buy[["ticker", "name", "sector", "GPA", "BM", "BUY_score"]], hide_index=True, use_container_width=True)

st.subheader("Profitability versus valuation")
plot_df = df.dropna(subset=["GPA", "BM"]).copy()
plot_df = plot_df[plot_df["BM"] > 0]
sell_ids, buy_ids = set(sell["ticker"]), set(buy["ticker"])
def label(t):
    if t in sell_ids and t in buy_ids:
        return "Both screens"
    if t in sell_ids:
        return "SELL"
    if t in buy_ids:
        return "BUY"
    return "Other"
plot_df["Screen"] = plot_df["ticker"].map(label)
if not plot_df.empty:
    fig = px.scatter(plot_df, x="BM", y="GPA", color="Screen", hover_name="ticker", hover_data=["name", "sector"], title="Selected universe: GPA vs B/M")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No companies have usable GPA and B/M for the chart.")

st.subheader("Company drill-down")
options = sorted(df["ticker"].tolist())
choice = st.selectbox("Choose a ticker", options)
record = df[df["ticker"] == choice].iloc[0]
st.write(f"**{record['name']}** — {record['sector']}")
show_cols = [c for c in ["fiscal_date", "market_cap", "total_assets", "net_income", "operating_cash_flow", "gross_profit", "stockholders_equity", "STA", "Scaled_NOA", "GPA", "BM", "red_flags"] if c in df.columns]
st.dataframe(pd.DataFrame({"Measure": show_cols, "Value": [record[c] for c in show_cols]}), hide_index=True)
st.write("**Current screen status:**", label(choice))

st.subheader("Investment conclusions — to complete")
st.info("After validating your course formulas and financial data, write an evidence-based SELL case and a separate BUY case for the leading candidates. Discuss counterarguments, financial trends, and valuation risks; do not treat screening flags as final advice.")
with st.expander("Methodology and limitations"):
    st.markdown("""- **SELL:** STA and scaled NOA are high-tail earnings-quality signals. Each can count as one red flag; companies need both measures available.
- **BUY:** GPA and positive B/M are independently percentile-ranked among companies with both measures. The BUY score equally weights the two ranks.
- Percentiles are recalculated after sector and size filtering, so changing the universe can change the rankings.
- Missing values remain missing. No missing financial data is replaced with zero.
- **Provisional:** Verify scaled NOA against the course's Chapter 3 formula. B/M uses latest annual book equity and a market capitalization captured at a different date; it is not a point-in-time backtest. Financial statement dates and accounting comparability need further review.
- Candidates can appear on both lists when quality/value and earnings-quality signals conflict. This requires judgment, not automatic resolution.
""")
