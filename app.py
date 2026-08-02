import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import hashlib

# ──────────────────────────────────────────────
# DATA
# ──────────────────────────────────────────────

STOCKS = [
    {"symbol": "RELIANCE",   "name": "Reliance Industries",      "base_price": 2940,  "sector": "Energy"},
    {"symbol": "TCS",        "name": "Tata Consultancy Services", "base_price": 3870,  "sector": "IT"},
    {"symbol": "HDFCBANK",   "name": "HDFC Bank",                 "base_price": 1685,  "sector": "Banking"},
    {"symbol": "INFY",       "name": "Infosys",                   "base_price": 1810,  "sector": "IT"},
    {"symbol": "ITC",        "name": "ITC Ltd",                    "base_price": 462,   "sector": "FMCG"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors",                "base_price": 985,   "sector": "Auto"},
    {"symbol": "SBIN",       "name": "State Bank of India",        "base_price": 812,   "sector": "Banking"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel",              "base_price": 1590,  "sector": "Telecom"},
]

BROKERS = [
    {"id": "zerodha",  "name": "Zerodha Kite", "note": "Kite Connect API"},
    {"id": "upstox",   "name": "Upstox",      "note": "Upstox API v2"},
    {"id": "angelone", "name": "Angel One",   "note": "SmartAPI"},
    {"id": "fyers",    "name": "Fyers",        "note": "Fyers API v3"},
    {"id": "generic",  "name": "Any broker",   "note": "Custom REST / WebSocket"},
]

# ──────────────────────────────────────────────
# SEEDED RANDOM (mulberry32 equivalent)
# ──────────────────────────────────────────────

def mulberry32(seed):
    """Pure-Python mulberry32 PRNG — matches the JS version."""
    state = seed & 0xFFFFFFFF
    def _rand():
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((state ^ (state >> 15)) * (1 | state)) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) >> 0) / 4294967296
    return _rand

def symbol_seed(symbol):
    s = 0
    for i, ch in enumerate(symbol):
        s += ord(ch) * (i + 7)
    return s

