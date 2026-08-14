"""Quant Trade Module — Full trading dashboard matching the React HTML UI.
Stock search with logos, TradingView chart, portfolio overview, backtester,
risk calc, options pricer, correlation, Monte Carlo, VaR, factor exposure,
quant signal screener, open positions, P&L calendar.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math
from modules.data_fetch import get_history

# ═══════════════════════════════════════════════════════════════════════════
# STOCK DATABASE (matching the HTML)
# ═══════════════════════════════════════════════════════════════════════════
STOCK_DB = [
    {"name": "Reliance Industries", "symbol": "NSE:RELIANCE", "exchange": "NSE", "logo": "RELIANCE", "price": 2915.4},
    {"name": "Tata Consultancy Services", "symbol": "NSE:TCS", "exchange": "NSE", "logo": "TCS", "price": 3760.1},
    {"name": "Infosys", "symbol": "NSE:INFY", "exchange": "NSE", "logo": "INFY", "price": 1842.6},
    {"name": "HDFC Bank", "symbol": "NSE:HDFCBANK", "exchange": "NSE", "logo": "HDFCBANK", "price": 1698.3},
    {"name": "ICICI Bank", "symbol": "NSE:ICICIBANK", "exchange": "NSE", "logo": "ICICIBANK", "price": 1256.8},
    {"name": "State Bank of India", "symbol": "NSE:SBIN", "exchange": "NSE", "logo": "SBIN", "price": 842.2},
    {"name": "Tata Motors", "symbol": "NSE:TATAMOTORS", "exchange": "NSE", "logo": "TATAMOTORS", "price": 1024.5},
    {"name": "Adani Enterprises", "symbol": "NSE:ADANIENT", "exchange": "NSE", "logo": "ADANIENT", "price": 3120.9},
    {"name": "Bajaj Finance", "symbol": "NSE:BAJFINANCE", "exchange": "NSE", "logo": "BAJFINANCE", "price": 7210.4},
    {"name": "Wipro", "symbol": "NSE:WIPRO", "exchange": "NSE", "logo": "WIPRO", "price": 562.7},
    {"name": "Nifty 50 Futures", "symbol": "NSE:NIFTY", "exchange": "NSE", "logo": "NIFTY", "price": 24480},
    {"name": "Bank Nifty", "symbol": "NSE:BANKNIFTY", "exchange": "NSE", "logo": "BANKNIFTY", "price": 52140},
    {"name": "Apple Inc", "symbol": "NASDAQ:AAPL", "exchange": "NASDAQ", "logo": "AAPL", "price": 224.1},
    {"name": "Microsoft", "symbol": "NASDAQ:MSFT", "exchange": "NASDAQ", "logo": "MSFT", "price": 441.3},
    {"name": "Amazon", "symbol": "NASDAQ:AMZN", "exchange": "NASDAQ", "logo": "AMZN", "price": 198.5},
    {"name": "Alphabet (Google)", "symbol": "NASDAQ:GOOGL", "exchange": "NASDAQ", "logo": "GOOGL", "price": 176.2},
    {"name": "Tesla", "symbol": "NASDAQ:TSLA", "exchange": "NASDAQ", "logo": "TSLA", "price": 256.8},
    {"name": "Meta Platforms", "symbol": "NASDAQ:META", "exchange": "NASDAQ", "logo": "META", "price": 512.4},
    {"name": "Nvidia", "symbol": "NASDAQ:NVDA", "exchange": "NASDAQ", "logo": "NVDA", "price": 132.7},
    {"name": "Bitcoin", "symbol": "BINANCE:BTCUSDT", "exchange": "Binance", "logo": "BTC", "price": 64200},
    {"name": "Ethereum", "symbol": "BINANCE:ETHUSDT", "exchange": "Binance", "logo": "ETH", "price": 3410},
]

def logo_url(t):
    return f"https://s3-symbol-logo.tradingview.com/{t.lower()}.svg"

# Demo positions (matching HTML)
POSITIONS = [
    {"sym": "RELIANCE", "side": "Long", "qty": 1200, "entry": 2840, "last": 2915, "pnl": 90000},
    {"sym": "TCS", "side": "Long", "qty": 600, "entry": 3820, "last": 3760, "pnl": -36000},
    {"sym": "NIFTY FUT", "side": "Short", "qty": 50, "entry": 24650, "last": 24480, "pnl": 8500},
    {"sym": "HDFCBANK", "side": "Long", "qty": 900, "entry": 1650, "last": 1698, "pnl": 43200},
    {"sym": "AAPL", "side": "Short", "qty": 300, "entry": 228, "last": 224, "pnl": 1200},
]

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
STRATEGY_EQ = [100, 103, 101, 108, 112, 109, 117, 121, 118, 126, 131, 124]
BENCH_EQ = [100, 101, 99, 103, 104, 102, 106, 108, 105, 109, 111, 111]
DD_SERIES = [0, -1.2, -3.5, -0.8, 0, -2.1, 0, 0, -1.9, 0, 0, -8.4]
FACTOR_NAMES = ['Momentum', 'Value', 'Size', 'Quality', 'Volatility']
FACTOR_VALS = [0.42, -0.18, 0.09, 0.31, -0.22]


# ═══════════════════════════════════════════════════════════════════════════
# NAV CONFIG (matching the HTML)
# ═══════════════════════════════════════════════════════════════════════════
NAV_GROUPS = [
    {"group": "Markets", "items": [
        {"id": "screener", "icon": "\U0001f50d", "label": "Stock search / screener"},
        {"id": "chart", "icon": "\U0001f4c8", "label": "TradingView chart"},
        {"id": "overview", "icon": "\U0001f4ca", "label": "Portfolio overview"},
    ]},
    {"group": "Quant tools", "items": [
        {"id": "backtest", "icon": "\u23f1\ufe0f", "label": "Strategy backtester"},
        {"id": "riskcalc", "icon": "\U0001f9ee", "label": "Position size and risk"},
        {"id": "optionpricer", "icon": "\u03a9", "label": "Options pricer (Black-Scholes)"},
        {"id": "correlation", "icon": "\U0001f517", "label": "Correlation matrix"},
        {"id": "montecarlo", "icon": "\U0001f3b0", "label": "Monte Carlo simulator"},
        {"id": "var", "icon": "\u26a0\ufe0f", "label": "Value at Risk (VaR)"},
        {"id": "factor", "icon": "\U0001f9ec", "label": "Factor exposure"},
        {"id": "screenerquant", "icon": "\U0001f9e0", "label": "Quant signal screener"},
    ]},
    {"group": "Portfolio", "items": [
        {"id": "positions", "icon": "\U0001f4cb", "label": "Open positions"},
        {"id": "pnlcal", "icon": "\U0001f4c5", "label": "P&L calendar"},
    ]},
]


# ═══════════════════════════════════════════════════════════════════════════
# 1. STOCK SEARCH / SCREENER
# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
def _render_screener():
    st.markdown("## \U0001f50d Stock Search")
    st.caption("Kisi bhi stock ko choose karne par chart khulega. Search ya direct select karo.")

    q = st.text_input("Search stocks", placeholder="e.g. Reliance, TCS, Apple, Bitcoin", key="qt_screener_input")

    # Build the list to display
    if q.strip():
        matches = [s for s in STOCK_DB if q.lower() in s["name"].lower() or q.lower() in s["symbol"].lower()]
    else:
        matches = STOCK_DB

    if not matches:
        st.info("No matches found.")
        return

    st.markdown(f"**{len(matches)} stocks found** \u2014 click any to open chart")

    # Render as clickable cards using st.button
    cols = st.columns(3)
    for i, s in enumerate(matches):
        with cols[i % 3]:
            # Logo + exchange as HTML header
            html = (
                "<div style='display:flex;align-items:center;gap:8px;margin-bottom:-12px;'>"
                f"<img src='{logo_url(s['logo'])}' "
                "onerror='this.style.display=\"none\"' "
                "style='width:24px;height:24px;border-radius:4px;background:#fff;' />"
                f"<span style='font-size:12px;color:#8b949e;'>{s['exchange']}</span>"
                "</div>"
            )
            st.markdown(html, unsafe_allow_html=True)
            if st.button(s["name"], key=f"qt_stock_{s['logo']}", use_container_width=True,
                         help=f"{s['symbol']} \u00b7 {s['exchange']}"):
                st.session_state["qt_selected_stock"] = s
                st.session_state["qt_subview"] = "chart"
                st.rerun()

    # Also show a selectbox as alternative
    st.markdown("---")
    options = [f"{s['name']} ({s['symbol']})" for s in matches]
    sel = st.selectbox("Or select from dropdown:", options, key="qt_screener_sel")
    if st.button("\U0001f4c8 Open Chart", key="qt_screener_go", type="primary"):
        idx = options.index(sel)
        st.session_state["qt_selected_stock"] = matches[idx]
        st.session_state["qt_subview"] = "chart"
        st.rerun()


def _render_chart():
    st.markdown("## \U0001f4c8 Live Candlestick Chart")
    st.caption("Full TradingView chart \u2014 indicators, drawing tools, timeframes, and symbol switch all included.")

    # Search box
    q = st.text_input("Search a stock to load its chart", placeholder="e.g. Reliance, Apple, Bitcoin", key="qt_chart_search")

    # Get selected stock
    selected = st.session_state.get("qt_selected_stock", STOCK_DB[0])

    if q.strip():
        matches = [s for s in STOCK_DB if q.lower() in s["name"].lower() or q.lower() in s["symbol"].lower()]
        if matches:
            options = [f"{s['name']} ({s['symbol']})" for s in matches]
            sel = st.selectbox("Select:", options, key="qt_chart_sel")
            idx = options.index(sel)
            selected = matches[idx]

    # Show selected header
    st.markdown(f"""
    <div style='display:flex;align-items:center;gap:10px;margin:10px 0;'>
        <img src='{logo_url(selected["logo"])}' onerror='this.style.display="none"' style='width:30px;height:30px;border-radius:6px;background:#fff;' />
        <div>
            <div style='font-weight:600;font-size:14px;color:#e6edf3;'>{selected["name"]}</div>
            <div style='font-size:12px;color:#8b949e;'>{selected["symbol"]} \u00b7 {selected["exchange"]}</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # TradingView widget (self-contained, no import from app.py)
    import streamlit.components.v1 as _components
    tv_symbol = selected["symbol"] if ":" in selected["symbol"] else f"NSE:{selected['symbol']}"

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("\U0001f5fa\ufe0f Open Fullscreen", key="qt_chart_fs", use_container_width=True):
            st.session_state["qt_fullscreen"] = not st.session_state.get("qt_fullscreen", False)
            st.rerun()

    if st.session_state.get("qt_fullscreen", False):
        html = f'''
        <div id="tv-fs" style="position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:99999;background:#131722;">
          <div class="tradingview-widget-container" style="height:100vh;width:100vw;">
            <div class="tradingview-widget-container__widget" style="height:100vh;width:100vw;"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
            {{
              "autosize": true,
              "symbol": "{tv_symbol}",
              "interval": "D",
              "timezone": "Asia/Kolkata",
              "theme": "dark",
              "style": "1",
              "locale": "in",
              "toolbar_bg": "#131722",
              "enable_publishing": false,
              "withdateranges": true,
              "hide_side_toolbar": false,
              "allow_symbol_change": true,
              "studies": ["STD;SMA", "STD;RSI", "Volume@tv-basicstudies", "STD;MACD", "STD;Bollinger_Bands"],
              "support_host": "https://www.tradingview.com"
            }}
            </script>
          </div>
          <button onclick="var e=document.getElementById('tv-fs');e.parentNode.removeChild(e);document.body.style.overflow='';" style="position:fixed;top:12px;right:12px;z-index:100000;background:#ef4444;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:14px;cursor:pointer;font-weight:600;">\u2716 Close</button>
        </div>
        <script>document.body.style.overflow='hidden';</script>
        '''
        _components.html(html, height=1000)
        if st.button("Exit Fullscreen", key="qt_fs_exit", type="secondary"):
            st.session_state["qt_fullscreen"] = False
            st.rerun()
    else:
        html = f'''
        <div class="tradingview-widget-container" style="height:560px;width:100%;">
          <div class="tradingview-widget-container__widget" style="height:560px;width:100%;"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
            "autosize": true,
            "symbol": "{tv_symbol}",
            "interval": "D",
            "timezone": "Asia/Kolkata",
            "theme": "dark",
            "style": "1",
            "locale": "in",
            "toolbar_bg": "#131722",
            "enable_publishing": false,
            "withdateranges": true,
            "hide_side_toolbar": false,
            "allow_symbol_change": true,
            "studies": ["STD;SMA", "STD;RSI", "Volume@tv-basicstudies", "STD;MACD", "STD;Bollinger_Bands"],
            "support_host": "https://www.tradingview.com"
          }}
          </script>
        </div>
        '''
        _components.html(html, height=560)

    # Quick switch buttons
    st.markdown("#### Quick switch")
    quick_cols = st.columns(6)
    quick_stocks = STOCK_DB[:6]
    for i, s in enumerate(quick_stocks):
        with quick_cols[i]:
            if st.button(s["logo"], key=f"qt_quick_{s['logo']}", use_container_width=True):
                st.session_state["qt_selected_stock"] = s
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# 3. PORTFOLIO OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════
def _render_overview():
    st.markdown("## \U0001f4ca Portfolio Overview")
    st.caption("Live snapshot of strategy performance versus benchmark.")

    # Metric cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Portfolio value", "$4.82M", "+1.34% today")
    m2.metric("Sharpe ratio", "1.87", "Trailing 252d")
    m3.metric("Max drawdown", "-8.4%", "Since inception")
    m4.metric("Net exposure", "62%", "Gross 148%")

    # Equity curve vs benchmark
    st.markdown("#### Equity curve vs benchmark")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=MONTHS, y=STRATEGY_EQ, name="Strategy", line=dict(color="#3b82f6", width=2)))
    fig.add_trace(go.Scatter(x=MONTHS, y=BENCH_EQ, name="Benchmark", line=dict(color="#8b949e", width=2)))
    fig.update_layout(height=240, margin=dict(l=0, r=0, t=10, b=0),
                      paper_bgcolor="#151b23", plot_bgcolor="#151b23",
        dragmode="zoom", hovermode="x unified",
                      font=dict(color="#e6edf3"), xaxis=dict(gridcolor="#2a3441"), yaxis=dict(gridcolor="#2a3441"))
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "doubleClick": "reset", "modeBarButtonsToAdd": ["drawline", "eraseshape"],
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })

    # Drawdown
    st.markdown("#### Drawdown")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=MONTHS, y=DD_SERIES, name="Drawdown", marker_color="#ef4444"))
    fig2.update_layout(height=170, margin=dict(l=0, r=0, t=10, b=0),
                       paper_bgcolor="#151b23", plot_bgcolor="#151b23",
        dragmode="zoom", hovermode="x unified",
                       font=dict(color="#e6edf3"), xaxis=dict(gridcolor="#2a3441"), yaxis=dict(gridcolor="#2a3441"))
    st.plotly_chart(fig2, use_container_width=True, config={
        "scrollZoom": True, "doubleClick": "reset", "modeBarButtonsToAdd": ["drawline", "eraseshape"],
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })


# ═══════════════════════════════════════════════════════════════════════════
# 4. STRATEGY BACKTESTER
# ═══════════════════════════════════════════════════════════════════════════
def _render_backtest():
    st.markdown("## \u23f1\ufe0f Strategy Backtester")
    st.caption("Backtest a simple moving-average crossover strategy.")

    c1, c2, c3, c4 = st.columns(4)
    with c1: sym = st.text_input("Symbol", value="RELIANCE.NS", key="qt_bt_sym")
    with c2: fast = st.slider("Fast MA", 3, 30, 10, key="qt_bt_fast")
    with c3: slow = st.slider("Slow MA", 10, 100, 30, key="qt_bt_slow")
    with c4: period = st.selectbox("Period", ["6mo", "1y", "2y", "5y", "10y"], index=4, key="qt_bt_period")

    if st.button("Run Backtest", type="primary", key="qt_bt_run"):
        with st.spinner("Running backtest..."):
            df, is_synthetic = get_history(sym, period=period, interval="1d")
            if df is None or df.empty:
                st.error("No data.")
                return
            if is_synthetic:
                st.caption("\u26a0\ufe0f Live feed rate-limited \u2014 showing simulated candles.")
            df["MA_fast"] = df["Close"].rolling(fast).mean()
            df["MA_slow"] = df["Close"].rolling(slow).mean()
            df["Signal"] = (df["MA_fast"] > df["MA_slow"]).astype(int).diff()
            position = 0
            entry_price = 0
            trades = []
            for i in range(len(df)):
                sig = df["Signal"].iloc[i]
                price = df["Close"].iloc[i]
                if sig == 1 and position == 0:
                    position = 1
                    entry_price = price
                    trades.append({"Date": df.index[i].strftime("%Y-%m-%d"), "Action": "BUY", "Price": round(price, 2)})
                elif sig == -1 and position == 1:
                    pnl = (price - entry_price) / entry_price * 100
                    trades.append({"Date": df.index[i].strftime("%Y-%m-%d"), "Action": "SELL", "Price": round(price, 2), "P&L%": round(pnl, 2)})
                    position = 0
                    entry_price = 0

            # Equity curve
            df["Strategy"] = df["Close"].pct_change().fillna(0) * df["Signal"].shift(1).fillna(0)
            df["Strategy_equity"] = (1 + df["Strategy"]).cumprod()
            df["Buy_hold"] = (1 + df["Close"].pct_change().fillna(0)).cumprod()

            strat_ret = (df["Strategy_equity"].iloc[-1] - 1) * 100
            bh_ret = (df["Buy_hold"].iloc[-1] - 1) * 100

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Strategy Return", f"{strat_ret:+.2f}%")
        m2.metric("Buy & Hold", f"{bh_ret:+.2f}%")
        m3.metric("Trades", len(trades))
        m4.metric("Final Equity", f"${df['Strategy_equity'].iloc[-1]:.2f}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["Strategy_equity"], name="Strategy", line=dict(color="#3b82f6", width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=df["Buy_hold"], name="Buy & Hold", line=dict(color="#8b949e", width=2)))
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                          paper_bgcolor="#151b23", plot_bgcolor="#151b23",
        dragmode="zoom", hovermode="x unified",
                          font=dict(color="#e6edf3"), xaxis=dict(gridcolor="#2a3441"), yaxis=dict(gridcolor="#2a3441"))
        st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "doubleClick": "reset", "modeBarButtonsToAdd": ["drawline", "eraseshape"],
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })

        if trades:
            st.markdown("#### Trade History")
            st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# 5. RISK CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════
