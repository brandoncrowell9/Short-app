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


# ============================================
# FINA3343 ANALYSIS APP 1
# WALL STREET RESEARCH WORKSPACE
# ============================================

st.markdown("### MARKET INTELLIGENCE")

c1, c2, c3 = st.columns(3)

c1.metric("COMPANIES IN UNIVERSE", f"{len(df):,}")
c2.metric("EARNINGS QUALITY ALERTS", f"{len(sell):,}")
c3.metric("VALUE + QUALITY CANDIDATES", f"{len(buy):,}")

st.caption(
    "Live screening results based on your selected sectors, "
    "market capitalization, and financial thresholds."
)

st.divider()

# Identify company status using existing screen results
sell_ids = set(sell["ticker"])
buy_ids = set(buy["ticker"])

def screen_label(ticker):
    if ticker in sell_ids and ticker in buy_ids:
        return "Both screens"
    if ticker in sell_ids:
        return "SELL"
    if ticker in buy_ids:
        return "BUY"
    return "Other"

# Main research navigation
overview_tab, buy_tab, sell_tab, company_tab = st.tabs([
    "📊 Market Overview",
    "📈 BUY Research",
    "📉 SELL Research",
    "🏢 Company Drill-Down"
])

# ============================================
# TAB 1: MARKET OVERVIEW
# ============================================

with overview_tab:

    st.subheader("Equity Screening Overview")

    st.write(
        "This dashboard evaluates financial statement quality, "
        "profitability, and valuation across the selected "
        "company universe."
    )

    

    col1, col2 = st.columns(2)

    # LEFT CHART: SECTOR COVERAGE
    with col1:
        st.markdown("#### Sector Coverage")

        sector_counts = (
            df["sector"]
            .value_counts()
            .reset_index()
        )
        sector_counts.columns = ["Sector", "Companies"]

        sector_fig = px.bar(
            sector_counts,
            x="Companies",
            y="Sector",
            orientation="h",
            title="Companies by Sector",
            color_discrete_sequence=["#49D9C4"]
        )

        sector_fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0B1525",
            plot_bgcolor="#0B1525",
            yaxis={"categoryorder": "total ascending"}
        )

        st.plotly_chart(
            sector_fig,
            use_container_width=True
        )

    # RIGHT CHART: SCREENING SCATTERPLOT
    with col2:
        st.markdown("#### Screening Results")

        scatter_df = df.dropna(
            subset=["GPA", "BM"]
        ).copy()

        scatter_df = scatter_df[
            scatter_df["BM"] > 0
        ]

        scatter_df["Screen"] = (
            scatter_df["ticker"].apply(screen_label)
        )

        scatter_fig = px.scatter(
            scatter_df,
            x="BM",
            y="GPA",
            color="Screen",
            hover_name="ticker",
            hover_data=["name", "sector"],
            log_x=True,
            color_discrete_map={
                "BUY": "#49D9C4",
                "SELL": "#FF7A7A",
                "Both screens": "#F4C95D",
                "Other": "#72849B"
            },
            title="Profitability vs. Valuation",
            labels={
                "BM": "Book-to-Market Ratio",
                "GPA": "Gross Profitability"
            }
        )

        scatter_fig.update_traces(
            marker=dict(size=8, opacity=0.7)
        )

        scatter_fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0B1525",
            plot_bgcolor="#0B1525",
            legend_title_text="Screening Signal"
        )

        st.plotly_chart(
            scatter_fig,
            use_container_width=True
        )





st.info(
        "BUY and SELL screens use different financial "
        "statement information and ratios. These are financial health "
        "signals, but do not mean the stock is an automatic buy or sell."
    )


# ============================================
# TAB 2: BUY RESEARCH
# ============================================

with buy_tab:

    st.subheader("BUY Research | Profitability & Value")

    st.write(
        "This strategy identifies companies with strong "
        "gross profitability and relatively high "
        "book-to-market ratios."
    )
    st.markdown("#### Financial Interpretation")

    st.write(
        "Higher GPA indicates stronger gross profit "
        "generation compared to its assets. Higher B/M "
        "can indicate a lower market valuation relative "
        "to accounting equity, but can also show underlying "
        "financial distress or weaker growth expectations."
    )

    st.markdown("#### Current BUY Screening Criteria")

    st.write(
        f"Minimum GPA percentile: **{gpa_pct}%**"
    )

    st.write(
        f"Minimum B/M percentile: **{bm_pct}%**"
    )

    st.metric("Potential BUY Candidates", len(buy))

    st.markdown("#### Ranked BUY Candidates")

    if buy.empty:
        st.warning(
            "No companies meet the current BUY criteria. "
            "Try adjusting the sidebar filters."
        )
    else:
        st.dataframe(
            buy[
                [
                    "ticker", "name", "sector",
                    "GPA", "BM", "BUY_score"
                ]
            ],
            hide_index=True,
            use_container_width=True
        )

        st.markdown("#### Top BUY Candidates")

        top_buy = buy.head(10).copy()

        buy_fig = px.bar(
            top_buy,
            x="ticker",
            y="BUY_score",
            color_discrete_sequence=["#49D9C4"],
            title="Top 10 Combined BUY Scores",
            hover_data=["name", "GPA", "BM"]
        )

        buy_fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0B1525",
            plot_bgcolor="#0B1525",
            yaxis_title="Combined Percentile Score"
        )

        st.plotly_chart(
            buy_fig,
            use_container_width=True
        )


