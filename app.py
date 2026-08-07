import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
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
    menu_items={
        "About": "📊 Quant Desk — Stock Analysis Dashboard\nBuilt with Streamlit + Plotly + yfinance\nFor educational purposes only — not financial advice.",
    },
)
# Hide GitHub deploy button only (3-dots menu stays visible)
st.markdown("""
<style>
.stDeployButton {display: none !important;}
/* Fix Plotly chart zoom - prevent double-tap, enable smooth scroll/pinch */
.js-plotly-plot .plot-container,
.js-plotly-plot .svg-container {
    touch-action: none !important;
}
.modebar-btn[data-val="zoomIn2d"], .modebar-btn[data-val="zoomOut2d"] {
    display: none !important;
}
/* Better Plotly modebar styling */
.modebar {background: transparent !important;}
.modebar-btn.active {background-color: rgba(59,130,246,0.2) !important;}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
# PASSWORD PROTECTION
# ──────────────────────────────────────────────
def check_password():
    """Returns True if the correct password is entered."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if st.session_state["authenticated"]:
        return True
    st.markdown("""
    <div style="display:flex;justify-content:center;align-items:center;min-height:60vh;">
      <div style="background:#151b23;border:1px solid #2a3441;border-radius:16px;padding:36px 40px;text-align:center;max-width:380px;">
        <h2 style="color:#e6edf3;margin:0 0 8px;">\U0001f512 Quant Desk</h2>
        <p style="color:#8b949e;font-size:13px;margin:0 0 20px;">Enter password to access the dashboard</p>
      </div>
    </div>
    """, unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password", placeholder="Enter password...", label_visibility="collapsed")
    if st.button("Unlock \u2192", type="primary", use_container_width=True):
        if pwd == "dinesh@123":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("\u274c Incorrect password. Try again.")
    st.stop()
    return False

if not check_password():
    st.stop()
# ASSETS WATCHLIST
# ──────────────────────────────────────────────

ASSETS = [
    # India - NSE
    {"ticker": "RELIANCE.NS",   "tv": "NSE:RELIANCE",    "name": "Reliance Industries",      "type": "NSE",  "logo": "RELIANCE"},
    {"ticker": "TCS.NS",        "tv": "NSE:TCS",          "name": "Tata Consultancy Services","type": "NSE",  "logo": "TCS"},
    {"ticker": "INFY.NS",       "tv": "NSE:INFY",         "name": "Infosys",                  "type": "NSE",  "logo": "INFY"},
    {"ticker": "HDFCBANK.NS",   "tv": "NSE:HDFCBANK",     "name": "HDFC Bank",               "type": "NSE",  "logo": "HDFCBANK"},
    {"ticker": "ICICIBANK.NS",  "tv": "NSE:ICICIBANK",    "name": "ICICI Bank",               "type": "NSE",  "logo": "ICICIBANK"},
    {"ticker": "SBIN.NS",       "tv": "NSE:SBIN",         "name": "State Bank of India",     "type": "NSE",  "logo": "SBIN"},
    {"ticker": "TATAMOTORS.NS", "tv": "NSE:TATAMOTORS",  "name": "Tata Motors",             "type": "NSE",  "logo": "TATAMOTORS"},
    {"ticker": "ADANIENT.NS",   "tv": "NSE:ADANIENT",    "name": "Adani Enterprises",       "type": "NSE",  "logo": "ADANIENT"},
    {"ticker": "BAJFINANCE.NS", "tv": "NSE:BAJFINANCE",   "name": "Bajaj Finance",           "type": "NSE",  "logo": "BAJFINANCE"},
    {"ticker": "WIPRO.NS",      "tv": "NSE:WIPRO",        "name": "Wipro",                   "type": "NSE",  "logo": "WIPRO"},
    {"ticker": "LT.NS",         "tv": "NSE:LT",           "name": "Larsen & Toubro",         "type": "NSE",  "logo": "LT"},
    {"ticker": "HINDUNILVR.NS", "tv": "NSE:HINDUNILVR",  "name": "Hindustan Unilever",      "type": "NSE",  "logo": "HINDUNILVR"},
    {"ticker": "BHARTIARTL.NS", "tv": "NSE:BHARTIARTL",  "name": "Bharti Airtel",           "type": "NSE",  "logo": "BHARTIARTL"},
    {"ticker": "MARUTI.NS",     "tv": "NSE:MARUTI",       "name": "Maruti Suzuki",           "type": "NSE",  "logo": "MARUTI"},
    {"ticker": "AXISBANK.NS",   "tv": "NSE:AXISBANK",    "name": "Axis Bank",               "type": "NSE",  "logo": "AXISBANK"},
    {"ticker": "KOTAKBANK.NS",  "tv": "NSE:KOTAKBANK",    "name": "Kotak Mahindra Bank",    "type": "NSE",  "logo": "KOTAKBANK"},
    {"ticker": "SUNPHARMA.NS",  "tv": "NSE:SUNPHARMA",   "name": "Sun Pharma",              "type": "NSE",  "logo": "SUNPHARMA"},
    {"ticker": "ITC.NS",        "tv": "NSE:ITC",          "name": "ITC Limited",             "type": "NSE",  "logo": "ITC"},
    {"ticker": "^NSEI",         "tv": "NSE:NIFTY",        "name": "Nifty 50 Index",          "type": "Index", "logo": "NIFTY50"},
    {"ticker": "^NSEBANK",      "tv": "NSE:NIFTYBANK",   "name": "Bank Nifty Index",       "type": "Index", "logo": "NIFTYBANK"},
    # US - NASDAQ / NYSE
    {"ticker": "AAPL",          "tv": "NASDAQ:AAPL",      "name": "Apple Inc",               "type": "NASDAQ", "logo": "AAPL"},
    {"ticker": "MSFT",          "tv": "NASDAQ:MSFT",      "name": "Microsoft",               "type": "NASDAQ", "logo": "MSFT"},
    {"ticker": "AMZN",          "tv": "NASDAQ:AMZN",      "name": "Amazon",                  "type": "NASDAQ", "logo": "AMZN"},
    {"ticker": "GOOGL",         "tv": "NASDAQ:GOOGL",     "name": "Alphabet (Google)",       "type": "NASDAQ", "logo": "GOOGL"},
    {"ticker": "TSLA",          "tv": "NASDAQ:TSLA",      "name": "Tesla",                   "type": "NASDAQ", "logo": "TSLA"},
    {"ticker": "META",          "tv": "NASDAQ:META",      "name": "Meta Platforms",          "type": "NASDAQ", "logo": "META"},
    {"ticker": "NVDA",          "tv": "NASDAQ:NVDA",     "name": "Nvidia",                  "type": "NASDAQ", "logo": "NVDA"},
    {"ticker": "NFLX",          "tv": "NASDAQ:NFLX",      "name": "Netflix",                 "type": "NASDAQ", "logo": "NFLX"},
    {"ticker": "INTC",          "tv": "NASDAQ:INTC",     "name": "Intel",                   "type": "NASDAQ", "logo": "INTC"},
    {"ticker": "KO",            "tv": "NYSE:KO",          "name": "Coca-Cola",               "type": "NYSE",   "logo": "KO"},
    {"ticker": "WMT",           "tv": "NYSE:WMT",         "name": "Walmart",                 "type": "NYSE",   "logo": "WMT"},
    {"ticker": "JPM",           "tv": "NYSE:JPM",         "name": "JPMorgan Chase",          "type": "NYSE",   "logo": "JPM"},
    # Crypto
    {"ticker": "BTC-USD",       "tv": "BINANCE:BTCUSDT",  "name": "Bitcoin",                 "type": "Crypto", "logo": "BTC"},
    {"ticker": "ETH-USD",       "tv": "BINANCE:ETHUSDT",  "name": "Ethereum",                "type": "Crypto", "logo": "ETH"},
    {"ticker": "SOL-USD",       "tv": "BINANCE:SOLUSDT",  "name": "Solana",                  "type": "Crypto", "logo": "SOL"},
    {"ticker": "DOGE-USD",      "tv": "BINANCE:DOGEUSDT", "name": "Dogecoin",                "type": "Crypto", "logo": "DOGE"},
    # Commodities
    {"ticker": "GC=F",          "tv": "TVC:GOLD",         "name": "Gold Futures",            "type": "Commodity", "logo": "GOLD"},
]

# ── Navigation Tabs ──
NAV_TABS = ["Dashboard", "AI Analysis", "Strategy Bot", "Backtester", "Quant Tools", "Quant Trade", "Quant Trading", "Portfolio", "Trading Bot"]
active_tab = st.sidebar.selectbox("Navigate", NAV_TABS, key="nav_tab")

if active_tab != "Dashboard":
    if active_tab == "Strategy Bot":
        from modules.strategy_bot import render_strategy_bot
        render_strategy_bot()
    elif active_tab == "Backtester":
        from modules.backtester import render_backtester
    elif active_tab == "Quant Tools":
        from modules.quant_tools import render_quant_tools
        render_quant_tools()
        render_backtester()
    elif active_tab == "Quant Trade":
        from modules.quant_trade import render_quant_trade
        render_quant_trade()
    elif active_tab == "Quant Trading":
        from modules.quant_trading import render_quant_trading
        render_quant_trading()
    elif active_tab == "Portfolio":
        from modules.portfolio_tracker import render_portfolio_tracker
        render_portfolio_tracker()
    elif active_tab == "AI Analysis":
        from modules.ai_analysis import render_ai_analysis
        render_ai_analysis()
    elif active_tab == "Trading Bot":
        from modules.trading_bot import render_trading_bot
        render_trading_bot()
    st.stop()

BROKERS = [
    {"id": "zerodha",  "name": "Zerodha Kite", "note": "Kite Connect API",       "fields": ["API Key", "API Secret"]},
    {"id": "upstox",   "name": "Upstox",      "note": "Upstox API v2",          "fields": ["API Key", "API Secret", "Redirect URI"]},
    {"id": "angelone", "name": "Angel One",   "note": "SmartAPI",               "fields": ["API Key", "Client ID", "PIN"]},
    {"id": "fyers",    "name": "Fyers",        "note": "Fyers API v3",          "fields": ["App ID", "Secret Key"]},
    {"id": "generic",  "name": "Any broker",   "note": "Custom REST / WebSocket", "fields": ["Base URL", "API Key"]},
]

# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────

if "selected_asset" not in st.session_state:
    st.session_state.selected_asset = None
if "show_analysis" not in st.session_state:
    st.session_state.show_analysis = False
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "voice_generated" not in st.session_state:
    st.session_state.voice_generated = None
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "connection" not in st.session_state:
    st.session_state.connection = None
if "credentials" not in st.session_state:
    st.session_state.credentials = {}
if "period" not in st.session_state:
    st.session_state.period = "10y"
if "interval" not in st.session_state:
    st.session_state.interval = "1d"
if "backtest_result" not in st.session_state:
    st.session_state.backtest_result = None
if "order_message" not in st.session_state:
    st.session_state.order_message = None

# ──────────────────────────────────────────────
# DATA FETCH (yfinance)
# ──────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_ohlc(ticker, period="6mo", interval="1d"):
    """Fetch real OHLC data using yfinance. Returns DataFrame with lowercase columns."""
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        date_col = "Date" if "Date" in df.columns else "Datetime"
        df = df.rename(columns={date_col: "date"})
        # Rename to lowercase
        rename_map = {}
        for col in df.columns:
            cl = col.lower()
            if cl == "open": rename_map[col] = "open"
            elif cl == "high": rename_map[col] = "high"
            elif cl == "low": rename_map[col] = "low"
            elif cl == "close": rename_map[col] = "close"
            elif cl == "volume": rename_map[col] = "volume"
        df = df.rename(columns=rename_map)
        # Ensure numeric
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close"])
        return df
    except Exception:
        return None

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
# PIVOT DETECTION & TREND LINES
# ──────────────────────────────────────────────

def find_pivots(df, lookback=3):
    highs, lows = [], []
    n = len(df)
    for i in range(lookback, n - lookback):
        is_high = True
        is_low = True
        for j in range(i - lookback, i + lookback + 1):
            if j == i:
                continue
            if df["high"].iloc[j] >= df["high"].iloc[i]:
                is_high = False
            if df["low"].iloc[j] <= df["low"].iloc[i]:
                is_low = False
        if is_high:
            highs.append({"idx": i, "price": df["high"].iloc[i]})
        if is_low:
            lows.append({"idx": i, "price": df["low"].iloc[i]})
    return {"highs": highs, "lows": lows}

def linear_regression(points):
    n_pts = len(points)
    if n_pts < 2:
        return None
    sum_x = sum(p["idx"] for p in points)
    sum_y = sum(p["price"] for p in points)
    sum_xy = sum(p["idx"] * p["price"] for p in points)
    sum_xx = sum(p["idx"] ** 2 for p in points)
    denom = n_pts * sum_xx - sum_x * sum_x
    if denom == 0:
        return None
    slope = (n_pts * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n_pts
    return {"slope": slope, "intercept": intercept}

# ──────────────────────────────────────────────
# ANALYSIS (chart data)
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
    sma200_vals = sma(closes, 200)
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
    last_sma200 = last_val(sma200_vals)
    last_bb_upper = last_val(bb_upper)
    last_bb_lower = last_val(bb_lower)

    avg_vol = df["volume"].iloc[-20:].mean() if "volume" in df.columns else 0
    vol_ratio = round(last["volume"] / avg_vol, 2) if avg_vol else 0

    returns = closes.pct_change().dropna()
    daily_vol = returns.std()
    annualized_vol = round(daily_vol * np.sqrt(252) * 100, 2) if daily_vol else 0
    mean_return = returns.mean()
    sharpe = round((mean_return * 252) / (daily_vol * np.sqrt(252)) if daily_vol else 0, 2)

    # Skewness & Kurtosis
    n_ret = len(returns)
    skewness = round(float(n_ret / ((n_ret-1)*(n_ret-2)) * np.sum(((returns - mean_return) / daily_vol) ** 3)), 3) if daily_vol and n_ret > 2 else 0
    kurtosis = round(float(n_ret*(n_ret+1) / ((n_ret-1)*(n_ret-2)*(n_ret-3)) * np.sum(((returns - mean_return) / daily_vol) ** 4) - 3*(n_ret-1)**2/((n_ret-2)*(n_ret-3))), 3) if daily_vol and n_ret > 3 else 0

    # Sortino ratio
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
    sortino = round(float(mean_return * 252 / downside_std), 2) if downside_std and downside_std != 0 else 0

    # Golden/Death Cross
    golden_cross = False
    death_cross = False
    if last_sma50 is not None and last_sma200 is not None:
        prev_sma50 = sma50_vals.iloc[-2] if len(sma50_vals) > 1 else None
        prev_sma200 = sma200_vals.iloc[-2] if len(sma200_vals) > 1 else None
        if prev_sma50 is not None and prev_sma200 is not None and not np.isnan(prev_sma50) and not np.isnan(prev_sma200):
            if last_sma50 > last_sma200 and prev_sma50 <= prev_sma200:
                golden_cross = True
            elif last_sma50 < last_sma200 and prev_sma50 >= prev_sma200:
                death_cross = True

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

    pivots = find_pivots(df)
    res_trend = linear_regression(pivots["highs"][-6:]) if len(pivots["highs"]) >= 2 else None
    sup_trend = linear_regression(pivots["lows"][-6:]) if len(pivots["lows"]) >= 2 else None

    n_candles = len(df)
    res_trend_vals = None
    sup_trend_vals = None
    if res_trend:
        res_trend_vals = [round(res_trend["slope"] * i + res_trend["intercept"], 2) for i in range(n_candles)]
    if sup_trend:
        sup_trend_vals = [round(sup_trend["slope"] * i + sup_trend["intercept"], 2) for i in range(n_candles)]

    return {
        "change_pct": change_pct, "day_change_pct": day_change_pct,
        "last_rsi": last_rsi, "last_macd": last_macd, "last_signal": last_signal,
        "last_hist": last_hist, "last_sma20": last_sma20, "last_sma50": last_sma50,
        "bb_upper": last_bb_upper, "bb_lower": last_bb_lower,
        "avg_vol": avg_vol, "vol_ratio": vol_ratio,
        "annualized_vol": annualized_vol, "sharpe": sharpe,
        "sortino": sortino, "skewness": skewness, "kurtosis": kurtosis,
        "golden_cross": golden_cross, "death_cross": death_cross, "last_sma200": last_sma200,
        "verdict": verdict, "bull_signals": bull, "bear_signals": bear,
        "patterns": patterns, "support": support, "resistance": resistance,
        "sma20": sma20_vals, "sma50": sma50_vals, "sma200": sma200_vals,
        "rsi_vals": rsi_vals, "macd_line": macd_line, "signal_line": signal_line,
        "hist": hist, "bb_upper_series": bb_upper, "bb_lower_series": bb_lower, "bb_mid_series": bb_mid,
        "res_trend": res_trend, "sup_trend": sup_trend,
        "res_trend_vals": res_trend_vals, "sup_trend_vals": sup_trend_vals,
        "pivots": pivots,
    }

# ──────────────────────────────────────────────
# AI ANALYSIS (quant + technical + summary)
# ──────────────────────────────────────────────

def compute_ai_summary(df):
    """Compute indicators and build a quant + technical + overall summary."""
    close = df["close"]

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_val = ema12 - ema26
    signal_val = macd_val.ewm(span=9, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi_val = 100 - (100 / (1 + rs))

    daily_returns = close.pct_change().dropna()
    volatility = float(daily_returns.std() * np.sqrt(252) * 100) if len(daily_returns) > 0 else 0
    sharpe = float((daily_returns.mean() / daily_returns.std()) * np.sqrt(252)) if len(daily_returns) > 0 and daily_returns.std() != 0 else 0

    last_close = float(close.iloc[-1])
    last_sma20 = float(sma20.iloc[-1]) if not pd.isna(sma20.iloc[-1]) else None
    last_sma50 = float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else None
    last_rsi = float(rsi_val.iloc[-1]) if not pd.isna(rsi_val.iloc[-1]) else None
    last_macd = float(macd_val.iloc[-1]) if not pd.isna(macd_val.iloc[-1]) else 0
    last_signal = float(signal_val.iloc[-1]) if not pd.isna(signal_val.iloc[-1]) else 0

    period_high = round(float(close.max()), 2)
    period_low = round(float(close.min()), 2)

    # Build summary
    trend = "uptrend" if last_sma20 and last_close > last_sma20 else "downtrend"
    if last_sma20 and last_sma50:
        trend_strength = "strong" if (last_sma20 > last_sma50) == (trend == "uptrend") else "weak/mixed"
    else:
        trend_strength = "insufficient data"

    if last_rsi is None:
        rsi_state = "not enough data"
    elif last_rsi > 70:
        rsi_state = "overbought"
    elif last_rsi < 30:
        rsi_state = "oversold"
    else:
        rsi_state = "neutral"

    macd_state = "bullish crossover" if last_macd > last_signal else "bearish crossover"

    quant_text = (
        f"Annualized volatility is {round(volatility, 2)}%, with a Sharpe ratio of "
        f"{round(sharpe, 2)}. Price is trading between a period low of {period_low} and "
        f"high of {period_high}, currently at {round(last_close, 2)}."
    )

    technical_text = (
        f"Price is in a {trend} ({trend_strength}) relative to the 20/50-day SMA "
        f"({round(last_sma20, 2) if last_sma20 else 'N/A'}/{round(last_sma50, 2) if last_sma50 else 'N/A'}). "
        f"RSI(14) is at {round(last_rsi, 2) if last_rsi else 'N/A'} ({rsi_state}). "
        f"MACD ({round(last_macd, 4)}) vs signal ({round(last_signal, 4)}) indicates a {macd_state}."
    )

    overall_bias = "bullish" if trend == "uptrend" and last_macd > last_signal else "cautious/bearish" if trend == "downtrend" and last_macd < last_signal else "mixed"
    rsi_advice = "watch for a pullback before entry" if rsi_state == "overbought" else "watch for reversal confirmation" if rsi_state == "oversold" else "no extreme momentum signal currently"

    overall_summary = (
        f"Overall bias leans {overall_bias}. "
        f"RSI suggests {rsi_state} conditions, so {rsi_advice}. "
        f"Use the period range ({period_low}\u2013{period_high}) as reference support/resistance."
    )

    return {
        "quant": quant_text,
        "technical": technical_text,
        "summary": overall_summary,
        "indicators": {
            "last_close": round(last_close, 2),
            "sma20": round(last_sma20, 2) if last_sma20 else None,
            "sma50": round(last_sma50, 2) if last_sma50 else None,
            "rsi14": round(last_rsi, 2) if last_rsi else None,
            "macd": round(last_macd, 4),
            "macd_signal": round(last_signal, 4),
            "volatility_pct": round(volatility, 2),
            "sharpe": round(sharpe, 2),
            "period_high": period_high,
            "period_low": period_low,
        },
    }

# ──────────────────────────────────────────────
# FORMATTERS
# ──────────────────────────────────────────────

# ──────────────────────────────────────────────
# SIGNAL ENGINE (SMA crossover + RSI + MACD)
# ──────────────────────────────────────────────

def generate_signals(df, rsi_buy=40, rsi_sell=65):
    """Rule-based BUY/SELL/HOLD signals using SMA crossover + RSI + MACD."""
    df = df.copy()
    df["sma_fast"] = df["close"].rolling(20).mean()
    df["sma_slow"] = df["close"].rolling(50).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    df["rsi_sig"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd_sig"] = ema12 - ema26
    df["macd_sig_signal"] = df["macd_sig"].ewm(span=9, adjust=False).mean()

    df["signal"] = "HOLD"
    buy_cond = (df["sma_fast"] > df["sma_slow"]) & (df["rsi_sig"] < rsi_buy) & (df["macd_sig"] > df["macd_sig_signal"])
    sell_cond = (df["sma_fast"] < df["sma_slow"]) | (df["rsi_sig"] > rsi_sell) | (df["macd_sig"] < df["macd_sig_signal"])
    df.loc[buy_cond, "signal"] = "BUY"
    df.loc[sell_cond & ~buy_cond, "signal"] = "SELL"
    return df

def latest_signal(df):
    """Return the latest signal dict."""
    sig_df = generate_signals(df)
    last = sig_df.iloc[-1]
    return {
        "signal": last["signal"],
        "close": round(float(last["close"]), 2),
        "sma_fast": round(float(last["sma_fast"]), 2) if not pd.isna(last["sma_fast"]) else None,
        "sma_slow": round(float(last["sma_slow"]), 2) if not pd.isna(last["sma_slow"]) else None,
        "rsi": round(float(last["rsi_sig"]), 2) if not pd.isna(last["rsi_sig"]) else None,
        "macd": round(float(last["macd_sig"]), 4) if not pd.isna(last["macd_sig"]) else None,
        "macd_signal": round(float(last["macd_sig_signal"]), 4) if not pd.isna(last["macd_sig_signal"]) else None,
    }

# ──────────────────────────────────────────────
# BACKTESTER
# ──────────────────────────────────────────────

def run_backtest(df, initial_cash=100000.0, qty_per_trade=10):
    """Simulate the signal strategy on historical data."""
    sig_df = generate_signals(df).dropna(subset=["sma_slow"]).reset_index(drop=True)

    cash = initial_cash
    position = 0
    trades = []
    equity_curve = []

    for _, row in sig_df.iterrows():
        price = float(row["close"])
        date = str(row["date"]) if "date" in row else str(row.name)

        if row["signal"] == "BUY" and cash >= price * qty_per_trade:
            cash -= price * qty_per_trade
            position += qty_per_trade
            trades.append({"date": date, "action": "BUY", "price": round(price, 2), "qty": qty_per_trade})
        elif row["signal"] == "SELL" and position > 0:
            cash += price * position
            trades.append({"date": date, "action": "SELL", "price": round(price, 2), "qty": position})
            position = 0

        equity = cash + position * price
        equity_curve.append({"date": date, "equity": round(equity, 2)})

    final_price = float(sig_df.iloc[-1]["close"])
    final_equity = cash + position * final_price
    total_return_pct = ((final_equity - initial_cash) / initial_cash) * 100

    equity_series = pd.Series([e["equity"] for e in equity_curve])
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max * 100
    max_drawdown_pct = round(float(drawdown.min()), 2) if len(drawdown) else 0

    completed = [t for t in trades if t["action"] == "SELL"]
    wins = 0
    buy_stack = []
    for t in trades:
        if t["action"] == "BUY":
            buy_stack.append(t["price"])
        elif t["action"] == "SELL" and buy_stack:
            avg_buy = sum(buy_stack) / max(len(buy_stack), 1)
            if t["price"] > avg_buy:
                wins += 1
            buy_stack = []

    win_rate = round((wins / len(completed)) * 100, 2) if completed else 0

    return {
        "initial_cash": initial_cash,
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "max_drawdown_pct": max_drawdown_pct,
        "total_trades": len(trades),
        "win_rate_pct": win_rate,
        "trades": trades[-20:],
        "equity_curve": equity_curve,
    }

def equity_curve_chart(equity_curve, theme="dark"):
    """Plotly chart for backtest equity curve."""
    template = "plotly_dark" if theme == "dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)" if theme == "dark" else "rgba(255,255,255,0)"
    dates = [e["date"] for e in equity_curve]
    values = [e["equity"] for e in equity_curve]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=values, name="Equity",
        fill="tozeroy", fillcolor="rgba(42,120,214,0.12)",
        line=dict(color="#2a78d6", width=2),
    ))
    fig.update_layout(template=template, height=280,
                      margin=dict(l=50, r=20, t=20, b=30),
                      yaxis_title="Equity", showlegend=False,
                      font=dict(size=11), paper_bgcolor=bg_color, plot_bgcolor=bg_color)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(50,50,50,0.3)" if theme == "dark" else "rgba(200,200,200,0.5)")
    return fig

# ──────────────────────────────────────────────
# BROKER CONNECTOR (Sandbox mode)
# ──────────────────────────────────────────────

SANDBOX_MODE = True

def place_order_simulated(ticker, side, qty=10):
    """Sandbox order placement - no real orders."""
    if SANDBOX_MODE:
        return {
            "status": "SIMULATED",
            "message": f"[SANDBOX] Would {side} {qty} of {ticker} (MARKET). No real order placed.",
        }
    return {"status": "ERROR", "message": "Live trading not implemented."}

def fmt_vol(n):
    if n is None: return "\u2014"
    if n >= 1e7: return f"{n/1e7:.2f}Cr"
    if n >= 1e5: return f"{n/1e5:.2f}L"
    if n >= 1e3: return f"{n/1e3:.1f}K"
    return str(int(n))

def fmt_num(n):
    if n is None: return "\u2014"
    if isinstance(n, float) and np.isnan(n): return "\u2014"
    return f"{n:,.0f}"

# ──────────────────────────────────────────────
# TRADINGVIEW EMBED
# ──────────────────────────────────────────────

def render_tradingview(symbol, theme="dark", height=600):
    """Render TradingView advanced chart with native zoom/pan/drawing tools."""
    tv_symbol = symbol if ":" in symbol else f"NSE:{symbol}"
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
    """
    components.html(html, height=height)
def render_tradingview_fullscreen(symbol, theme="dark"):
    """Render TradingView chart in fullscreen overlay."""
    tv_symbol = symbol if ":" in symbol else f"NSE:{symbol}"
    html = f"""
    <div id="tv-fs" style="position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:99999;background:#131722;">
      <div class="tradingview-widget-container" style="height:100vh;width:100vw;">
        <div class="tradingview-widget-container__widget" style="height:100vh;width:100vw;"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
        {{
          "autosize": true,
          "symbol": "{tv_symbol}",
          "interval": "D",
          "timezone": "Asia/Kolkata",
          "theme": "{theme}",
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
      <button onclick="var e=document.getElementById('tv-fs');e.parentNode.removeChild(e);document.body.style.overflow='';" style="position:fixed;top:12px;right:12px;z-index:100000;background:#ef4444;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:14px;cursor:pointer;font-weight:600;">✖ Close Fullscreen</button>
    </div>
    <script>document.body.style.overflow='hidden';</script>
    """
    components.html(html, height=1000)

    if st.button("Exit Fullscreen", key="tv_fs_exit", type="secondary"):
        st.session_state["tv_fullscreen"] = False
        st.rerun()

def render_tradingview_ticker(symbol, theme="dark"):
    tv_sym = symbol.replace(".NS", "") if ".NS" in symbol else symbol
    if symbol.startswith("^"):
        tv_sym = "NIFTY" if symbol == "^NSEI" else "NIFTYBANK" if symbol == "^NSEBANK" else symbol
    html = f"""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
      {{
        "symbols": [
          {{"proName": "NSE:{tv_sym}", "title": "{tv_sym}"}},
          {{"proName": "NSE:RELIANCE", "title": "RELIANCE"}},
          {{"proName": "NSE:TCS", "title": "TCS"}},
          {{"proName": "NSE:HDFCBANK", "title": "HDFCBANK"}},
          {{"proName": "NSE:NIFTY", "title": "NIFTY 50"}}
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
# VOICE NARRATION
# ──────────────────────────────────────────────

def build_narration(asset_name, summary=None):
    parts = [f"Here's the read on {asset_name}."]
    if summary:
        parts.append(summary["quant"])
        parts.append(summary["technical"])
        parts.append(summary["summary"])
    else:
        parts.append("The chart is showing real market data with SMA, RSI, MACD, and Bollinger Bands overlaid.")
        parts.append("Use RSI to judge overbought or oversold conditions. Above 70 signals overbought, below 30 oversold.")
        parts.append("MACD crossing above its signal line is bullish momentum, and crossing below as bearish.")
    parts.append("Remember, none of this is financial advice.")
    return " ".join(parts)

def generate_audio(text):
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
# PLOTLY CHARTS
# ──────────────────────────────────────────────

def candlestick_chart(df, analysis, show_ma, show_bb, show_trend, theme="dark"):
    template = "plotly_dark" if theme == "dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)" if theme == "dark" else "rgba(255,255,255,0)"
    grid_color = "rgba(50,50,50,0.25)" if theme == "dark" else "rgba(200,200,200,0.4)"

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.46, 0.16, 0.18, 0.20],
        subplot_titles=("Price & Indicators", "Volume", "RSI (14)", "MACD (12, 26, 9)"),
    )

    # TradingView-style candlestick - exact TradingView colors & styling
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="OHLC",
        # TradingView exact colors: #26a69a (bullish green), #ef5350 (bearish red)
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
        increasing_fillcolor="#26a69a",
        decreasing_fillcolor="#ef5350",
        # Thicker wicks for better visibility
        line_width=2,
        # Narrow whiskers to emphasize body
        whiskerwidth=0.3,
        # Make sure body is visible even for small candles
        selector=dict(type="candlestick"),
    ), row=1, col=1)

    # Ensure minimum candle width (TradingView style: visible bodies)
    fig.update_traces(
        increasing_line_width=2,
        decreasing_line_width=2,
        selector=dict(type="candlestick"),
    )

    if show_ma:
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["sma20"], name="SMA 20",
                                 line=dict(color="#2962ff", width=1.8)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["sma50"], name="SMA 50",
                                 line=dict(color="#ff9800", width=1.8)), row=1, col=1)
        if analysis.get("sma200"):
            fig.add_trace(go.Scatter(x=df["date"], y=analysis["sma200"], name="SMA 200",
                                     line=dict(color="#9c27b0", width=1.8)), row=1, col=1)

    if show_bb:
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["bb_upper_series"], name="BB Upper",
                                 line=dict(color="#9575cd", width=1.2, dash="dot"), opacity=0.7), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["bb_lower_series"], name="BB Lower",
                                 line=dict(color="#9575cd", width=1.2, dash="dot"), opacity=0.7, showlegend=False), row=1, col=1)

    if show_trend and analysis.get("res_trend_vals") is not None:
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["res_trend_vals"], name="Resistance Trend",
                                 line=dict(color="#ef5350", width=2, dash="dash"), opacity=0.9), row=1, col=1)
    if show_trend and analysis.get("sup_trend_vals") is not None:
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["sup_trend_vals"], name="Support Trend",
                                 line=dict(color="#26a69a", width=2, dash="dash"), opacity=0.9), row=1, col=1)

    # Support / Resistance horizontal lines - BOLD and visible like TradingView
    fig.add_hline(y=analysis["resistance"], line_dash="solid", line_color="#ef5350",
                  line_width=2, opacity=0.8, row=1, col=1,
                  annotation_text=f"R: {analysis['resistance']:.2f}",
                  annotation_position="top right", annotation_font_size=10,
                  annotation_font_color="#ef5350")
    fig.add_hline(y=analysis["support"], line_dash="solid", line_color="#26a69a",
                  line_width=2, opacity=0.8, row=1, col=1,
                  annotation_text=f"S: {analysis['support']:.2f}",
                  annotation_position="bottom right", annotation_font_size=10,
                  annotation_font_color="#26a69a")

    if "volume" in df.columns:
        colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(df["close"], df["open"])]
        fig.add_trace(go.Bar(x=df["date"], y=df["volume"], name="Volume",
                             marker_color=colors, opacity=0.6), row=2, col=1)
        if analysis.get("avg_vol"):
            fig.add_hline(y=analysis["avg_vol"], line_dash="dash", line_color="#7c7b76",
                          opacity=0.5, row=2, col=1)

    fig.add_trace(go.Scatter(x=df["date"], y=analysis["rsi_vals"], name="RSI",
                             line=dict(color="#ab47bc", width=1.8)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#ef5350", line_width=1, opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#26a69a", line_width=1, opacity=0.5, row=3, col=1)

    hist_colors = ["#26a69a" if h >= 0 else "#ef5350" for h in analysis["hist"]]
    fig.add_trace(go.Bar(x=df["date"], y=analysis["hist"], name="MACD Hist",
                         marker_color=hist_colors, opacity=0.6), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=analysis["macd_line"], name="MACD",
                             line=dict(color="#2962ff", width=1.6)), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=analysis["signal_line"], name="Signal",
                             line=dict(color="#ff9800", width=1.6)), row=4, col=1)

    fig.update_layout(
        template=template,
        height=820,
        margin=dict(l=50, r=60, t=40, b=30),
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(size=11, family="Trebuchet MS, sans-serif"),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        hovermode="x unified",
        dragmode="zoom",
        # TradingView-like crosshair
        xaxis=dict(showspikes=True, spikethickness=1, spikedash="solid", spikelength=8, spikecolor="rgba(150,150,150,0.4)"),
        yaxis=dict(showspikes=True, spikethickness=1, spikedash="solid", spikelength=8, spikecolor="rgba(150,150,150,0.4)"),
    )
    # TradingView-like axis styling
    fig.update_xaxes(showgrid=False, showline=True, linecolor=grid_color, mirror=True)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=grid_color, side="right",
                     showline=True, linecolor=grid_color, mirror=True)
    # Fix y-axis to show proper price formatting
    fig.update_yaxes(tickformat=".2f", row=1, col=1)
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
# SIDEBAR (shared)
# ──────────────────────────────────────────────