def _render_riskcalc():
    st.markdown("## \U0001f9ee Position Size & Risk Calculator")
    st.caption("Calculate optimal position size based on your risk tolerance and stop loss.")

    c1, c2, c3, c4 = st.columns(4)
    with c1: capital = st.number_input("Total Capital", value=100000, step=10000, key="qt_rc_cap")
    with c2: risk_pct = st.slider("Risk per trade (%)", 0.5, 20.0, 2.0, 0.5, key="qt_rc_risk")
    with c3: entry = st.number_input("Entry Price", value=100.0, step=0.5, format="%.2f", key="qt_rc_entry")
    with c4: stop = st.number_input("Stop Loss Price", value=95.0, step=0.5, format="%.2f", key="qt_rc_stop")

    risk_amt = capital * (risk_pct / 100)
    per_share = abs(entry - stop)
    if per_share > 0:
        shares = int(risk_amt / per_share)
        pos_val = shares * entry
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Risk Amount", f"\u20b9{risk_amt:,.2f}")
        m2.metric("Risk/Share", f"\u20b9{per_share:.2f}")
        m3.metric("Max Position", f"{shares:,} shares")
        m4.metric("Position Value", f"\u20b9{pos_val:,.2f}")

        target = st.number_input("Target Price", value=110.0, step=0.5, format="%.2f", key="qt_rc_target")
        rr = (target - entry) / per_share if per_share > 0 else 0
        st.metric("Risk:Reward", f"1:{rr:.2f}")