def gen_candles(symbol, base_price, n=90):
    seed = symbol_seed(symbol)
    rand = mulberry32(seed)
    price = base_price * (0.9 + rand() * 0.2)
    drift = (rand() - 0.48) * 0.0018
    candles = []
    today = pd.Timestamp.now().normalize()
    for i in range(n):
        vol = 0.012 + rand() * 0.014
        change = drift + (rand() - 0.5) * vol
        open_ = price
        close = open_ * (1 + change)
        high = max(open_, close) * (1 + rand() * 0.006)
        low = min(open_, close) * (1 - rand() * 0.006)
        volume = round(500_000 + rand() * 4_500_000 * (1 + abs(change) * 20))
        price = close
        d = today - pd.Timedelta(days=n - i - 1)
        candles.append({
            "date": d,
            "open": round(open_, 2),
            "close": round(close, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "volume": volume,
        })
    return pd.DataFrame(candles)

# ──────────────────────────────────────────────
# TECHNICAL INDICATORS
# ──────────────────────────────────────────────

def sma(series, period):
    return series.rolling(period).mean().round(2)

def ema(series, period):
    k = 2 / (period + 1)
    ema_vals = series.ewm(span=period, adjust=False).mean()
    return ema_vals.round(2)

def rsi(series, period=14):
    diff = series.diff()
    gain = diff.clip(lower=0)
    loss = -diff.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / (avg_loss.replace(0, np.nan))
    out = (100 - 100 / (1 + rs))
    out.iloc[:period] = np.nan
    return out.round(2)

def macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = (ema12 - ema26).round(2)
    signal = macd_line.ewm(span=9, adjust=False).mean().round(2)
    hist = (macd_line - signal).round(2)
    return macd_line, signal, hist

def bollinger(series, period=20, mult=2):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = (mid + mult * std).round(2)
    lower = (mid - mult * std).round(2)
    return upper, mid, lower

def detect_patterns(df):
    n = len(df)
    if n < 3:
        return ["Not enough data for pattern detection"]
    last = df.iloc[-1]; prev = df.iloc[-2]; prev2 = df.iloc[-3]
    body = abs(last["close"] - last["open"])
    rng = (last["high"] - last["low"]) or 1
    upper_wick = last["high"] - max(last["open"], last["close"])
    lower_wick = min(last["open"], last["close"]) - last["low"]
    patterns = []
    if body / rng < 0.12:
        patterns.append("🔴 Doji — indecision, possible reversal")
    if lower_wick > body * 2 and upper_wick < body * 0.5 and last["close"] > last["open"]:
        patterns.append("🟢 Hammer — bullish reversal signal")
    if upper_wick > body * 2 and lower_wick < body * 0.5 and last["close"] < last["open"]:
        patterns.append("🔴 Shooting star — bearish reversal signal")
    if prev["close"] < prev["open"] and last["close"] > last["open"] and last["close"] > prev["open"] and last["open"] < prev["close"]:
        patterns.append("🟢 Bullish engulfing — buyers overwhelming sellers")
    if prev["close"] > prev["open"] and last["close"] < last["open"] and last["close"] < prev["open"] and last["open"] > prev["close"]:
        patterns.append("🔴 Bearish engulfing — sellers overwhelming buyers")
    if prev2["close"] < prev2["open"] and abs(prev["close"] - prev["open"]) / ((prev["high"] - prev["low"]) or 1) < 0.3 and last["close"] > last["open"] and last["close"] > (prev2["open"] + prev2["close"]) / 2:
        patterns.append("🟢 Morning star — 3-candle bullish reversal")
    if not patterns:
        patterns.append("➡️ No strong single/multi-candle pattern detected — trend continuation likely")
    return patterns

# ──────────────────────────────────────────────
# CHARTS
# ──────────────────────────────────────────────

def candlestick_chart(df, sma20, sma50, bb_upper, bb_lower, show_ma, show_bb):
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.46, 0.16, 0.18, 0.20],
        subplot_titles=("Price & Indicators", "Volume", "RSI (14)", "MACD (12, 26, 9)"),
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="OHLC",
        increasing_line_color="#1d9e75", decreasing_line_color="#e0524f",
    ), row=1, col=1)

    if show_ma:
        fig.add_trace(go.Scatter(x=df["date"], y=sma20, name="SMA 20", line=dict(color="#378add", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=sma50, name="SMA 50", line=dict(color="#eda100", width=1.5)), row=1, col=1)

    if show_bb:
        fig.add_trace(go.Scatter(x=df["date"], y=bb_upper, name="BB Upper", line=dict(color="#7f77dd", width=1, dash="dot"), opacity=0.8), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=bb_lower, name="BB Lower", line=dict(color="#7f77dd", width=1, dash="dot"), opacity=0.8, showlegend=False), row=1, col=1)

    # Volume
    colors = ["#5dcaa5" if c >= o else "#f0997b" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(x=df["date"], y=df["volume"], name="Volume", marker_color=colors, opacity=0.85), row=2, col=1)

    # RSI
    rsi_vals = rsi(df["close"])
    fig.add_trace(go.Scatter(x=df["date"], y=rsi_vals, name="RSI", line=dict(color="#a89ff0", width=1.6)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#e0524f", opacity=0.6, row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#1d9e75", opacity=0.6, row=3, col=1)

    # MACD
    macd_line, signal_line, hist = macd(df["close"])
    hist_colors = ["#5dcaa5" if h >= 0 else "#f0997b" for h in hist]
    fig.add_trace(go.Bar(x=df["date"], y=hist, name="MACD Hist", marker_color=hist_colors, opacity=0.85), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=macd_line, name="MACD", line=dict(color="#378add", width=1.4)), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=signal_line, name="Signal", line=dict(color="#eda100", width=1.4)), row=4, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=780,
        margin=dict(l=50, r=20, t=40, b=30),
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(size=11),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(50,50,50,0.4)")
    return fig

def trend_chart(df):
    first = df["close"].iloc[0]
    pct = ((df["close"] - first) / first * 100).round(2)
    last_val = pct.iloc[-1]
    color = "#1d9e75" if last_val >= 0 else "#e0524f"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=pct, name="Cumulative %",
        fill="tozeroy", fillcolor=f"rgba({29 if last_val>=0 else 224},{158 if last_val>=0 else 82},{117 if last_val>=0 else 79},0.14)",
        line=dict(color=color, width=2.2),
    ))
    fig.add_trace(go.Scatter(
        x=[df["date"].iloc[-1]], y=[last_val], mode="markers",
        marker=dict(size=8, color=color, line=dict(color="#111", width=2)),
        showlegend=False,
    ))
    fig.update_layout(
        template="plotly_dark", height=240,
        margin=dict(l=50, r=20, t=20, b=30),
        yaxis_title="Cumulative %",
        showlegend=False,
        font=dict(size=11),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(50,50,50,0.4)")
    return fig

# ──────────────────────────────────────────────
# ANALYSIS
# ──────────────────────────────────────────────

def build_analysis(df):
    closes = df["close"]
    last = df.iloc[-1]
    first = df.iloc[0]
    prev = df.iloc[-2]

    change_pct = round(((last["close"] - first["close"]) / first["close"]) * 100, 2)
    day_change_pct = round(((last["close"] - prev["close"]) / prev["close"]) * 100, 2)

    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    rsi_vals = rsi(closes)
    macd_line, signal_line, hist = macd(closes)
    bb_upper, bb_mid, bb_lower = bollinger(closes)

    last_rsi = rsi_vals.iloc[-1]
    last_macd = macd_line.iloc[-1]
    last_signal = signal_line.iloc[-1]
    last_hist = hist.iloc[-1]
    last_sma20 = sma20.iloc[-1]
    last_sma50 = sma50.iloc[-1]
    last_bb_upper = bb_upper.iloc[-1]
    last_bb_lower = bb_lower.iloc[-1]

    avg_vol = df["volume"].iloc[-20:].mean()
    vol_ratio = round(last["volume"] / avg_vol, 2) if avg_vol else 0

    # Volatility
    returns = closes.pct_change().dropna()
    daily_vol = returns.std()
    annualized_vol = round(daily_vol * np.sqrt(252) * 100, 2) if daily_vol else 0
    mean_return = returns.mean()
    sharpe = round((mean_return * 252) / (daily_vol * np.sqrt(252)) if daily_vol else 0, 2)

    # Signals
    bull, bear = 0, 0
    if last_rsi is not None and not np.isnan(last_rsi):
        if last_rsi < 30: bull += 1
        elif last_rsi > 70: bear += 1
    if last_macd is not None and last_signal is not None:
        if not np.isnan(last_macd) and not np.isnan(last_signal):
            if last_macd > last_signal: bull += 1
            else: bear += 1
    if last_sma20 is not None and last_sma50 is not None:
        if not np.isnan(last_sma20) and not np.isnan(last_sma50):
            if last_sma20 > last_sma50: bull += 1
            else: bear += 1
    if last_bb_lower is not None and not np.isnan(last_bb_lower):
        if last["close"] < last_bb_lower: bull += 1
        elif last_bb_upper is not None and not np.isnan(last_bb_upper) and last["close"] > last_bb_upper: bear += 1
    if last["close"] > first["close"]: bull += 1
    else: bear += 1

    if bull - bear >= 2:
        verdict = "Bullish bias 🟢"
    elif bear - bull >= 2:
        verdict = "Bearish bias 🔴"
    else:
        verdict = "Neutral / range-bound ⚪"

    patterns = detect_patterns(df)

    support = round(df["low"].iloc[-20:].min(), 2)
    resistance = round(df["high"].iloc[-20:].max(), 2)

    return {
        "change_pct": change_pct,
        "day_change_pct": day_change_pct,
        "last_rsi": last_rsi,
        "last_macd": last_macd,
        "last_signal": last_signal,
        "last_hist": last_hist,
        "last_sma20": last_sma20,
        "last_sma50": last_sma50,
        "bb_upper": last_bb_upper,
        "bb_lower": last_bb_lower,
        "avg_vol": avg_vol,
        "vol_ratio": vol_ratio,
        "annualized_vol": annualized_vol,
        "sharpe": sharpe,
        "verdict": verdict,
        "bull_signals": bull,
        "bear_signals": bear,
        "patterns": patterns,
        "support": support,
        "resistance": resistance,
        "sma20": sma20,
        "sma50": sma50,
        "rsi_vals": rsi_vals,
        "macd_line": macd_line,
        "signal_line": signal_line,
        "hist": hist,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bb_mid": bb_mid,
    }

def fmt_vol(n):
    if n >= 1e7: return f"{n/1e7:.2f}Cr"
    if n >= 1e5: return f"{n/1e5:.2f}L"
    if n >= 1e3: return f"{n/1e3:.1f}K"
    return str(int(n))

def fmt_num(n):
    if n is None or (isinstance(n, float) and np.isnan(n)): return "—"
    return f"{n:,.0f}"

# ──────────────────────────────────────────────
# STREAMLIT UI
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="Stock Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main > div { padding-top: 1rem; }
    .stMetric { background: rgba(255,255,255,0.03); border-radius: 8px; padding: 10px 14px; border: 1px solid rgba(255,255,255,0.06); }
    .verdict-box { padding: 12px 18px; border-radius: 10px; font-size: 1.1rem; font-weight: 600; text-align: center; margin: 8px 0; }
    .pattern-item { padding: 6px 0; font-size: 0.95rem; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
st.sidebar.title("⚙️ Settings")

stock_options = [f"{s['symbol']} — {s['name']}" for s in STOCKS]
selected_stock_label = st.sidebar.selectbox("Select Stock", stock_options, index=0)
selected_idx = stock_options.index(selected_stock_label)
stock = STOCKS[selected_idx]

broker_options = [f"{b['name']} ({b['note']})" for b in BROKERS]
selected_broker_label = st.sidebar.selectbox("Broker Connection", broker_options, index=0)

candle_count = st.sidebar.slider("Number of candles", min_value=30, max_value=180, value=90, step=10)

show_ma = st.sidebar.checkbox("Show Moving Averages (SMA 20 / 50)", value=True)
show_bb = st.sidebar.checkbox("Show Bollinger Bands", value=True)

st.sidebar.markdown("---")
st.sidebar.caption("📊 Simulated data for educational use only. Not financial advice.")

# ── Generate data ──
df = gen_candles(stock["symbol"], stock["base_price"], candle_count)
analysis = build_analysis(df)

# ── Header ──
st.title("📊 Stock Analysis Dashboard")
st.markdown(f"### {stock['symbol']} — {stock['name']}  ·  {stock['sector']} sector")

# ── Top metrics row ──
col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

last_price = df["close"].iloc[-1]
day_color = "🟢" if analysis["day_change_pct"] >= 0 else "🔴"

with col_m1:
    st.metric("Last Price", f"₹{last_price:,.2f}", f"{analysis['day_change_pct']:+.2f}% today")
with col_m2:
    st.metric("Period Change", f"{analysis['change_pct']:+.2f}%", f"over {candle_count} candles")
with col_m3:
    st.metric("RSI (14)", f"{analysis['last_rsi']:.1f}" if analysis['last_rsi'] is not None and not np.isnan(analysis['last_rsi']) else "—")
with col_m4:
    st.metric("Volume", fmt_vol(df["volume"].iloc[-1]), f"{analysis['vol_ratio']:.2f}× avg")
with col_m5:
    st.metric("Volatility (ann.)", f"{analysis['annualized_vol']}%")

# ── Verdict banner ──
verdict_color = "#1a4d2e" if "Bullish" in analysis["verdict"] else "#4d1a1a" if "Bearish" in analysis["verdict"] else "#333"
st.markdown(f"""
<div class="verdict-box" style="background:{verdict_color};color:#fff;">
    {analysis['verdict']} &nbsp;|&nbsp; Bullish signals: {analysis['bull_signals']} &nbsp;·&nbsp; Bearish signals: {analysis['bear_signals']}
</div>
""", unsafe_allow_html=True)

# ── Main chart ──
st.plotly_chart(
    candlestick_chart(
        df, analysis["sma20"], analysis["sma50"],
        analysis["bb_upper"], analysis["bb_lower"],
        show_ma, show_bb,
    ),
    use_container_width=True,
)

# ── Trend chart ──
st.markdown("### 📈 Cumulative Return Trend")
st.plotly_chart(trend_chart(df), use_container_width=True)

# ── Two-column: Indicators detail + Patterns ──
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 📋 Technical Indicators")
    ind_data = {
        "Indicator": ["SMA 20", "SMA 50", "RSI (14)", "MACD Line", "MACD Signal", "MACD Histogram",
                      "BB Upper", "BB Lower", "Support (20d low)", "Resistance (20d high)",
                      "Avg Volume (20d)", "Volume Ratio", "Annualized Volatility", "Sharpe-like Ratio"],
        "Value": [
            fmt_num(analysis["last_sma20"]),
            fmt_num(analysis["last_sma50"]),
            f"{analysis['last_rsi']:.2f}" if analysis['last_rsi'] is not None and not np.isnan(analysis['last_rsi']) else "—",
            fmt_num(analysis["last_macd"]),
            fmt_num(analysis["last_signal"]),
            fmt_num(analysis["last_hist"]),
            fmt_num(analysis["bb_upper"]),
            fmt_num(analysis["bb_lower"]),
            f"₹{analysis['support']}",
            f"₹{analysis['resistance']}",
            fmt_vol(analysis["avg_vol"]),
            f"{analysis['vol_ratio']}×",
            f"{analysis['annualized_vol']}%",
            f"{analysis['sharpe']}",
        ],
    }
    st.dataframe(pd.DataFrame(ind_data), use_container_width=True, hide_index=True)

with col_right:
    st.markdown("### 🔍 Candlestick Patterns")
    for p in analysis["patterns"]:
        st.markdown(f"<div class='pattern-item'>{p}</div>", unsafe_allow_html=True)

    st.markdown("### 📊 Signal Summary")
    sig_df = pd.DataFrame({
        "Type": ["🟢 Bullish", "🔴 Bearish", "⚖️ Net"],
        "Count": [analysis["bull_signals"], analysis["bear_signals"], analysis["bull_signals"] - analysis["bear_signals"]],
    })
    st.dataframe(sig_df, use_container_width=True, hide_index=True)

# ── Raw data table ──
st.markdown("### 📑 Recent Candle Data")
display_df = df[["date", "open", "high", "low", "close", "volume"]].copy()
display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
display_df.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
display_df["Volume"] = display_df["Volume"].apply(fmt_vol)
st.dataframe(display_df.tail(20), use_container_width=True, hide_index=True)

# ── Footer ──
st.markdown("---")
st.caption("📊 Stock Analysis Dashboard — Built with Streamlit + Plotly | Simulated data for educational purposes only | Not financial advice")