theme = st.session_state.theme

st.sidebar.markdown("## \u2699\ufe0f Settings")

theme_col1, theme_col2 = st.sidebar.columns([1, 1])
if theme_col1.button("\U0001f319 Dark", use_container_width=True,
                     type="primary" if st.session_state.theme == "dark" else "secondary"):
    st.session_state.theme = "dark"
    st.rerun()
if theme_col2.button("\u2600\ufe0f Light", use_container_width=True,
                     type="primary" if st.session_state.theme == "light" else "secondary"):
    st.session_state.theme = "light"
    st.rerun()

st.sidebar.markdown("---")

# ── Broker Connection Panel ──
st.sidebar.markdown("### \U0001f517 Broker Connection")

if st.session_state.connection:
    conn = st.session_state.connection
    mode_label = "\U0001f7e2 Live" if conn.get("mode") == "live" else "\U0001f7e1 Demo"
    st.sidebar.markdown(f"""
    <div style='padding:10px 14px; border-radius:8px; background:{"#1a3d1a" if theme=="dark" else "#d4edda"};
    border:1px solid {"#2a5a2a" if theme=="dark" else "#c3e6cb"};'>
        <div style='font-weight:700;font-size:13px;'>{conn["name"]} {mode_label}</div>
        <div style='font-size:11px;opacity:0.7;margin-top:2px;'>Connected {conn["connected_at"]}</div>
    </div>
    """, unsafe_allow_html=True)
    if st.sidebar.button("\U0001f50c Disconnect", use_container_width=True):
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
    st.sidebar.caption(f"\U0001f4cb {broker_meta['note']}")

    credentials = {}
    for field in broker_meta["fields"]:
        is_secret = "secret" in field.lower() or "pin" in field.lower() or "key" in field.lower()
        credentials[field] = st.sidebar.text_input(
            field, type="password" if is_secret else "default",
            key=f"cred_{selected_broker_id}_{field}"
        )

    if st.sidebar.button("\U0001f517 Connect", use_container_width=True, type="primary"):
        st.session_state.connection = {
            "broker_id": selected_broker_id,
            "name": broker_meta["name"],
            "connected_at": time.strftime("%H:%M:%S"),
            "mode": "demo",
        }
        st.session_state.credentials = credentials
        st.sidebar.success(f"\u2705 Connected to {broker_meta['name']} (Demo)")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("\U0001f4ca Quant Desk \u2014 Real data via yfinance. Not financial advice.")

