import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import time

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="Quant Desk — Stock Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# DATA
# ──────────────────────────────────────────────

SYMBOLS = [
    {"symbol": "RELIANCE",   "exchange": "NSE", "name": "Reliance Industries",      "base_price": 2940,  "sector": "Energy"},
    {"symbol": "TCS",        "exchange": "NSE", "name": "Tata Consultancy Services", "base_price": 3870,  "sector": "IT"},
    {"symbol": "HDFCBANK",   "exchange": "NSE", "name": "HDFC Bank",                 "base_price": 1685,  "sector": "Banking"},
    {"symbol": "INFY",       "exchange": "NSE", "name": "Infosys",                   "base_price": 1810,  "sector": "IT"},
    {"symbol": "ITC",        "exchange": "NSE", "name": "ITC Ltd",                    "base_price": 462,   "sector": "FMCG"},
    {"symbol": "TATAMOTORS", "exchange": "NSE", "name": "Tata Motors",                "base_price": 985,   "sector": "Auto"},
    {"symbol": "SBIN",       "exchange": "NSE", "name": "State Bank of India",        "base_price": 812,   "sector": "Banking"},
    {"symbol": "BHARTIARTL", "exchange": "NSE", "name": "Bharti Airtel",              "base_price": 1590,  "sector": "Telecom"},
    {"symbol": "NIFTY",      "exchange": "NSE", "name": "Nifty 50 Index",             "base_price": 22000, "sector": "Index"},
    {"symbol": "BANKNIFTY",  "exchange": "NSE", "name": "Bank Nifty Index",           "base_price": 48000, "sector": "Index"},
]

BROKERS = [
    {"id": "zerodha",  "name": "Zerodha Kite", "note": "Kite Connect API",       "fields": ["API Key", "API Secret"]},
    {"id": "upstox",   "name": "Upstox",      "note": "Upstox API v2",          "fields": ["API Key", "API Secret", "Redirect URI"]},
    {"id": "angelone", "name": "Angel One",   "note": "SmartAPI",               "fields": ["API Key", "Client ID", "PIN"]},
    {"id": "fyers",    "name": "Fyers",        "note": "Fyers API v3",          "fields": ["App ID", "Secret Key"]},
    {"id": "generic",  "name": "Any broker",   "note": "Custom REST / WebSocket", "fields": ["Base URL", "API Key"]},
]

# ──────────────────────────────────────────────
# SEEDED RANDOM (matches JS mulberry32)
# ──────────────────────────────────────────────

