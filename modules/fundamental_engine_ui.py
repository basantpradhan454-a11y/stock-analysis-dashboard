"""Fundamental Engine UI — Health Score Dashboard for Streamlit."""
import streamlit as st
import json
from modules.fundamental_engine import run_fundamental_engine


def _fmt(val, prefix="", suffix="", percent=False):
    if val is None or val == "N/A":
        return "N/A"
    if percent:
        return f"{val*100:.1f}%"
    if isinstance(val, (int, float)):
        if abs(val) >= 1e12:
            return f"{prefix}{val/1e12:.2f}T{suffix}"
        elif abs(val) >= 1e9:
            return f"{prefix}{val/1e9:.2f}B{suffix}"
        elif abs(val) >= 1e7:
            return f"{prefix}{val/1e7:.2f}Cr{suffix}"
        return f"{prefix}{val:.2f}{suffix}"
    return f"{prefix}{val}{suffix}"


def render_fundamental_engine_ui():
    st.markdown(
        """<div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,5,20,0.95));
        border:1px solid rgba(74,158,255,0.25);border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1rem;">
        <div style="font-size:1.1rem;font-weight:800;font-family:Orbitron,monospace;
        background:linear-gradient(90deg,#00c853,#ffb020);-webkit-background-clip:text;
        -webkit-text-fill-color:transparent;">📊 Fundamental Engine</div>
        <div style="color:#8b949e;font-size:11px;margin-top:2px;">
        Yahoo Finance Fundamentals · Health Score (0-100) · Profitability · Valuation · Financial Health · Growth</div>
        </div>""",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        ticker = st.text_input(
            "Stock Ticker", value="RELIANCE.NS",
            placeholder="RELIANCE.NS, TCS.NS, AAPL, MSFT...",
            key="fund_engine_ticker"
        )
    with col2:
        st.markdown("&nbsp;")
        analyze_btn = st.button("🔍 Analyze Fundamentals", type="primary", key="fund_engine_btn")

    if analyze_btn:
        with st.spinner(f"Fetching fundamentals for {ticker}..."):
            result = run_fundamental_engine(ticker)

        if not result.get("ok"):
            st.error(f"Error: {result.get('error', 'Unknown error')}")
            return

        data = result["data"]
        score = result["score"]
        hs = score["health_score"]
        verdict = score["verdict"]
        breakdown = score["breakdown"]

        # --- Health Score Header ---
        score_color = "#00c853" if hs >= 75 else "#ffb020" if hs >= 50 else "#ff3b3b"
        st.markdown(
            f"""<div style="background:#10151d;border:1px solid {score_color};
            border-radius:12px;padding:1.5rem;text-align:center;margin-bottom:1rem;">
            <div style="font-size:3rem;font-weight:800;color:{score_color};">{hs}</div>
            <div style="font-size:1.1rem;color:#e8ecf1;margin-top:0.3rem;">{verdict}</div>
            <div style="font-size:12px;color:#7c8798;margin-top:0.3rem;">Health Score (0-100)</div>
            </div>""",
            unsafe_allow_html=True,
        )

        # --- Breakdown Cards ---
        st.markdown("### Score Breakdown")
        bc1, bc2, bc3, bc4 = st.columns(4)
        for col, (key, val) in zip([bc1, bc2, bc3, bc4], breakdown.items()):
            c = "#00c853" if val >= 7 else "#ffb020" if val >= 5 else "#ff3b3b"
            col.markdown(
                f"""<div style="background:#10151d;border:1px solid #232a36;
                border-radius:8px;padding:1rem;text-align:center;">
                <div style="font-size:1.5rem;font-weight:700;color:{c};">{val}</div>
                <div style="font-size:11px;color:#7c8798;margin-top:4px;">{key}</div>
                </div>""",
                unsafe_allow_html=True,
            )

        # --- Key Metrics Table ---
        st.markdown("### Key Fundamentals")
        metrics = [
            ("Company Name", data.get("name")),
            ("Sector", data.get("sector")),
            ("Current Price", _fmt(data.get("current_price"), prefix="₹")),
            ("Market Cap", _fmt(data.get("market_cap"), prefix="₹")),
            ("P/E Ratio", _fmt(data.get("pe_ratio"))),
            ("Forward P/E", _fmt(data.get("forward_pe"))),
            ("P/B Ratio", _fmt(data.get("pb_ratio"))),
            ("ROE", _fmt(data.get("roe"), percent=True)),
            ("Profit Margin", _fmt(data.get("profit_margin"), percent=True)),
            ("Debt/Equity", _fmt(data.get("debt_to_equity"))),
            ("Current Ratio", _fmt(data.get("current_ratio"))),
            ("Revenue Growth", _fmt(data.get("revenue_growth"), percent=True)),
            ("Earnings Growth", _fmt(data.get("earnings_growth"), percent=True)),
            ("Dividend Yield", _fmt(data.get("dividend_yield"), percent=True)),
            ("Beta", _fmt(data.get("beta"))),
            ("52-Week High", _fmt(data.get("52w_high"), prefix="₹")),
            ("52-Week Low", _fmt(data.get("52w_low"), prefix="₹")),
        ]

        mc1, mc2 = st.columns(2)
        for i, (label, value) in enumerate(metrics):
            col = mc1 if i % 2 == 0 else mc2
            col.markdown(
                f"""<div style="display:flex;justify-content:space-between;
                padding:8px 12px;border-bottom:1px solid #1a212c;font-size:13px;">
                <span style="color:#7c8798;">{label}</span>
                <span style="color:#e8ecf1;font-weight:600;">{value}</span>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown(
            """<div style="color:#7c8798;font-size:11px;margin-top:1rem;">
            Note: Fundamental analysis for informational purposes only, not investment advice.
            Health score is calculated using weighted averages of profitability, valuation,
            financial health, and growth metrics.</div>""",
            unsafe_allow_html=True,
        )
    else:
        st.info("Enter a stock ticker above and click **Analyze Fundamentals** to get a health score and key metrics.")