# ──────────────────────────────────────────────
# WATCHLIST SCREEN
# ──────────────────────────────────────────────

if st.session_state.selected_asset is None:
    st.markdown("## \U0001f4ca Quant Desk")
    st.markdown("### Watchlist \u2014 Chart kholne ke liye ek asset chuniye")
    st.markdown("")

    search_query = st.text_input("\U0001f50d Search", placeholder="Type ticker or name...", key="watchlist_search")
    filtered = [a for a in ASSETS if
        search_query.lower() in a["ticker"].lower() or
        search_query.lower() in a["name"].lower() or
        search_query.lower() in a.get("tv", "").lower()]

    if not filtered:
        st.warning("No matches found")
    else:
        cols = st.columns(4)
        for i, asset in enumerate(filtered):
            with cols[i % 4]:
                logo_url = f"https://s3-symbol-logo.tradingview.com/{asset.get('logo', asset['ticker']).lower()}.svg"
                st.markdown(
                    f'<img src="{logo_url}" width="28" height="28" '
                    f'style="border-radius:6px;object-fit:contain;background:#fff;padding:2px;" '
                    f'onerror="this.style.display=\'none\'">',
                    unsafe_allow_html=True
                )
                card_key = f"asset_card_{i}"
                if st.button(
                    f"**{asset['ticker']}**\n{asset['name']}\n{asset['type']}",
                    key=card_key,
                    use_container_width=True,
                ):
                    st.session_state.selected_asset = asset
                    st.session_state.show_analysis = False
                    st.session_state.analysis_result = None
                    st.session_state.voice_generated = None
                    st.session_state.backtest_result = None
                    st.session_state.order_message = None
                    st.rerun()

    st.markdown("---")
    st.caption("\U0001f4ca Data source: yfinance (real market data) \u2014 Educational use only, not financial advice.")