def mulberry32(seed):
    """Pure-Python mulberry32 PRNG — matches the JS version bit-for-bit."""
    state = seed & 0xFFFFFFFF
    def _rand():
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        # imul(a, b) = (a * b) & 0xFFFFFFFF in JS when both are 32-bit
        t = ((state ^ ((state >> 15) & 0xFFFF)) * (1 | state)) & 0xFFFFFFFF
        t = (t + (((t ^ ((t >> 7) & 0xFFFFFF)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        t = t ^ ((t >> 14) & 0x3FFFF)
        return t / 4294967296
    return _rand

def symbol_seed(symbol):
    s = 0
    for i, ch in enumerate(symbol):
        s += ord(ch) * (i + 7)
    return s & 0xFFFFFFFF

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
    return series.ewm(span=period, adjust=False).mean().round(2)

def rsi(series, period=14):
    diff = series.diff()
    gain = diff.clip(lower=0)
    loss = -diff.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
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
# ANALYSIS
# ──────────────────────────────────────────────

def build_analysis(df):
    closes = df["close"]
    last = df.iloc[-1]
    first = df.iloc[0]
    prev = df.iloc[-2]

    change_pct = round(((last["close"] - first["close"]) / first["close"]) * 100, 2)
    day_change_pct = round(((last["close"] - prev["close"]) / prev["close"]) * 100, 2)

    sma20_vals = sma(closes, 20)
    sma50_vals = sma(closes, 50)
    rsi_vals = rsi(closes)
    macd_line, signal_line, hist = macd(closes)
    bb_upper, bb_mid, bb_lower = bollinger(closes)

    def last_val(s):
        v = s.iloc[-1]
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        return v

    last_rsi = last_val(rsi_vals)
    last_macd = last_val(macd_line)
    last_signal = last_val(signal_line)
    last_hist = last_val(hist)
    last_sma20 = last_val(sma20_vals)
    last_sma50 = last_val(sma50_vals)
    last_bb_upper = last_val(bb_upper)
    last_bb_lower = last_val(bb_lower)

    avg_vol = df["volume"].iloc[-20:].mean()
    vol_ratio = round(last["volume"] / avg_vol, 2) if avg_vol else 0

    returns = closes.pct_change().dropna()
    daily_vol = returns.std()
    annualized_vol = round(daily_vol * np.sqrt(252) * 100, 2) if daily_vol else 0
    mean_return = returns.mean()
    sharpe = round((mean_return * 252) / (daily_vol * np.sqrt(252)) if daily_vol else 0, 2)

    bull, bear = 0, 0
    if last_rsi is not None:
        if last_rsi < 30: bull += 1
        elif last_rsi > 70: bear += 1
    if last_macd is not None and last_signal is not None:
        if last_macd > last_signal: bull += 1
        else: bear += 1
    if last_sma20 is not None and last_sma50 is not None:
        if last_sma20 > last_sma50: bull += 1
        else: bear += 1
    if last_bb_lower is not None:
        if last["close"] < last_bb_lower: bull += 1
        elif last_bb_upper is not None and last["close"] > last_bb_upper: bear += 1
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
        "change_pct": change_pct, "day_change_pct": day_change_pct,
        "last_rsi": last_rsi, "last_macd": last_macd, "last_signal": last_signal,
        "last_hist": last_hist, "last_sma20": last_sma20, "last_sma50": last_sma50,
        "bb_upper": last_bb_upper, "bb_lower": last_bb_lower,
        "avg_vol": avg_vol, "vol_ratio": vol_ratio,
        "annualized_vol": annualized_vol, "sharpe": sharpe,
        "verdict": verdict, "bull_signals": bull, "bear_signals": bear,
        "patterns": patterns, "support": support, "resistance": resistance,
        "sma20": sma20_vals, "sma50": sma50_vals,
        "rsi_vals": rsi_vals, "macd_line": macd_line, "signal_line": signal_line,
        "hist": hist, "bb_upper": bb_upper, "bb_lower": bb_lower, "bb_mid": bb_mid,
    }

def fmt_vol(n):
    if n is None: return "—"
    if n >= 1e7: return f"{n/1e7:.2f}Cr"
    if n >= 1e5: return f"{n/1e5:.2f}L"
    if n >= 1e3: return f"{n/1e3:.1f}K"
    return str(int(n))

def fmt_num(n):
    if n is None: return "—"
    if isinstance(n, float) and np.isnan(n): return "—"
    return f"{n:,.0f}"

# ──────────────────────────────────────────────
# TRADINGVIEW EMBED
# ──────────────────────────────────────────────

def render_tradingview(symbol, theme="dark", height=580):
    """Embed TradingView advanced chart widget."""
    tv_symbol = f"NSE:{symbol}"
    html = f"""
    <div class="tradingview-widget-container" style="height:{height}px;width:100%;">
      <div class="tradingview-widget-container__widget" style="height:calc({height}px - 0px);width:100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
      {{
        "autosize": true,
        "symbol": "{tv_symbol}",
        "interval": "D",
        "timezone": "Asia/Kolkata",
        "theme": "{theme}",
        "style": "1",
        "locale": "in",
        "enable_publishing": false,
        "withdateranges": true,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "studies": [
          "STD;SMA",
          "STD;RSI",
          "STD;MACD",
          "STD;Bollinger_Bands"
        ],
        "support_host": "https://www.tradingview.com"
      }}
      </script>
    </div>
    """
    components.html(html, height=height)

def render_tradingview_ticker(symbol, theme="dark"):
    """Embed TradingView ticker tape widget."""
    html = f"""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
      {{
        "symbols": [
          {{"proName": "NSE:{symbol}", "title": "{symbol}"}},
          {{"proName": "NSE:RELIANCE", "title": "RELIANCE"}},
          {{"proName": "NSE:TCS", "title": "TCS"}},
          {{"proName": "NSE:HDFCBANK", "title": "HDFCBANK"}},
          {{"proName": "NSE:NIFTY", "title": "NIFTY 50"}},
          {{"proName": "NSE:BANKNIFTY", "title": "BANK NIFTY"}}
        ],
        "showSymbolLogo": true,
        "isTransparent": true,
        "displayMode": "adaptive",
        "colorTheme": "{theme}",
        "locale": "in"
      }}
      </script>
    </div>
    """
    components.html(html, height=70)

# ──────────────────────────────────────────────
# VOICE NARRATION (gTTS)
# ──────────────────────────────────────────────

def build_narration(symbol_meta, broker_name=None):
    s = symbol_meta["name"]
    parts = [
        f"Here's the read on {s}.",
        "The chart is showing live TradingView data with SMA, RSI, MACD, and Bollinger Bands overlaid.",
        "Use RSI to judge overbought or oversold conditions — above 70 typically signals overbought, below 30 oversold.",
        "MACD crossing above its signal line is generally read as bullish momentum, and crossing below as bearish.",
        "Bollinger Bands widen with volatility — price pressing the upper band can mean strength or exhaustion depending on volume.",
    ]
    if broker_name:
        parts.append(f"Your {broker_name} connection is in demo mode right now, so no live order data is being pulled.")
    else:
        parts.append("No broker is connected yet, so this is chart analysis only, not account data.")
    parts.append("Remember, none of this is financial advice — it's a read of the indicators, not a recommendation.")
    return " ".join(parts)

def generate_audio(text):
    """Generate audio from text using gTTS, return bytes."""
    try:
        from gtts import gTTS
        audio_fp = io.BytesIO()
        tts = gTTS(text=text, lang="en", slow=False)
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        return audio_fp
    except Exception:
        return None

# ──────────────────────────────────────────────
# PLOTLY CHARTS (for analysis tab)
# ──────────────────────────────────────────────

def candlestick_chart(df, analysis, show_ma, show_bb, theme="dark"):
    template = "plotly_dark" if theme == "dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)" if theme == "dark" else "rgba(255,255,255,0)"
    grid_color = "rgba(50,50,50,0.3)" if theme == "dark" else "rgba(200,200,200,0.5)"

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.46, 0.16, 0.18, 0.20],
        subplot_titles=("Price & Indicators", "Volume", "RSI (14)", "MACD (12, 26, 9)"),
    )

    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="OHLC",
        increasing_line_color="#1d9e75", decreasing_line_color="#e0524f",
    ), row=1, col=1)

    if show_ma:
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["sma20"], name="SMA 20",
                                 line=dict(color="#378add", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["sma50"], name="SMA 50",
                                 line=dict(color="#eda100", width=1.5)), row=1, col=1)

    if show_bb:
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["bb_upper"], name="BB Upper",
                                 line=dict(color="#7f77dd", width=1, dash="dot"), opacity=0.8), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["bb_lower"], name="BB Lower",
                                 line=dict(color="#7f77dd", width=1, dash="dot"), opacity=0.8, showlegend=False), row=1, col=1)

    colors = ["#5dcaa5" if c >= o else "#f0997b" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(x=df["date"], y=df["volume"], name="Volume",
                         marker_color=colors, opacity=0.85), row=2, col=1)

    fig.add_trace(go.Scatter(x=df["date"], y=analysis["rsi_vals"], name="RSI",
                             line=dict(color="#a89ff0", width=1.6)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#e0524f", opacity=0.6, row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#1d9e75", opacity=0.6, row=3, col=1)

    hist_colors = ["#5dcaa5" if h >= 0 else "#f0997b" for h in analysis["hist"]]
    fig.add_trace(go.Bar(x=df["date"], y=analysis["hist"], name="MACD Hist",
                         marker_color=hist_colors, opacity=0.85), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=analysis["macd_line"], name="MACD",
                             line=dict(color="#378add", width=1.4)), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=analysis["signal_line"], name="Signal",
                             line=dict(color="#eda100", width=1.4)), row=4, col=1)

    fig.update_layout(
        template=template,
        height=780,
        margin=dict(l=50, r=20, t=40, b=30),
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(size=11),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=grid_color)
    return fig

