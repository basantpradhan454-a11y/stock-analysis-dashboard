"""Quant Trading Dashboard Module
3 strategy categories with live equity curves, P&L tracking, and trade counts.
Categories: Arbitrage-based, Directional, Systematic/ML.
Each category has a code input, algorithm selector, and live simulation.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import time


# ── Strategy categories ──
CATEGORIES = [
    {
        "id": "arb",
        "name": "Arbitrage-based",
        "badge": "Arbitrage",
        "badge_color": "#5dcaa5",
        "bg_color": "rgba(29, 158, 117, 0.08)",
        "border_color": "rgba(29, 158, 117, 0.25)",
        "chart_color": "#1d9e75",
        "placeholder": "// e.g. stat arb pairs trading\nif (spread > threshold) short(A); long(B);",
        "default_algo": "meanrevert",
        "algos": [
            ("meanrevert", "Mean reversion signal"),
            ("trend", "Trend / momentum signal"),
            ("random", "Random walk (ML sim)"),
        ]},
    {
        "id": "dir",
        "name": "Directional",
        "badge": "Directional",
        "badge_color": "#f0997b",
        "bg_color": "rgba(216, 90, 48, 0.08)",
        "border_color": "rgba(216, 90, 48, 0.25)",
        "chart_color": "#d85a30",
        "placeholder": "// e.g. trend following\nif (price > sma50) buy(); else sell();",
        "default_algo": "trend",
        "algos": [
            ("meanrevert", "Mean reversion signal"),
            ("trend", "Trend / momentum signal"),
            ("random", "Random walk (ML sim)"),
        ]},
    {
        "id": "sys",
        "name": "Systematic / ML",
        "badge": "Systematic",
        "badge_color": "#afa9ec",
        "bg_color": "rgba(127, 119, 221, 0.08)",
        "border_color": "rgba(127, 119, 221, 0.25)",
        "chart_color": "#7f77dd",
        "placeholder": "// e.g. factor / ML signal\nscore = model.predict(features);\nif (score > 0.6) buy();",
        "default_algo": "random",
        "algos": [
            ("meanrevert", "Mean reversion signal"),
            ("trend", "Trend / momentum signal"),
            ("random", "Random walk (ML sim)"),
        ]},
]


def _next_price(algo, last, t, rng):
    """Generate next price based on algorithm type."""
    noise = rng.normal(0, 1)
    if algo == "trend":
        return last + noise * 0.6 + np.sin(t / 15) * 0.8
    elif algo == "meanrevert":
        pull = (100 - last) * 0.05
        return last + pull + noise * 0.5
    else:
        return last + noise * 1.2


def _hex_to_rgba(hex_color, alpha=0.1):
    """Convert a #RRGGBB hex string to a valid rgba(...) string for Plotly."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _render_equity_chart(data, chart_color, name):
    """Render an equity curve chart with Plotly."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=data,
        mode="lines",
        name=name,
        line=dict(color=chart_color, width=2),
        fill="tozeroy",
        fillcolor=_hex_to_rgba(chart_color, 0.10),
    ))
    fig.update_layout(
        template="plotly_dark",
        height=200,
        margin=dict(l=30, r=20, t=10, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(size=10, family="Trebuchet MS, sans-serif"),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(50,50,50,0.2)", tickformat=".1f", side="right"),
    )
    return fig


def render_quant_trading():
    """Main render function for the Quant Trading Dashboard."""
    st.markdown("""<div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,5,20,0.95));border:1px solid rgba(74,158,255,0.25);border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1.2rem;">
    <div style="font-size:1.3rem;font-weight:800;font-family:Orbitron,monospace;background:linear-gradient(90deg,#5dcaa5,#f0997b,#afa9ec);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
    \U0001f4c8 Quant Trading Dashboard</div>
    <div style="color:#8b949e;font-size:12px;margin-top:4px;">
    Paste your strategy logic in a category, hit run \u2014 each category gets its own live chart.</div>
    </div>""", unsafe_allow_html=True)

    # Initialize session state for each category
    for cat in CATEGORIES:
        if f"qt_{cat['id']}_running" not in st.session_state:
            st.session_state[f"qt_{cat['id']}_running"] = False
        if f"qt_{cat['id']}_data" not in st.session_state:
            st.session_state[f"qt_{cat['id']}_data"] = [100.0]
        if f"qt_{cat['id']}_trades" not in st.session_state:
            st.session_state[f"qt_{cat['id']}_trades"] = 0
        if f"qt_{cat['id']}_algo" not in st.session_state:
            st.session_state[f"qt_{cat['id']}_algo"] = cat["default_algo"]

    # Check if any strategy is running
    any_running = any(st.session_state[f"qt_{c['id']}_running"] for c in CATEGORIES)

    # Control bar
    ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 2])
    with ctrl1:
        if st.button("\u25b6\ufe0f Run All", type="primary", key="qt_run_all", disabled=any_running):
            for cat in CATEGORIES:
                st.session_state[f"qt_{cat['id']}_running"] = True
                st.session_state[f"qt_{cat['id']}_data"] = [100.0]
                st.session_state[f"qt_{cat['id']}_trades"] = 0
            st.rerun()
    with ctrl2:
        if st.button("\u23f9\ufe0f Stop All", key="qt_stop_all", disabled=not any_running):
            for cat in CATEGORIES:
                st.session_state[f"qt_{cat['id']}_running"] = False
            st.rerun()

    # Live simulation loop
    running_cats = [c for c in CATEGORIES if st.session_state[f"qt_{c['id']}_running"]]
    if running_cats:
        rng = np.random.default_rng(int(time.time()) % 2**31)
        # Generate one step for each running category
        for cat in running_cats:
            data = st.session_state[f"qt_{cat['id']}_data"]
            algo = st.session_state[f"qt_{cat['id']}_algo"]
            t = len(data)
            last = data[-1]
            new_price = _next_price(algo, last, t, rng)
            new_price = round(new_price, 2)
            data.append(new_price)
            if len(data) > 60:
                data.pop(0)
            # Random trade occurrence
            if rng.random() < 0.3:
                st.session_state[f"qt_{cat['id']}_trades"] += 1

        # Small delay for visual effect
        time.sleep(0.4)
        st.rerun()

    # Render category cards in a grid
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]

    for i, cat in enumerate(CATEGORIES):
        with cols[i]:
            # Card styling
            st.markdown(f"""<div style="background:{cat['bg_color']};border:1px solid {cat['border_color']};border-radius:12px;padding:1rem 1.2rem;margin-bottom:0.5rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-size:14px;font-weight:600;color:#e6e8eb;">{cat['name']}</span>
                <span style="font-size:11px;padding:2px 8px;border-radius:6px;background:{cat['bg_color']};color:{cat['badge_color']};">{cat['badge']}</span>
            </div>
            </div>""", unsafe_allow_html=True)

            # Code input
            code_key = f"qt_code_{cat['id']}"
            if code_key not in st.session_state:
                st.session_state[code_key] = cat["placeholder"]
            st.text_area(
                "Strategy Code",
                key=code_key,
                height=70,
                label_visibility="collapsed",
                help="Write your strategy logic here (for reference)",
            )

            # Algorithm selector + Run/Stop
            algo_col, run_col, stop_col = st.columns([2, 1, 1])
            with algo_col:
                algo_opts = cat["algos"]
                current_algo = st.session_state[f"qt_{cat['id']}_algo"]
                algo_idx = next((i for i, (v, _) in enumerate(algo_opts) if v == current_algo), 0)
                selected = st.selectbox(
                    "Algorithm",
                    options=[v for v, _ in algo_opts],
                    format_func=lambda v: next(l for vv, l in algo_opts if vv == v),
                    index=algo_idx,
                    key=f"qt_algo_select_{cat['id']}",
                    label_visibility="collapsed",
                )
                st.session_state[f"qt_{cat['id']}_algo"] = selected

            is_running = st.session_state[f"qt_{cat['id']}_running"]
            with run_col:
                if st.button("Run \u2197", key=f"qt_run_{cat['id']}", disabled=is_running,
                             help="Start live simulation"):
                    st.session_state[f"qt_{cat['id']}_running"] = True
                    st.session_state[f"qt_{cat['id']}_data"] = [100.0]
                    st.session_state[f"qt_{cat['id']}_trades"] = 0
                    st.rerun()
            with stop_col:
                if st.button("Stop", key=f"qt_stop_{cat['id']}", disabled=not is_running):
                    st.session_state[f"qt_{cat['id']}_running"] = False
                    st.rerun()

            # Status indicator
            if is_running:
                st.markdown(f'<p style="font-size:11px;color:{cat["badge_color"]};margin:2px 0 6px;">\U0001f7e2 live</p>', unsafe_allow_html=True)
            else:
                st.markdown(f'<p style="font-size:11px;color:#9aa0a8;margin:2px 0 6px;">\u26ab idle</p>', unsafe_allow_html=True)

            # Equity chart
            data = st.session_state[f"qt_{cat['id']}_data"]
            fig = _render_equity_chart(data, cat["chart_color"], cat["name"])
            st.plotly_chart(fig, use_container_width=True, config={
                "displayModeBar": False, "displaylogo": False, "staticPlot": True
            })

            # Stats: P&L and trades
            pnl = ((data[-1] - 100) / 100 * 100) if len(data) > 0 else 0
            pnl_color = "#5dcaa5" if pnl >= 0 else "#f0997b"
            trades = st.session_state[f"qt_{cat['id']}_trades"]
            st.markdown(
                f'<div style="display:flex;gap:16px;font-size:12px;color:#9aa0a8;margin-top:4px;">'
                f'<span>P&L: <b style="color:{pnl_color};">{pnl:.2f}%</b></span>'
                f'<span>Trades: <b style="color:#e6e8eb;">{trades}</b></span>'
                f'</div>',
                unsafe_allow_html=True,
            )