# ──────────────────────────────────────────────
# DASHBOARD SCREEN
# ──────────────────────────────────────────────

else:
    asset = st.session_state.selected_asset
    ticker = asset["ticker"]

    # Back button in sidebar
    if st.sidebar.button("\u2190 Back to Watchlist", use_container_width=True):
        st.session_state.selected_asset = None
        st.session_state.show_analysis = False
        st.session_state.analysis_result = None
        st.session_state.voice_generated = None
        st.session_state.backtest_result = None
        st.session_state.order_message = None
        st.rerun()

    # Period fixed to 10y (live + historical)
    st.session_state.period = "10y"
    st.session_state.interval = "1d"
    # ── Fetch data ──
    with st.spinner(f"Fetching real data for {ticker}..."):
        df = fetch_ohlc(ticker, st.session_state.period, st.session_state.interval)

    if df is None or len(df) < 5:
        with st.expander("\u26a0\ufe0f Error Details (click to expand)"):
            st.error(f"Could not fetch data for {ticker}. Please try a different period or asset.")
        if st.button("\u2190 Back to Watchlist"):
            st.session_state.selected_asset = None
            st.rerun()
        st.stop()

    analysis = build_analysis(df)
    last_price = float(df["close"].iloc[-1])

    # -- Compute signal --
    sig = latest_signal(df)
    sig_colors = {"BUY": "#0ca30c", "SELL": "#d03b3b", "HOLD": "#898781"}
    sig_color = sig_colors.get(sig["signal"], "#898781")

    # -- Header --
    col_title, col_signal, col_badge, col_price = st.columns([3, 1, 1, 1])
    with col_title:
        st.markdown(f"## \U0001f4ca {ticker} \u2014 {asset['name']}")
        st.caption(f"{asset['type']} \u00b7 Data via yfinance \u00b7 {st.session_state.period} / {st.session_state.interval}")
    with col_signal:
        st.markdown(f"""
        <div style='text-align:center;padding:8px 16px;border-radius:20px;background:{sig_color}22;color:{sig_color};font-size:1.1rem;font-weight:700;'>
            {sig['signal']}
        </div>
        """, unsafe_allow_html=True)
    with col_badge:
        if st.session_state.connection:
            st.markdown(f"\U0001f7e1 {st.session_state.connection['name']} \u00b7 Demo")
        else:
            st.markdown("\u26aa No broker connected")
    with col_price:
        st.metric("Last Price", f"\u20b9{last_price:,.2f}" if ticker.endswith(".NS") or ticker.startswith("^") else f"${last_price:,.2f}",
                  f"{analysis['day_change_pct']:+.2f}% today")

    # ── Ticker tape ──
    render_tradingview_ticker(ticker, theme)

    st.markdown("")

    # ── AI Analysis + Voice buttons (side by side, above chart) ──
    # -- Signal metrics row --
    sig_col1, sig_col2, sig_col3, sig_col4 = st.columns(4)
    with sig_col1:
        st.metric("Signal: " + sig["signal"], f"\u20b9{sig['close']:,.2f}")
    with sig_col2:
        st.metric("SMA 20", f"{sig['sma_fast']:.2f}" if sig['sma_fast'] else "\u2014")
    with sig_col3:
        st.metric("SMA 50", f"{sig['sma_slow']:.2f}" if sig['sma_slow'] else "\u2014")
    with sig_col4:
        st.metric("RSI (14)", f"{sig['rsi']:.1f}" if sig['rsi'] else "\u2014")

    st.markdown("")

    # -- AI Analysis + Voice + Backtest + Order buttons --
    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns([1, 1, 1, 1, 1])

    with btn_col1:
        if st.button("\u2728 AI Analysis", type="primary", use_container_width=True):
            st.session_state.show_analysis = True
            st.session_state.analysis_result = compute_ai_summary(df)
            st.session_state.voice_generated = None

    with btn_col2:
        if st.button("\U0001f50a Voice Brief", use_container_width=True):
            narration = build_narration(asset["name"],
                st.session_state.analysis_result if st.session_state.show_analysis else None)
            with st.spinner("Generating audio..."):
                audio_bytes = generate_audio(narration)
                if audio_bytes:
                    st.session_state.voice_generated = audio_bytes
                else:
                    st.error("\u274c Failed to generate audio. gTTS might not be available.")

    with btn_col3:
        if st.button("\U0001f504 Run Backtest", use_container_width=True):
            with st.spinner("Running backtest simulation..."):
                bt_df = fetch_ohlc(ticker, "1y", "1d")
                if bt_df is not None and len(bt_df) > 50:
                    st.session_state.backtest_result = run_backtest(bt_df)
                else:
                    st.error("\u274c Not enough data for backtest.")

    with btn_col4:
        if st.button("\U0001f7e2 Sim BUY", use_container_width=True):
            result = place_order_simulated(ticker, "BUY", 10)
            st.session_state.order_message = result["message"]

    with btn_col5:
        if st.button("\U0001f7e3 Sim SELL", use_container_width=True):
            result = place_order_simulated(ticker, "SELL", 10)
            st.session_state.order_message = result["message"]

    # ── Analysis summary box (shown when AI Analysis clicked) ──
    if st.session_state.show_analysis and st.session_state.analysis_result:
        result = st.session_state.analysis_result
        st.markdown("#### \U0001f9ee Quant Analysis")
        st.info(result["quant"])
        st.markdown("#### \U0001f4ca Technical Analysis")
        st.info(result["technical"])
        st.markdown("#### \U0001f4cb Overall Summary")
        st.success(result["summary"])

    # ── Voice audio player ──
    if st.session_state.voice_generated:
        st.audio(st.session_state.voice_generated, format="audio/mp3")

    # -- Order message (sandbox) --
    if st.session_state.order_message:
        st.info(f"\U0001f7e0 {st.session_state.order_message}")

    # -- Backtest results --
    if st.session_state.backtest_result:
        bt = st.session_state.backtest_result
        st.markdown("#### \U0001f4c8 Backtest Results (1 year, sandbox simulation)")

        bt_col1, bt_col2, bt_col3, bt_col4 = st.columns(4)
        with bt_col1:
            st.metric("Final Equity", f"\u20b9{bt['final_equity']:,.2f}")
        with bt_col2:
            st.metric("Total Return", f"{bt['total_return_pct']:+.2f}%")
        with bt_col3:
            st.metric("Max Drawdown", f"{bt['max_drawdown_pct']:.2f}%")
        with bt_col4:
            st.metric("Win Rate", f"{bt['win_rate_pct']:.1f}%")

        st.caption(f"{bt['total_trades']} total trades simulated. Initial cash: \u20b9{bt['initial_cash']:,.0f}. Historical simulation, not a guarantee of future results.")

        st.plotly_chart(equity_curve_chart(bt["equity_curve"], theme), use_container_width=True)

        if bt["trades"]:
            st.markdown("##### Last 20 Trades")
            trades_df = pd.DataFrame(bt["trades"])
            st.dataframe(trades_df, use_container_width=True, hide_index=True)


    # ── Verdict banner ──
    verdict_bg = "#1a4d2e" if "Bullish" in analysis["verdict"] else "#4d1a1a" if "Bearish" in analysis["verdict"] else "#333"
    st.markdown(f"""
    <div style='padding:12px 18px;border-radius:10px;background:{verdict_bg};color:#fff;text-align:center;font-size:1.1rem;font-weight:600;margin:8px 0;'>
        {analysis['verdict']} &nbsp;|&nbsp; Bullish: {analysis['bull_signals']} &nbsp;\u00b7&nbsp; Bearish: {analysis['bear_signals']}
    </div>
    """, unsafe_allow_html=True)
    # ── Main chart - Plotly candlestick (scroll to zoom like photo) ──
    st.plotly_chart(
        candlestick_chart(df, analysis, True, True, True, theme),
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False,
            "responsive": True,
            "modeBarButtonsToAdd": ["drawline", "drawopenpath", "drawrect", "eraseshape"],
            "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
        },
    )
    # ── Top metrics row ──
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    with col_m1:
        st.metric("Period Change", f"{analysis['change_pct']:+.2f}%", f"over {len(df)} candles")
    with col_m2:
        rsi_val = analysis["last_rsi"]
        st.metric("RSI (14)", f"{rsi_val:.1f}" if rsi_val is not None else "\u2014")
    with col_m3:
        st.metric("Volume", fmt_vol(df["volume"].iloc[-1]) if "volume" in df.columns else "\u2014",
                  f"{analysis['vol_ratio']:.2f}\u00d7 avg" if "volume" in df.columns else "")
    with col_m4:
        st.metric("Volatility (ann.)", f"{analysis['annualized_vol']}%")
    with col_m5:
        st.metric("Sharpe Ratio", f"{analysis['sharpe']}")

    # Golden/Death Cross alert
    if analysis.get("golden_cross"):
        st.success("❤️ GOLDEN CROSS detected! SMA50 crossed above SMA200 — strong bullish signal.")
    elif analysis.get("death_cross"):
        st.error("⚰️ DEATH CROSS detected! SMA50 crossed below SMA200 — strong bearish signal.")
    # Skewness/Kurtosis info
    sk = analysis.get("skewness", 0)
    ku = analysis.get("kurtosis", 0)
    so = analysis.get("sortino", 0)
    sk_msg = "right-skewed (more big gains)" if sk > 0.5 else "left-skewed (more big losses)" if sk < -0.5 else "symmetric"
    ku_msg = "fat tails (extreme moves likely)" if ku > 3 else "thin tails" if ku < 0 else "normal distribution"
    st.info(f"Sortino: {so} | Skewness: {sk} ({sk_msg}) | Kurtosis: {ku} ({ku_msg})")

    # ── Two-column: Indicators + Patterns ──
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### \U0001f4cb Technical Indicators")
        ind_data = {
            "Indicator": ["SMA 20", "SMA 50", "RSI (14)", "MACD Line", "MACD Signal",
                          "MACD Histogram", "BB Upper", "BB Lower",
                          "Support (20d low)", "Resistance (20d high)",
                          "Resistance Trend Slope", "Support Trend Slope",
                          "Golden Cross", "Death Cross",
                          "SMA 200", "Avg Volume (20d)", "Volume Ratio",
                          "Annualized Volatility", "Sharpe Ratio",
                          "Sortino Ratio", "Skewness", "Kurtosis"],
            "Value": [
                fmt_num(analysis["last_sma20"]), fmt_num(analysis["last_sma50"]),
                f"{analysis['last_rsi']:.2f}" if analysis["last_rsi"] is not None else "\u2014",
                fmt_num(analysis["last_macd"]), fmt_num(analysis["last_signal"]),
                fmt_num(analysis["last_hist"]),
                fmt_num(analysis["bb_upper"]), fmt_num(analysis["bb_lower"]),
                f"\u20b9{analysis['support']}", f"\u20b9{analysis['resistance']}",
                f"{analysis['res_trend']['slope']:+.4f}" if analysis.get('res_trend') else "\u2014",
                f"{analysis['sup_trend']['slope']:+.4f}" if analysis.get('sup_trend') else "\u2014",
                fmt_vol(analysis["avg_vol"]), f"{analysis['vol_ratio']}\u00d7",
                "Yes ❤️" if analysis.get("golden_cross") else "No",
                "Yes ⚰️" if analysis.get("death_cross") else "No",
                fmt_num(analysis.get("last_sma200")) if analysis.get("last_sma200") else "—",
                fmt_vol(analysis["avg_vol"]), f"{analysis['vol_ratio']}×",
                f"{analysis['annualized_vol']}%", f"{analysis['sharpe']}",
                f"{analysis.get('sortino', 0)}",
                f"{analysis.get('skewness', 0)}",
                f"{analysis.get('kurtosis', 0)}",
            ],
        }
        st.dataframe(pd.DataFrame(ind_data), use_container_width=True, hide_index=True)

        # Raw data table
        st.markdown("---")
        st.markdown("#### \U0001f4cb Recent Candle Data")
        display_df = df[["date", "open", "high", "low", "close"]].copy()
        if "volume" in df.columns:
            display_df["volume"] = df["volume"].apply(fmt_vol)
        display_df.columns = ["Date", "Open", "High", "Low", "Close"] + (["Volume"] if "volume" in df.columns else [])
        display_df["Date"] = pd.to_datetime(display_df["Date"]).dt.strftime("%Y-%m-%d")
        st.dataframe(display_df.tail(30), use_container_width=True, hide_index=True)

    with col_right:
        st.markdown("#### \U0001f50d Candlestick Patterns")
        for p in analysis["patterns"]:
            st.markdown(f"- {p}")

        st.markdown("#### \U0001f4d0 Pivot Points & Trend Lines")
        pv = analysis.get("pivots", {"highs": [], "lows": []})
        st.markdown(f"**Pivot Highs:** {len(pv['highs'])} \u00b7 **Pivot Lows:** {len(pv['lows'])}")
        if analysis.get("res_trend"):
            st.markdown(f"- \U0001f534 Resistance trend slope: `{analysis['res_trend']['slope']:+.4f}`")
        if analysis.get("sup_trend"):
            st.markdown(f"- \U0001f7e2 Support trend slope: `{analysis['sup_trend']['slope']:+.4f}`")
        if not analysis.get("res_trend") and not analysis.get("sup_trend"):
            st.markdown("- Not enough pivot points for trend lines")

        st.markdown("#### \U0001f4ca Signal Summary")
        sig_df = pd.DataFrame({
            "Type": ["\U0001f7e2 Bullish", "\U0001f534 Bearish", "\u2696\ufe0f Net"],
            "Count": [analysis["bull_signals"], analysis["bear_signals"],
                      analysis["bull_signals"] - analysis["bear_signals"]],
        })
        st.dataframe(sig_df, use_container_width=True, hide_index=True)

    # ── TradingView chart with fullscreen (collapsible) ──
    st.markdown("---")
    with st.expander("TradingView Live Chart (native zoom + fullscreen)"):
        fs_col1, fs_col2 = st.columns([4, 1])
        with fs_col2:
            if st.button("\U0001f5fa\ufe0f Open Fullscreen", key="tv_fs", use_container_width=True):
                st.session_state["tv_fullscreen"] = not st.session_state.get("tv_fullscreen", False)
        if st.session_state.get("tv_fullscreen", False):
            render_tradingview_fullscreen(asset.get("tv", ticker), theme)
        else:
            render_tradingview(asset.get("tv", ticker), theme, height=600)
# ── Footer ──
st.markdown("---")
footer_col1, footer_col2 = st.columns([3, 1])
with footer_col1:
    st.caption("Quant Desk -- Signal Engine + Backtester + Broker Sandbox | Streamlit + Plotly + yfinance | Not financial advice")
with footer_col2:
    st.caption("Powered by [TradingView](https://www.tradingview.com)")