def trend_chart(df, theme="dark"):
    template = "plotly_dark" if theme == "dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)" if theme == "dark" else "rgba(255,255,255,0)"

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
    fig.update_layout(template=template, height=240,
                      margin=dict(l=50, r=20, t=20, b=30),
                      yaxis_title="Cumulative %", showlegend=False,
                      font=dict(size=11), paper_bgcolor=bg_color, plot_bgcolor=bg_color)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(50,50,50,0.3)" if theme == "dark" else "rgba(200,200,200,0.5)")
    return fig

# ──────────────────────────────────────────────
# SESSION STATE INIT
# ──────────────────────────────────────────────

if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "connection" not in st.session_state:
    st.session_state.connection = None
if "credentials" not in st.session_state:
    st.session_state.credentials = {}
if "voice_generated" not in st.session_state:
    st.session_state.voice_generated = None

# ──────────────────────────────────────────────
# SIDEBAR — Settings & Broker
# ──────────────────────────────────────────────

st.sidebar.markdown("## ⚙️ Settings")

# Theme toggle
theme_col1, theme_col2 = st.sidebar.columns([1, 1])
if theme_col1.button("🌙 Dark", use_container_width=True,
                     type="primary" if st.session_state.theme == "dark" else "secondary"):
    st.session_state.theme = "dark"
    st.rerun()