# ============================================
# TAB 3: SELL RESEARCH
# ============================================

with sell_tab:

    st.subheader("SELL Research | Earnings Quality")

    st.write(
        "This strategy identifies companies exhibiting "
        "potential accounting-quality warning signals."
    )

    st.markdown("#### Financial Interpretation")

    st.write(
        "High scaled total accruals may indicate "
        "that accounting earnings are less strongly "
        "supported by operating cash flow. Elevated "
        "scaled net operating assets can provide an "
        "additional earnings-quality warning signal."
    )

    st.markdown("#### Current SELL Screening Criteria")

    st.write(
        f"STA threshold: **{sta_pct}th percentile**"
    )

    st.write(
        f"NOA threshold: **{noa_pct}th percentile**"
    )

    st.write(
        f"Minimum red flags: **{flags_needed}**"
    )

    st.metric("Potential SELL Candidates", len(sell))

    st.markdown("#### Ranked SELL Candidates")

    if sell.empty:
        st.warning(
            "No companies meet the current SELL criteria. "
            "Try adjusting the sidebar filters."
        )
    else:
        st.dataframe(
            sell[
                [
                    "ticker", "name", "sector",
                    "STA", "Scaled_NOA", "red_flags"
                ]
            ],
            hide_index=True,
            use_container_width=True
        )

        st.markdown("#### Earnings Quality Comparison")

        sell_plot = sell.head(15).copy()

        sell_fig = px.scatter(
            sell_plot,
            x="STA",
            y="Scaled_NOA",
            size="red_flags",
            hover_name="ticker",
            hover_data=["name", "sector"],
            color_discrete_sequence=["#FF7A7A"],
            title="STA vs Scaled NOA"
        )

        sell_fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0B1525",
            plot_bgcolor="#0B1525"
        )

        st.plotly_chart(
            sell_fig,
            use_container_width=True
        )

# ============================================
# TAB 4: COMPANY ANALYSIS
# ============================================

with company_tab:

    st.subheader("Company Research Profile")

    options = sorted(df["ticker"].tolist())

    choice = st.selectbox(
        "Select a company to analyze",
        options
    )

    record = df[df["ticker"] == choice].iloc[0]

    st.markdown(f"### {record['name']} ({choice})")
    st.caption(f"Sector: {record['sector']}")

    st.markdown("#### Financial Ratios")

    ratio_cols = st.columns(4)

    for column, measure in zip(
        ratio_cols,
        ["STA", "Scaled_NOA", "GPA", "BM"]
    ):
        value = record[measure]

        column.metric(
            measure,
            f"{value:.4f}" if pd.notna(value) else "N/A"
        )

    st.markdown("#### Company Financial Data")

    show_cols = [
        c for c in [
            "fiscal_date",
            "market_cap",
            "total_assets",
            "net_income",
            "operating_cash_flow",
            "gross_profit",
            "stockholders_equity",
            "STA",
            "Scaled_NOA",
            "GPA",
            "BM",
            "red_flags"
        ]
        if c in df.columns
    ]

    st.dataframe(
        pd.DataFrame({
            "Measure": show_cols,
            "Value": [record[c] for c in show_cols]
        }),
        hide_index=True,
        use_container_width=True
    )

    status = screen_label(choice)

    st.markdown("#### Current Screening Classification")
    st.write(f"**{status}**")

    if status == "BUY":
        st.success(
            "This company meets the current profitability "
            "and valuation screening thresholds."
        )
    elif status == "SELL":
        st.error(
            "This company meets the current "
            "earnings-quality warning thresholds."
        )
    elif status == "Both screens":
        st.warning(
            "This company meets both BUY and SELL "
            "criteria. Its conflicting signals require "
            "additional investigation."
        )
    else:
        st.info(
            "This company does not currently qualify "
            "for either screen."
        )

    st.markdown("#### Research Methodology")

    with st.expander("Financial ratios and limitations"):

        st.markdown("""
**BUY methodology**

- Gross Profitability (GPA): Gross Profit / Total Assets.
- Book-to-Market (B/M): Book Equity / Market Capitalization.
- BUY scores equally weight GPA and B/M percentile ranks.

**SELL methodology**

- Scaled Total Accruals (STA): (Net Income - Operating Cash Flow) / Total Assets.
- Scaled NOA: Net Operating Assets / Total Assets.
- High STA and NOA can signal potential earnings-quality concerns.

**Important limitations**

- The NOA formula still needs to be verified against course materials.
- Book equity and market capitalization may come from different dates.
- Foreign-listed companies may require currency reconciliation.
- Percentiles are recalculated after filtering the universe.
- Missing values are not replaced with zero.
- Screening signals are not final investment recommendations.
        """)

st.divider()

st.caption(
    "FINA3343 Analysis App 1 | "
    "Educational Financial Statement Research Dashboard"
)