# ═══════════════════════════════════════════════════════════════════════════
# 6. OPTIONS PRICER
# ═══════════════════════════════════════════════════════════════════════════
def _render_optionpricer():
    st.markdown("## \u03a9 Options Pricer (Black-Scholes)")
    st.caption("Price European call and put options using the Black-Scholes-Merton model.")

    # Pure Python normal distribution (no scipy needed)
    import math as _m2
    def _norm_cdf(x):
        return 0.5 * (1 + _m2.erf(x / _m2.sqrt(2)))
    def _norm_pdf(x):
        return _m2.exp(-x**2 / 2) / _m2.sqrt(2 * _m.pi)
    class _norm:
        cdf = staticmethod(_norm_cdf)
        pdf = staticmethod(_norm_pdf)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: S = st.number_input("Spot Price (S)", value=100.0, step=0.5, format="%.2f", key="qt_op_S")
    with c2: K = st.number_input("Strike Price (K)", value=100.0, step=0.5, format="%.2f", key="qt_op_K")
    with c3: T_days = st.number_input("Days to Expiry", value=30, step=1, key="qt_op_T")
    with c4: r_pct = st.number_input("Risk-free Rate (%)", value=6.5, step=0.1, format="%.1f", key="qt_op_r")
    with c5: vol_pct = st.number_input("Volatility (%)", value=25.0, step=0.5, format="%.1f", key="qt_op_vol")

    T = T_days / 365
    r = r_pct / 100
    sigma = vol_pct / 100

    def bs(S, K, T, r, sigma, typ):
        if T <= 0 or sigma <= 0:
            intr = max(S - K, 0) if typ == "call" else max(K - S, 0)
            return intr, 0, 0, 0, 0, 0
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        if typ == "call":
            price = S * _norm.cdf(d1) - K * math.exp(-r * T) * _norm.cdf(d2)
            delta = _norm.cdf(d1)
        else:
            price = K * math.exp(-r * T) * _norm.cdf(-d2) - S * _norm.cdf(-d1)
            delta = _norm.cdf(d1) - 1
        gamma = _norm.pdf(d1) / (S * sigma * math.sqrt(T))
        vega = S * math.sqrt(T) * _norm.pdf(d1) / 100
        theta = (-(S * _norm.pdf(d1) * sigma) / (2 * math.sqrt(T))) / 365
        rho = (K * T * math.exp(-r * T) * (_norm.cdf(d2) if typ == "call" else _norm.cdf(-d2))) / 100
        return price, delta, gamma, vega, theta, rho

    cp, cd, cg, cv, ct, cr = bs(S, K, T, r, sigma, "call")
    pp, pd, pg, pv, pt, pr = bs(S, K, T, r, sigma, "put")

    p1, p2 = st.columns(2)
    p1.metric("Call Price", f"\u20b9{cp:.2f}", f"\u0394={cd:.4f}")
    p2.metric("Put Price", f"\u20b9{pp:.2f}", f"\u0394={pd:.4f}")

    st.markdown("#### Greeks")
    gdf = pd.DataFrame({
        "Greek": ["Price", "Delta", "Gamma", "Vega (1%)", "Theta (day)", "Rho (1%)"],
        "Call": [f"\u20b9{cp:.2f}", f"{cd:.4f}", f"{cg:.6f}", f"{cv:.4f}", f"{ct:.4f}", f"{cr:.4f}"],
        "Put": [f"\u20b9{pp:.2f}", f"{pd:.4f}", f"{pg:.6f}", f"{pv:.4f}", f"{pt:.4f}", f"{pr:.4f}"],
    })
    st.dataframe(gdf, use_container_width=True, hide_index=True)

    # Payoff
    prices = np.linspace(S * 0.7, S * 1.3, 50)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices, y=np.maximum(prices - K, 0) - cp, name="Call P&L", line=dict(color="#22c55e", width=2)))
    fig.add_trace(go.Scatter(x=prices, y=np.maximum(K - prices, 0) - pp, name="Put P&L", line=dict(color="#ef4444", width=2)))
    fig.add_hline(y=0, line=dict(color="#8b949e", width=1, dash="dash"))
    fig.add_vline(x=K, line=dict(color="#3b82f6", width=1, dash="dot"))
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Spot at Expiry", yaxis_title="P&L",
                      paper_bgcolor="#151b23", plot_bgcolor="#151b23", font=dict(color="#e6edf3"),
        dragmode="zoom", hovermode="x unified",
                      xaxis=dict(gridcolor="#2a3441"), yaxis=dict(gridcolor="#2a3441"))
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "doubleClick": "reset", "modeBarButtonsToAdd": ["drawline", "eraseshape"],
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })


# ═══════════════════════════════════════════════════════════════════════════
# 7. CORRELATION MATRIX
# ═══════════════════════════════════════════════════════════════════════════
def _render_correlation():
    st.markdown("## \U0001f517 Correlation Matrix")
    st.caption("Compare return correlations between assets to diversify your portfolio.")

    syms = st.text_input("Symbols (comma-separated)", value="RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, ^NSEI", key="qt_corr_sym")
    period = st.selectbox("Period", ["3mo", "6mo", "1y", "2y", "5y", "10y"], index=5, key="qt_corr_period")

    if st.button("Compute Correlation", type="primary", key="qt_corr_btn"):
        symbols = [s.strip() for s in syms.split(",") if s.strip()]
        with st.spinner(f"Fetching data for {len(symbols)} assets..."):
            rdf = pd.DataFrame()
            for sym in symbols:
                try:
                    df, _ = get_history(sym, period=period, interval="1d")
                    if df is not None and not df.empty:
                        rdf[sym] = df["Close"].pct_change()
                except Exception:
                    pass
        if rdf.empty or len(rdf.columns) < 2:
            st.error("Not enough data.")
            return
        corr = rdf.corr()
        fig = go.Figure(go.Heatmap(z=corr.values, x=corr.columns, y=corr.columns, colorscale="RdYlGn", zmid=0, zmin=-1, zmax=1,
                                   text=corr.values.round(2), texttemplate="%{text}", textfont=dict(size=10)))
        fig.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="#151b23", font=dict(color="#e6edf3"))
        st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "doubleClick": "reset", "modeBarButtonsToAdd": ["drawline", "eraseshape"],
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })


# ═══════════════════════════════════════════════════════════════════════════
# 8. MONTE CARLO SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════
def _render_montecarlo():
    st.markdown("## \U0001f3b0 Monte Carlo Simulator")
    st.caption("Simulate future price paths using Geometric Brownian Motion (GBM).")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: sym = st.text_input("Symbol", value="RELIANCE.NS", key="qt_mc_sym")
    with c2: days = st.slider("Days", 10, 365, 90, key="qt_mc_days")
    with c3: n_sims = st.slider("Simulations", 100, 5000, 500, 50, key="qt_mc_sims")
    with c4: conf = st.selectbox("Confidence", [90, 95, 99], index=1, key="qt_mc_conf")
    with c5: period = st.selectbox("History", ["3mo", "6mo", "1y", "2y", "5y", "10y"], index=5, key="qt_mc_period")

    if st.button("Run Simulation", type="primary", key="qt_mc_run"):
        with st.spinner("Running Monte Carlo simulation..."):
            df, is_synthetic = get_history(sym, period=period, interval="1d")
            if df is None or df.empty:
                st.error(f"No data for {sym}")
                return
            if is_synthetic:
                st.caption("\u26a0\ufe0f Live feed rate-limited \u2014 showing simulated candles.")
            S0 = float(df["Close"].iloc[-1])
            rets = df["Close"].pct_change().dropna()
            mu = rets.mean() * 252
            sigma = rets.std() * math.sqrt(252)
            dt = 1 / 252
            np.random.seed(42)
            paths = np.zeros((n_sims, days + 1))
            paths[:, 0] = S0
            for t in range(1, days + 1):
                z = np.random.standard_normal(n_sims)
                paths[:, t] = paths[:, t-1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z)

        fp = paths[:, -1]
        lo = np.percentile(fp, (100 - conf) / 2)
        med = np.percentile(fp, 50)
        hi = np.percentile(fp, 100 - (100 - conf) / 2)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Current", f"\u20b9{S0:.2f}")
        m2.metric(f"{conf}% Low", f"\u20b9{lo:.2f}", f"{(lo/S0-1)*100:+.1f}%")
        m3.metric("Median", f"\u20b9{med:.2f}", f"{(med/S0-1)*100:+.1f}%")
        m4.metric(f"{conf}% High", f"\u20b9{hi:.2f}", f"{(hi/S0-1)*100:+.1f}%")
        m5.metric("Drift", f"{mu*100:.1f}%")

        fig = go.Figure()
        for i in range(min(n_sims, 50)):
            fig.add_trace(go.Scatter(x=list(range(days+1)), y=paths[i], mode="lines", line=dict(width=0.5), opacity=0.3, showlegend=False))
        fig.add_trace(go.Scatter(x=list(range(days+1)), y=np.percentile(paths, 5, axis=0), name=f"{conf}% Low", line=dict(color="#ef4444", width=2)))
        fig.add_trace(go.Scatter(x=list(range(days+1)), y=np.percentile(paths, 50, axis=0), name="Median", line=dict(color="#3b82f6", width=2)))
        fig.add_trace(go.Scatter(x=list(range(days+1)), y=np.percentile(paths, 95, axis=0), name=f"{conf}% High", line=dict(color="#22c55e", width=2)))
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Days", yaxis_title="Price",
                          paper_bgcolor="#151b23", plot_bgcolor="#151b23", font=dict(color="#e6edf3"),
        dragmode="zoom", hovermode="x unified",
                          xaxis=dict(gridcolor="#2a3441"), yaxis=dict(gridcolor="#2a3441"))
        st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "doubleClick": "reset", "modeBarButtonsToAdd": ["drawline", "eraseshape"],
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })


# ═══════════════════════════════════════════════════════════════════════════
# 9. VALUE AT RISK
# ═══════════════════════════════════════════════════════════════════════════
def _render_var():
    # Pure Python normal distribution (no scipy needed)
    import math as _m2
    def _norm_cdf(x):
        return 0.5 * (1 + _m2.erf(x / _m2.sqrt(2)))
    def _norm_pdf(x):
        return _m2.exp(-x**2 / 2) / _m2.sqrt(2 * _m.pi)
    class _norm:
        cdf = staticmethod(_norm_cdf)
        pdf = staticmethod(_norm_pdf)
    st.markdown("## \u26a0\ufe0f Value at Risk (VaR)")
    st.caption("Estimate potential portfolio losses using historical and parametric methods.")

    c1, c2, c3, c4 = st.columns(4)
    with c1: pv = st.number_input("Portfolio Value", value=1000000, step=100000, key="qt_var_pv")
    with c2: syms = st.text_input("Holdings", value="RELIANCE.NS, TCS.NS, INFY.NS", key="qt_var_sym")
    with c3: weights_text = st.text_input("Weights", value="0.4, 0.35, 0.25", key="qt_var_w")
    with c4: period = st.selectbox("Lookback", ["3mo", "6mo", "1y", "2y", "5y", "10y"], index=5, key="qt_var_period")

    confs = st.multiselect("Confidence Levels", [90, 95, 99], default=[95, 99], key="qt_var_conf")
    horizon = st.slider("Horizon (days)", 1, 20, 1, key="qt_var_horizon")

    if st.button("Calculate VaR", type="primary", key="qt_var_btn"):
        symbols = [s.strip() for s in syms.split(",") if s.strip()]
        try:
            weights = [float(w.strip()) for w in weights_text.split(",")]
        except Exception:
            st.error("Invalid weights.")
            return
        if len(symbols) != len(weights):
            st.error("Symbols and weights count mismatch.")
            return

        with st.spinner("Fetching data..."):
            rdf = pd.DataFrame()
            for sym in symbols:
                try:
                    df, _ = get_history(sym, period=period, interval="1d")
                    if df is not None and not df.empty:
                        rdf[sym] = df["Close"].pct_change()
                except Exception:
                    pass
        if rdf.empty:
            st.error("No data.")
            return

        port_ret = (rdf[symbols] * weights).sum(axis=1).dropna()
        for c in confs:
            alpha = 1 - c / 100
            z = _norm.ppf(alpha)
            mean = port_ret.mean()
            std = port_ret.std()
            p_var = pv * (mean * horizon + z * std * math.sqrt(horizon)) * -1
            h_var = pv * np.percentile(port_ret, alpha * 100) * math.sqrt(horizon) * -1
            es_thresh = np.percentile(port_ret, alpha * 100)
            cvar = pv * port_ret[port_ret <= es_thresh].mean() * math.sqrt(horizon) * -1

            color = "#ef4444" if c == 99 else "#f59e0b" if c == 95 else "#3b82f6"
            st.markdown(f"""
            <div style='border:1px solid {color}33;border-radius:10px;padding:14px;margin:8px 0;background:{color}08;'>
                <div style='font-weight:700;color:{color};'>{c}% Confidence ({horizon}d)</div>
                <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:8px;'>
                    <div><div style='font-size:11px;color:#8b949e;'>Parametric VaR</div><div style='font-weight:600;font-size:18px;'>-\u20b9{p_var:,.0f}</div></div>
                    <div><div style='font-size:11px;color:#8b949e;'>Historical VaR</div><div style='font-weight:600;font-size:18px;'>-\u20b9{h_var:,.0f}</div></div>
                    <div><div style='font-size:11px;color:#8b949e;'>Expected Shortfall</div><div style='font-weight:600;font-size:18px;'>-\u20b9{cvar:,.0f}</div></div>
                </div>
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# 10. FACTOR EXPOSURE
# ═══════════════════════════════════════════════════════════════════════════
def _render_factor():
    st.markdown("## \U0001f9ec Factor Exposure")
    st.caption("Analyze your portfolio's exposure to common risk factors.")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("#### Factor Values")
        vals = []
        for f in FACTOR_NAMES:
            v = st.slider(f, -1.0, 1.0, float(FACTOR_VALS[FACTOR_NAMES.index(f)]), 0.01, key=f"qt_fe_{f}")
            vals.append(v)

    with col2:
        colors = ["#22c55e" if v >= 0 else "#ef4444" for v in vals]
        fig = go.Figure(go.Bar(x=vals, y=FACTOR_NAMES, orientation="h", marker_color=colors,
                               text=[f"{v:+.2f}" for v in vals], textposition="outside"))
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[-1, 1], gridcolor="#2a3441"),
                          paper_bgcolor="#151b23", plot_bgcolor="#151b23", font=dict(color="#e6edf3"),
        dragmode="zoom", hovermode="x unified",
                          yaxis=dict(gridcolor="#2a3441"))
        st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "doubleClick": "reset", "modeBarButtonsToAdd": ["drawline", "eraseshape"],
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })

    pos = sum(1 for v in vals if v > 0)
    neg = sum(1 for v in vals if v < 0)
    st.info(f"**{pos} positive** and **{neg} negative** factor exposures. "
            f"Strongest: **{FACTOR_NAMES[vals.index(max(vals))]}** ({max(vals):+.2f}). "
            f"Weakest: **{FACTOR_NAMES[vals.index(min(vals))]}** ({min(vals):+.2f}).")


# ═══════════════════════════════════════════════════════════════════════════
# 11. QUANT SIGNAL SCREENER
# ═══════════════════════════════════════════════════════════════════════════
def _render_screener_quant():
    st.markdown("## \U0001f9e0 Quant Signal Screener")
    st.caption("Screen multiple stocks for buy/sell signals based on technical indicators.")

    syms = st.text_input("Symbols to scan", value="RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, ICICIBANK.NS, SBIN.NS, TATAMOTORS.NS, WIPRO.NS", key="qt_qs_sym")
    symbols = [s.strip() for s in syms.split(",") if s.strip()]

    if st.button("Scan Signals", type="primary", use_container_width=True, key="qt_qs_scan"):
        results = []
        prog = st.progress(0)
        for i, sym in enumerate(symbols):
            prog.progress((i + 1) / max(len(symbols), 1))
            try:
                df, _ = get_history(sym, period="3mo", interval="1d")
                if df is None or df.empty or len(df) < 50:
                    continue
                close = df["Close"]
                rsi = 100 - 100 / (1 + close.diff().clip(lower=0).rolling(14).mean() / (-close.diff().clip(upper=0).rolling(14).mean().replace(0, np.nan)))
                sma20 = close.rolling(20).mean()
                sma50 = close.rolling(50).mean()
                ema12 = close.ewm(span=12, adjust=False).mean()
                ema26 = close.ewm(span=26, adjust=False).mean()
                macd = ema12 - ema26
                signal = macd.ewm(span=9, adjust=False).mean()

                l_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
                l_close = float(close.iloc[-1])
                l_sma20 = float(sma20.iloc[-1]) if not pd.isna(sma20.iloc[-1]) else l_close
                l_sma50 = float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else l_close
                l_macd = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0
                l_sig = float(signal.iloc[-1]) if not pd.isna(signal.iloc[-1]) else 0

                bull = 0
                if l_rsi < 35: bull += 2
                elif l_rsi > 65: bull -= 2
                if l_macd > l_sig: bull += 1
                else: bull -= 1
                if l_close > l_sma20: bull += 1
                else: bull -= 1
                if l_sma20 > l_sma50: bull += 1
                else: bull -= 1

                action = "BUY" if bull >= 3 else "SELL" if bull <= -3 else "HOLD"
                results.append({"Symbol": sym, "Price": round(l_close, 2), "RSI": round(l_rsi, 1),
                                "MACD": "Bull" if l_macd > l_sig else "Bear",
                                "Trend": "Up" if l_sma20 > l_sma50 else "Down",
                                "Signal": action, "Score": bull})
            except Exception:
                pass
        prog.empty()

        if not results:
            st.warning("No results.")
            return

        df_res = pd.DataFrame(results)
        def _color_sig(val):
            if val == "BUY": return "color:#22c55e;font-weight:700"
            elif val == "SELL": return "color:#ef4444;font-weight:700"
            return "color:#8b949e"
        st.dataframe(df_res.style.map(_color_sig, subset=["Signal"]), use_container_width=True, hide_index=True)

        b1, b2, b3 = st.columns(3)
        b1.metric("Buy Signals", len(df_res[df_res["Signal"] == "BUY"]))
        b2.metric("Sell Signals", len(df_res[df_res["Signal"] == "SELL"]))
        b3.metric("Hold", len(df_res[df_res["Signal"] == "HOLD"]))


# ═══════════════════════════════════════════════════════════════════════════
# 12. OPEN POSITIONS
# ═══════════════════════════════════════════════════════════════════════════
def _render_positions():
    st.markdown("## \U0001f4cb Open Positions")
    st.caption("Current portfolio positions with live P&L.")

    df = pd.DataFrame(POSITIONS)
    df["P&L"] = df["pnl"].apply(lambda x: f"\u20b9{x:+,.0f}")
    df["Side"] = df["side"].apply(lambda s: f"\U0001f7e2 {s}" if s == "Long" else f"\U0001f534 {s}")

    # Summary metrics
    total_pnl = sum(p["pnl"] for p in POSITIONS)
    total_long = sum(1 for p in POSITIONS if p["side"] == "Long")
    total_short = sum(1 for p in POSITIONS if p["side"] == "Short")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total P&L", f"\u20b9{total_pnl:+,.0f}")
    m2.metric("Positions", len(POSITIONS))
    m3.metric("Long", total_long)
    m4.metric("Short", total_short)

    # Positions table
    st.dataframe(df[["sym", "Side", "qty", "entry", "last", "P&L"]].rename(columns={
        "sym": "Symbol", "qty": "Qty", "entry": "Entry", "last": "Last"
    }), use_container_width=True, hide_index=True)

    # P&L bar chart
    fig = go.Figure(go.Bar(x=[p["sym"] for p in POSITIONS], y=[p["pnl"] for p in POSITIONS],
                           marker_color=["#22c55e" if p["pnl"] >= 0 else "#ef4444" for p in POSITIONS],
                           text=[f"\u20b9{p['pnl']:+,.0f}" for p in POSITIONS], textposition="outside"))
    fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Symbol", yaxis_title="P&L",
                      paper_bgcolor="#151b23", plot_bgcolor="#151b23", font=dict(color="#e6edf3"),
        dragmode="zoom", hovermode="x unified",
                      xaxis=dict(gridcolor="#2a3441"), yaxis=dict(gridcolor="#2a3441"))
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "doubleClick": "reset", "modeBarButtonsToAdd": ["drawline", "eraseshape"],
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })


# ═══════════════════════════════════════════════════════════════════════════
# 13. P&L CALENDAR
# ═══════════════════════════════════════════════════════════════════════════
def _render_pnlcal():
    st.markdown("## \U0001f4c5 P&L Calendar")
    st.caption("Daily profit and loss calendar view.")

    np.random.seed(42)
    today = datetime.now()
    days_back = st.slider("Days to show", 30, 180, 60, key="qt_pc_days")
    start = today - timedelta(days=days_back)
    dates = pd.date_range(start=start, end=today, freq="B")
    daily_pnl = np.random.normal(5000, 15000, len(dates))
    cum_pnl = np.cumsum(daily_pnl)

    total = cum_pnl[-1]
    best = max(daily_pnl)
    worst = min(daily_pnl)
    win = sum(1 for p in daily_pnl if p > 0)
    loss = sum(1 for p in daily_pnl if p < 0)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total P&L", f"\u20b9{total:+,.0f}")
    m2.metric("Best Day", f"\u20b9{best:+,.0f}")
    m3.metric("Worst Day", f"\u20b9{worst:+,.0f}")
    m4.metric("Win Days", f"{win}/{len(dates)}")
    m5.metric("Loss Days", f"{loss}/{len(dates)}")

    fig = go.Figure(go.Bar(x=dates, y=daily_pnl, marker_color=["#22c55e" if p >= 0 else "#ef4444" for p in daily_pnl]))
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Date", yaxis_title="Daily P&L",
                      paper_bgcolor="#151b23", plot_bgcolor="#151b23", font=dict(color="#e6edf3"),
        dragmode="zoom", hovermode="x unified",
                      xaxis=dict(gridcolor="#2a3441"), yaxis=dict(gridcolor="#2a3441"))
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "doubleClick": "reset", "modeBarButtonsToAdd": ["drawline", "eraseshape"],
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })

    fig2 = go.Figure(go.Scatter(x=dates, y=cum_pnl, line=dict(color="#3b82f6", width=2), fill="tozeroy", fillcolor="rgba(59,130,246,0.1)"))
    fig2.add_hline(y=0, line=dict(color="#8b949e", width=1, dash="dash"))
    fig2.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Date", yaxis_title="Cumulative P&L",
                       paper_bgcolor="#151b23", plot_bgcolor="#151b23", font=dict(color="#e6edf3"),
        dragmode="zoom", hovermode="x unified",
                       xaxis=dict(gridcolor="#2a3441"), yaxis=dict(gridcolor="#2a3441"))
    st.plotly_chart(fig2, use_container_width=True, config={
        "scrollZoom": True, "doubleClick": "reset", "modeBarButtonsToAdd": ["drawline", "eraseshape"],
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })


# ═══════════════════════════════════════════════════════════════════════════
# VIEW ROUTER
# ═══════════════════════════════════════════════════════════════════════════
RENDERERS = {
    "screener": _render_screener,
    "chart": _render_chart,
    "overview": _render_overview,
    "backtest": _render_backtest,
    "riskcalc": _render_riskcalc,
    "optionpricer": _render_optionpricer,
    "correlation": _render_correlation,
    "montecarlo": _render_montecarlo,
    "var": _render_var,
    "factor": _render_factor,
    "screenerquant": _render_screener_quant,
    "positions": _render_positions,
    "pnlcal": _render_pnlcal,
}


def render_quant_trade():
    """Main entry point for the Quant Trade tab."""
    # Sub-navigation matching the HTML sidebar groups
    all_items = []
    for group in NAV_GROUPS:
        for item in group["items"]:
            all_items.append(item)

    # If qt_subview was set (e.g. from screener click), sync the selectbox
    if "qt_subview" in st.session_state:
        override_id = st.session_state.pop("qt_subview")
        for item in all_items:
            if item["id"] == override_id:
                st.session_state["qt_subview_select"] = item["label"]
                break

    # Sidebar sub-nav with grouped labels
    sub_nav = st.sidebar.selectbox(
        "\U0001f50d Quant Trade View",
        [item["label"] for item in all_items],
        key="qt_subview_select"
    )

    # Find the matching view id
    selected_id = None
    for item in all_items:
        if item["label"] == sub_nav:
            selected_id = item["id"]
            break

    # Render the selected view
    renderer = RENDERERS.get(selected_id, _render_screener)
    renderer()