if theme_col2.button("☀️ Light", use_container_width=True,
                     type="primary" if st.session_state.theme == "light" else "secondary"):
    st.session_state.theme = "light"
    st.rerun()

st.sidebar.markdown("---")

# Symbol selector with search
st.sidebar.markdown("### Select Symbol")
search_query = st.sidebar.text_input("🔍 Search", placeholder="Type symbol or name...", key="symbol_search")

filtered_symbols = [s for s in SYMBOLS if
    search_query.lower() in s["symbol"].lower() or
    search_query.lower() in s["name"].lower()]

if filtered_symbols:
    symbol_labels = [f"{s['symbol']} — {s['name']}" for s in filtered_symbols]
    selected_label = st.sidebar.selectbox("Stock/Index", symbol_labels, key="symbol_select")
    selected_idx = symbol_labels.index(selected_label)
    stock = filtered_symbols[selected_idx]
else:
    stock = SYMBOLS[0]
    st.sidebar.warning("No matches found")

# Candle count
candle_count = st.sidebar.slider("Candles (simulated)", 30, 180, 90, step=10)

# Indicator toggles
st.sidebar.markdown("---")
show_ma = st.sidebar.checkbox("Moving Averages (SMA 20/50)", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands", value=True)

st.sidebar.markdown("---")

# ── Broker Connection Panel ──
st.sidebar.markdown("### 🔗 Broker Connection")

if st.session_state.connection:
    conn = st.session_state.connection
    broker_meta = next((b for b in BROKERS if b["id"] == conn["broker_id"]), None)
    mode_label = "🟢 Live" if conn.get("mode") == "live" else "🟡 Demo"
    st.sidebar.markdown(f"""
    <div style='padding:10px 14px; border-radius:8px; background:{"#1a3d1a" if st.session_state.theme=="dark" else "#d4edda"}; 
    border:1px solid {"#2a5a2a" if st.session_state.theme=="dark" else "#c3e6cb"};'>
        <div style='font-weight:700;font-size:13px;'>{conn["name"]} {mode_label}</div>
        <div style='font-size:11px;opacity:0.7;margin-top:2px;'>Connected {conn["connected_at"]}</div>
    </div>
    """, unsafe_allow_html=True)
    if st.sidebar.button("🔌 Disconnect", use_container_width=True):
        st.session_state.connection = None
        st.session_state.credentials = {}
        st.rerun()
else:
    selected_broker_id = st.sidebar.selectbox(
        "Select Broker",
        options=[b["id"] for b in BROKERS],
        format_func=lambda x: next(b["name"] for b in BROKERS if b["id"] == x),
        key="broker_select"
    )
    broker_meta = next(b for b in BROKERS if b["id"] == selected_broker_id)
    st.sidebar.caption(f"📋 {broker_meta['note']}")

    # Credential fields
    credentials = {}
    for field in broker_meta["fields"]:
        is_secret = "secret" in field.lower() or "pin" in field.lower() or "key" in field.lower()
        credentials[field] = st.sidebar.text_input(
            field, type="password" if is_secret else "default",
            key=f"cred_{selected_broker_id}_{field}"
        )

    if st.sidebar.button("🔗 Connect", use_container_width=True, type="primary"):
        # In real deployment: POST to backend server.
        # Here: demo mode since no backend configured.
        st.session_state.connection = {
            "broker_id": selected_broker_id,
            "name": broker_meta["name"],
            "connected_at": time.strftime("%H:%M:%S"),
            "mode": "demo",
        }
        st.session_state.credentials = credentials
        st.sidebar.success(f"✅ Connected to {broker_meta['name']} (Demo)")
        st.rerun()

    st.sidebar.info(
        "⚠️ Demo mode — no real broker connection. "
        "Point `BACKEND_BASE_URL` at your server to go live."
    )

st.sidebar.markdown("---")
st.sidebar.caption("📊 Quant Desk — Educational use only. Not financial advice.")

# ──────────────────────────────────────────────
# MAIN CONTENT
# ──────────────────────────────────────────────

theme = st.session_state.theme

# ── Header ──
col_title, col_badge = st.columns([3, 1])
with col_title:
    st.markdown(f"## 📊 Quant Desk — {stock['symbol']} ({stock['exchange']})")
    st.caption(f"{stock['name']} · {stock['sector']} sector")
with col_badge:
    if st.session_state.connection:
        st.markdown(f"🟡 {st.session_state.connection['name']} · Demo")
    else:
        st.markdown("⚪ No broker connected")

# ── Ticker tape ──
render_tradingview_ticker(stock["symbol"], theme)

st.markdown("")

# ── Tabs ──
tab_live, tab_analysis, tab_voice, tab_data = st.tabs([
    "📈 Live Chart", "📊 Technical Analysis", "🔊 Voice Brief", "📋 Raw Data"
])

# ── TAB 1: Live TradingView Chart ──
with tab_live:
    st.markdown(f"### Live TradingView Chart — {stock['symbol']}")
    st.caption("Real-time NSE data via TradingView. Toggle indicators (SMA, RSI, MACD, Bollinger Bands) from the chart's own menu.")
    render_tradingview(stock["symbol"], theme, height=600)

# ── TAB 2: Technical Analysis (simulated data) ──
with tab_analysis:
    df = gen_candles(stock["symbol"], stock["base_price"], candle_count)
    analysis = build_analysis(df)

    # Top metrics
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    last_price = df["close"].iloc[-1]

    with col_m1:
        st.metric("Last Price (sim)", f"₹{last_price:,.2f}", f"{analysis['day_change_pct']:+.2f}% today")
    with col_m2:
        st.metric("Period Change", f"{analysis['change_pct']:+.2f}%", f"over {candle_count} candles")
    with col_m3:
        rsi_val = analysis["last_rsi"]
        st.metric("RSI (14)", f"{rsi_val:.1f}" if rsi_val is not None else "—")
    with col_m4:
        st.metric("Volume", fmt_vol(df["volume"].iloc[-1]), f"{analysis['vol_ratio']:.2f}× avg")
    with col_m5:
        st.metric("Volatility (ann.)", f"{analysis['annualized_vol']}%")

    # Verdict banner
    verdict_bg = "#1a4d2e" if "Bullish" in analysis["verdict"] else "#4d1a1a" if "Bearish" in analysis["verdict"] else "#333"
    st.markdown(f"""
    <div style='padding:12px 18px;border-radius:10px;background:{verdict_bg};color:#fff;text-align:center;font-size:1.1rem;font-weight:600;margin:8px 0;'>
        {analysis['verdict']} &nbsp;|&nbsp; Bullish: {analysis['bull_signals']} &nbsp;·&nbsp; Bearish: {analysis['bear_signals']}
    </div>
    """, unsafe_allow_html=True)

    # Main candlestick chart
    st.plotly_chart(
        candlestick_chart(df, analysis, show_ma, show_bb, theme),
        use_container_width=True,
    )

    # Trend chart
    st.markdown("#### 📈 Cumulative Return Trend")
    st.plotly_chart(trend_chart(df, theme), use_container_width=True)

    # Two-column: Indicators + Patterns
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### 📋 Technical Indicators")
        ind_data = {
            "Indicator": ["SMA 20", "SMA 50", "RSI (14)", "MACD Line", "MACD Signal",
                          "MACD Histogram", "BB Upper", "BB Lower",
                          "Support (20d low)", "Resistance (20d high)",
                          "Avg Volume (20d)", "Volume Ratio",
                          "Annualized Volatility", "Sharpe-like Ratio"],
            "Value": [
                fmt_num(analysis["last_sma20"]), fmt_num(analysis["last_sma50"]),
                f"{analysis['last_rsi']:.2f}" if analysis["last_rsi"] is not None else "—",
                fmt_num(analysis["last_macd"]), fmt_num(analysis["last_signal"]),
                fmt_num(analysis["last_hist"]),
                fmt_num(analysis["bb_upper"]), fmt_num(analysis["bb_lower"]),
                f"₹{analysis['support']}", f"₹{analysis['resistance']}",
                fmt_vol(analysis["avg_vol"]), f"{analysis['vol_ratio']}×",
                f"{analysis['annualized_vol']}%", f"{analysis['sharpe']}",
            ],
        }
        st.dataframe(pd.DataFrame(ind_data), use_container_width=True, hide_index=True)

    with col_right:
        st.markdown("#### 🔍 Candlestick Patterns")
        for p in analysis["patterns"]:
            st.markdown(f"- {p}")

        st.markdown("#### 📊 Signal Summary")
        sig_df = pd.DataFrame({
            "Type": ["🟢 Bullish", "🔴 Bearish", "⚖️ Net"],
            "Count": [analysis["bull_signals"], analysis["bear_signals"],
                      analysis["bull_signals"] - analysis["bear_signals"]],
        })
        st.dataframe(sig_df, use_container_width=True, hide_index=True)

# ── TAB 3: Voice Brief ──
with tab_voice:
    st.markdown("### 🔊 AI Voice Brief")
    st.caption("Hear an AI-generated narration of the current chart setup.")

    connected_broker_name = st.session_state.connection["name"] if st.session_state.connection else None
    narration_text = build_narration(stock, connected_broker_name)

    st.info("🎙️ Click below to generate and play the voice brief.")

    st.markdown("**Narration preview:**")
    st.markdown(f"> {narration_text}")

    if st.button("🔊 Generate Voice Brief", type="primary"):
        with st.spinner("Generating audio..."):
            audio_bytes = generate_audio(narration_text)
            if audio_bytes:
                st.success("✅ Audio generated!")
                st.audio(audio_bytes, format="audio/mp3")
            else:
                st.error("❌ Failed to generate audio. gTTS might not be available.")

    st.markdown("---")
    st.markdown("#### 📝 What the brief covers:")
    st.markdown("""
    - **Chart overview** — live TradingView data with key indicators
    - **RSI interpretation** — overbought (>70) vs oversold (<30) zones
    - **MACD signals** — bullish vs bearish momentum crossovers
    - **Bollinger Bands** — volatility and price exhaustion signals
    - **Broker status** — whether live or demo mode is active
    - **Disclaimer** — educational content, not financial advice
    """)

# ── TAB 4: Raw Data ──
with tab_data:
    df = gen_candles(stock["symbol"], stock["base_price"], candle_count)
    display_df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
    display_df.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
    display_df["Volume"] = display_df["Volume"].apply(fmt_vol)
    st.markdown(f"#### Recent Candle Data — {stock['symbol']}")
    st.dataframe(display_df.tail(30), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### ⚙️ Broker Configuration Reference")
    broker_ref = pd.DataFrame([
        {"Broker": b["name"], "API": b["note"], "Required Fields": ", ".join(b["fields"])}
        for b in BROKERS
    ])
    st.dataframe(broker_ref, use_container_width=True, hide_index=True)

# ── Footer ──
st.markdown("---")
footer_col1, footer_col2 = st.columns([3, 1])
with footer_col1:
    st.caption("📊 Quant Desk — Built with Streamlit + Plotly + TradingView + gTTS | Simulated data for educational purposes only | Not financial advice")
with footer_col2:
    st.caption("Powered by [TradingView](https://www.tradingview.com)")
