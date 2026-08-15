"""FinSage AI - Advanced Analysis Module
Chart photo upload, 30-day Monte Carlo, ML predictions (Logistic + Random Forest),
AI auto-strategy, Fibonacci levels, Golden/Death Cross, Candlestick patterns,
comprehensive technical + quant analysis with skewness/kurtosis.
"""

import streamlit as st
import yfinance as yf
from modules.data_fetch import get_history
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math


# ── Indicator helpers ──
def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def _sma(s, n):
    return s.rolling(n).mean()

def _rsi(s, n=14):
    d = s.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
    ag = g.ewm(com=n-1, min_periods=n).mean()
    al = l.ewm(com=n-1, min_periods=n).mean()
    return 100 - 100/(1 + ag/al.replace(0, np.nan))

def _macd(s, f=12, sl=26, sig=9):
    m = _ema(s, f) - _ema(s, sl)
    return m, _ema(m, sig)

def _bb(s, n=20, k=2):
    m = s.rolling(n).mean(); sd = s.rolling(n).std()
    return m + k*sd, m, m - k*sd

def _atr(h, l, c, n=14):
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(com=n-1, min_periods=n).mean()

def _obv(close, vol):
    direction = np.sign(close.diff()).fillna(0)
    return (direction * vol).cumsum()

def _vwap(h, l, c, v):
    tp = (h + l + c) / 3
    return (tp * v).cumsum() / v.cumsum()

def _stochastic(high, low, close, period=14, smooth_k=3, smooth_d=3):
    """%K / %D stochastic oscillator."""
    lowest = low.rolling(period).min()
    highest = high.rolling(period).max()
    rng = (highest - lowest).replace(0, np.nan)
    raw_k = ((close - lowest) / rng * 100).fillna(50)
    k = raw_k.rolling(smooth_k).mean()
    d = k.rolling(smooth_d).mean()
    return k, d


def _composite_signal_score(close, sma_short, sma_long, rsi_arr, macd_line, signal_line, hist, bb_upper, bb_lower, stoch_k):
    """TradingView-style composite bull/bear score (0-100) from a weighted blend of
    MA Cross, RSI, MACD, Bollinger Bands, Stochastic and 10-bar momentum (ROC)."""
    signals = []
    bull_points = 0.0
    total_points = 0.0

    def push(name, verdict, weight, detail):
        nonlocal bull_points, total_points
        signals.append({"name": name, "verdict": verdict, "detail": detail})
        total_points += weight
        if verdict == "bullish":
            bull_points += weight
        elif verdict == "neutral":
            bull_points += weight / 2

    def last_val(series):
        try:
            x = series.iloc[-1]
            return None if pd.isna(x) else float(x)
        except Exception:
            return None

    ss, sl_ = last_val(sma_short), last_val(sma_long)
    if ss is not None and sl_ is not None:
        bullish = ss > sl_
        push("MA Cross", "bullish" if bullish else "bearish", 2,
             "Short MA above long MA — uptrend intact" if bullish else "Short MA below long MA — downtrend intact")

    rv = last_val(rsi_arr)
    if rv is not None:
        if rv > 70:
            push("RSI (14)", "bearish", 1.5, f"RSI {rv:.1f} — overbought")
        elif rv < 30:
            push("RSI (14)", "bullish", 1.5, f"RSI {rv:.1f} — oversold, rebound potential")
        else:
            push("RSI (14)", "neutral", 1.5, f"RSI {rv:.1f} — neutral zone")

    ml, sg = last_val(macd_line), last_val(signal_line)
    if ml is not None and sg is not None:
        bullish = ml > sg
        h_now = last_val(hist)
        h_prev = None
        try:
            if len(hist) > 1 and not pd.isna(hist.iloc[-2]):
                h_prev = float(hist.iloc[-2])
        except Exception:
            pass
        rising = h_now is not None and h_prev is not None and h_now > h_prev
        push("MACD", "bullish" if bullish else "bearish", 2,
             f"MACD line {'above' if bullish else 'below'} signal, histogram {'expanding' if rising else 'contracting'}")

    bu, bl = last_val(bb_upper), last_val(bb_lower)
    price = float(close.iloc[-1])
    if bu is not None and bl is not None and bu != bl:
        pos = (price - bl) / (bu - bl)
        if pos > 0.95:
            push("Bollinger Bands", "bearish", 1, "Price pressing upper band — stretched")
        elif pos < 0.05:
            push("Bollinger Bands", "bullish", 1, "Price pressing lower band — mean-reversion setup")
        else:
            push("Bollinger Bands", "neutral", 1, "Price mid-band, no extreme")

    kv = last_val(stoch_k)
    if kv is not None:
        if kv > 80:
            push("Stochastic (14,3)", "bearish", 1, f"%K {kv:.1f} — overbought")
        elif kv < 20:
            push("Stochastic (14,3)", "bullish", 1, f"%K {kv:.1f} — oversold")
        else:
            push("Stochastic (14,3)", "neutral", 1, f"%K {kv:.1f} — mid-range")

    if len(close) >= 11:
        roc = (float(close.iloc[-1]) - float(close.iloc[-11])) / float(close.iloc[-11]) * 100
        verdict = "bullish" if roc > 0.5 else "bearish" if roc < -0.5 else "neutral"
        push("Momentum (ROC-10)", verdict, 1.5, f"{'+' if roc >= 0 else ''}{roc:.2f}% over 10 bars")

    score = round((bull_points / total_points) * 100) if total_points > 0 else 50
    return score, signals


def _find_entry_exit_points(df, sma_short, sma_long, rsi_arr):
    """Rule-based long entry/exit swing points: MA cross confirmed by RSI."""
    points = []
    in_position = False
    for i in range(1, len(df)):
        s0, s1 = sma_short.iloc[i - 1], sma_short.iloc[i]
        l0, l1 = sma_long.iloc[i - 1], sma_long.iloc[i]
        if pd.isna(s0) or pd.isna(s1) or pd.isna(l0) or pd.isna(l1):
            continue
        crossed_up = s0 <= l0 and s1 > l1
        crossed_down = s0 >= l0 and s1 < l1
        r = rsi_arr.iloc[i]
        r = None if pd.isna(r) else float(r)
        if not in_position and crossed_up and (r is None or r < 65):
            points.append({"i": i, "type": "entry", "price": float(df["close"].iloc[i]), "date": df["date"].iloc[i]})
            in_position = True
        elif in_position and crossed_down:
            points.append({"i": i, "type": "exit", "price": float(df["close"].iloc[i]), "date": df["date"].iloc[i]})
            in_position = False
    return points


def _signal_gauge_chart(score):
    """TradingView-style bull/bear gauge for the composite signal score."""
    label = "BULLISH" if score >= 65 else "BEARISH" if score <= 35 else "NEUTRAL"
    bar_color = "#26a69a" if score >= 65 else "#ef5350" if score <= 35 else "#ff9800"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"size": 34, "color": bar_color}},
        title={"text": f"Signal Score — {label}", "font": {"size": 13}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": bar_color, "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 35], "color": "rgba(239,83,80,0.30)"},
                {"range": [35, 65], "color": "rgba(255,152,0,0.25)"},
                {"range": [65, 100], "color": "rgba(38,166,154,0.30)"},
            ],
            "threshold": {"line": {"color": "#fff", "width": 3}, "thickness": 0.85, "value": score}},
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=10),
                       paper_bgcolor="rgba(0,0,0,0)", font={"color": "#c9d1d9"})
    return fig


def _fibonacci_levels(df, lookback=100):
    recent = df.tail(lookback)
    swing_high = float(recent["high"].max())
    swing_low = float(recent["low"].min())
    diff = swing_high - swing_low
    return {
        "0.0%": swing_high, "23.6%": swing_high - 0.236 * diff,
        "38.2%": swing_high - 0.382 * diff, "50.0%": swing_high - 0.5 * diff,
        "61.8%": swing_high - 0.618 * diff, "100.0%": swing_low}

def _find_support_resistance(df, window=20):
    highs = df["high"].rolling(window, center=True).max()
    lows = df["low"].rolling(window, center=True).min()
    swing_highs = df["high"][(df["high"] == highs) & (df["high"].notna())]
    swing_lows = df["low"][(df["low"] == lows) & (df["low"].notna())]
    def cluster(levels, tol=0.01):
        sorted_l = sorted(levels.dropna().tolist())
        clusters = []
        for lvl in sorted_l:
            if clusters and abs(lvl - clusters[-1][-1]) / clusters[-1][-1] < tol:
                clusters[-1].append(lvl)
            else:
                clusters.append([lvl])
        return [round(np.mean(c), 2) for c in clusters]
    return cluster(swing_lows), cluster(swing_highs)

def _sharpe_ratio(returns, rf=0.06):
    excess = returns.mean() * 252 - rf
    std = returns.std() * np.sqrt(252)
    return excess / std if std > 0 else 0

def _sortino_ratio(returns, rf=0.06):
    downside = returns[returns < 0]
    ds = downside.std() * np.sqrt(252) if len(downside) > 0 else 0
    excess = returns.mean() * 252 - rf
    return excess / ds if ds > 0 else 0

def _max_drawdown(close):
    cum = (1 + close.pct_change()).cumprod()
    running_max = cum.cummax()
    dd = (cum - running_max) / running_max
    return float(dd.min())

def _var(returns, conf=0.95):
    return float(np.percentile(returns.dropna(), (1 - conf) * 100))


# ── NEW: Golden/Death Cross detection ──
def _golden_death_cross(sma50, sma200, dates=None):
    """Detect Golden Cross (SMA50 crosses above SMA200) and Death Cross (below)."""
    signals = pd.Series(0, index=sma50.index)
    golden = (sma50 > sma200) & (sma50.shift(1) <= sma200.shift(1))
    death = (sma50 < sma200) & (sma50.shift(1) >= sma200.shift(1))
    signals[golden] = 1
    signals[death] = -1
    # Find recent crosses — map integer indices to actual dates if provided
    golden_idx = sma50.index[golden.fillna(False)]
    death_idx = sma50.index[death.fillna(False)]
    if dates is not None:
        golden_dates = [dates.iloc[int(i)] if isinstance(i, (int, np.integer)) else pd.Timestamp(i) for i in golden_idx[-3:]]
        death_dates = [dates.iloc[int(i)] if isinstance(i, (int, np.integer)) else pd.Timestamp(i) for i in death_idx[-3:]]
    else:
        golden_dates = [pd.Timestamp(i) for i in golden_idx[-3:]]
        death_dates = [pd.Timestamp(i) for i in death_idx[-3:]]
    return signals, golden_dates, death_dates


# ── NEW: Candlestick pattern detection ──
def _detect_candlestick_patterns(df):
    """Detect Doji, Hammer, Shooting Star, Bullish/Bearish Engulfing patterns."""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    body = (c - o).abs()
    range_ = h - l
    upper_wick = h - pd.concat([o, c], axis=1).max(axis=1)
    lower_wick = pd.concat([o, c], axis=1).min(axis=1) - l

    patterns = pd.Series("", index=df.index)

    # Doji: very small body relative to range
    is_doji = body <= 0.1 * range_
    patterns[is_doji] += "Doji;"

    # Hammer: small body, long lower wick, little/no upper wick
    is_hammer = (lower_wick >= 2 * body) & (upper_wick <= 0.3 * body) & (body > 0)
    patterns[is_hammer] += "Hammer;"

    # Shooting Star: small body, long upper wick, little/no lower wick
    is_shooting_star = (upper_wick >= 2 * body) & (lower_wick <= 0.3 * body) & (body > 0)
    patterns[is_shooting_star] += "Shooting Star;"

    # Bullish Engulfing
    prev_open, prev_close = o.shift(1), c.shift(1)
    bullish_engulf = (
        (prev_close < prev_open) & (c > o) & (o <= prev_close) & (c >= prev_open)
    )
    patterns[bullish_engulf] += "Bullish Engulfing;"

    # Bearish Engulfing
    bearish_engulf = (
        (prev_close > prev_open) & (c < o) & (o >= prev_close) & (c <= prev_open)
    )
    patterns[bearish_engulf] += "Bearish Engulfing;"

    return patterns


# ── NEW: Returns statistics with skewness and kurtosis ──
def _returns_stats(returns):
    """Compute comprehensive return statistics including skewness and kurtosis."""
    mean_r = float(returns.mean())
    std_r = float(returns.std())
    # Skewness: measure of asymmetry
    n = len(returns)
    skew = float(n / ((n-1)*(n-2)) * np.sum(((returns - mean_r) / std_r) ** 3)) if std_r > 0 and n > 2 else 0
    # Kurtosis (excess): measure of tail thickness
    kurt = float(n*(n+1) / ((n-1)*(n-2)*(n-3)) * np.sum(((returns - mean_r) / std_r) ** 4) - 3*(n-1)**2/((n-2)*(n-3))) if std_r > 0 and n > 3 else 0
    return {
        "Mean Daily Return": mean_r,
        "Std Dev (Volatility)": std_r,
        "Annualized Volatility": std_r * np.sqrt(252),
        "Skewness": skew,
        "Kurtosis": kurt,
        "Annualized Return": (1 + mean_r) ** 252 - 1}


# ── NEW: Simple Random Forest (pure numpy decision trees) ──
def _gini(y):
    if len(y) == 0: return 0
    probs = np.bincount(y, minlength=2) / max(len(y), 1)
    return 1 - np.sum(probs ** 2)

def _best_split(X, y, feature_indices, n_candidates=10):
    """Find the best split for a decision tree node."""
    best_gini = _gini(y)
    best_feat, best_thresh = None, None
    n = len(y)
    for feat in feature_indices:
        col = X[:, feat]
        if n > n_candidates:
            thresholds = np.linspace(col.min(), col.max(), n_candidates + 1)[1:-1]
        else:
            thresholds = np.unique(col)[:-1]
        for thresh in thresholds:
            left = y[col <= thresh]
            right = y[col > thresh]
            if len(left) == 0 or len(right) == 0:
                continue
            g = (len(left) * _gini(left) + len(right) * _gini(right)) / n
            if g < best_gini:
                best_gini = g
                best_feat = feat
                best_thresh = thresh
    return best_feat, best_thresh

def _build_tree(X, y, feature_indices, depth=0, max_depth=5, min_samples=5):
    """Build a single decision tree."""
    if depth >= max_depth or len(y) < min_samples or len(np.unique(y)) == 1:
        probs = np.bincount(y, minlength=2) / len(y) if len(y) > 0 else np.array([0.5, 0.5])
        return {"leaf": True, "probs": probs}
    feat, thresh = _best_split(X, y, feature_indices)
    if feat is None:
        probs = np.bincount(y, minlength=2) / len(y) if len(y) > 0 else np.array([0.5, 0.5])
        return {"leaf": True, "probs": probs}
    left_mask = X[:, feat] <= thresh
    return {
        "leaf": False, "feat": feat, "thresh": thresh,
        "left": _build_tree(X[left_mask], y[left_mask], feature_indices, depth+1, max_depth, min_samples),
        "right": _build_tree(X[~left_mask], y[~left_mask], feature_indices, depth+1, max_depth, min_samples)}

def _predict_tree(tree, X):
    if tree["leaf"]:
        return tree["probs"]
    pred = np.zeros((len(X), 2))
    left_mask = X[:, tree["feat"]] <= tree["thresh"]
    pred[left_mask] = _predict_tree(tree["left"], X[left_mask])
    pred[~left_mask] = _predict_tree(tree["right"], X[~left_mask])
    return pred

def _train_random_forest(X, y, n_trees=50, max_depth=5, n_features=None, seed=42):
    """Simple Random Forest using pure numpy decision trees."""
    rng = np.random.default_rng(seed)
    n, d = X.shape
    if n_features is None:
        n_features = max(1, int(np.sqrt(d)))
    trees = []
    for t in range(n_trees):
        # Bootstrap sample
        idx = rng.integers(0, n, size=n)
        X_boot, y_boot = X[idx], y[idx]
        # Random feature subset
        feat_idx = rng.choice(d, size=min(n_features, d), replace=False)
        tree = _build_tree(X_boot, y_boot, feat_idx, max_depth=max_depth)
        trees.append(tree)
    return trees

def _predict_random_forest(trees, X):
    preds = np.zeros((len(X), 2))
    for tree in trees:
        preds += _predict_tree(tree, X)
    return preds / max(len(trees), 1)

def _random_forest_importance(trees, n_features):
    """Compute feature importance from the random forest."""
    importance = np.zeros(n_features)
    for tree in trees:
        if not tree["leaf"]:
            importance[tree["feat"]] += 1
            _collect_importance(tree, importance)
    total = importance.sum()
    return importance / total if total > 0 else importance

def _collect_importance(node, importance):
    """Recursively collect feature usage count."""
    if node["leaf"]:
        return
    importance[node["feat"]] += 1
    _collect_importance(node["left"], importance)
    _collect_importance(node["right"], importance)


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_data(sym, period="5y"):
    df, is_synthetic = get_history(sym, period=period, interval="1d")
    if df is None or df.empty:
        return None
    df = df.reset_index()
    date_col = "Date" if "Date" in df.columns else df.columns[0]
    df = df.rename(columns={date_col: "date", "Open": "open", "High": "high",
                            "Low": "low", "Close": "close", "Volume": "volume"})
    df["date"] = pd.to_datetime(df["date"])
    df.attrs["synthetic"] = is_synthetic
    return df


# ═══ 1. PHOTO UPLOAD → REAL CHART ═══
def _render_photo_upload():
    st.markdown("### \U0001f4f8 Chart Photo \u2192 Real Chart")
    st.caption("Upload any chart screenshot. Enter the symbol shown on it to load real data with full analysis.")
    uploaded = st.file_uploader("Upload chart screenshot/photo", type=["png", "jpg", "jpeg", "webp"], key="chart_photo_upload")
    if uploaded:
        col_photo, col_chart = st.columns([1, 2])
        with col_photo:
            st.markdown("**\U0001f4f7 Uploaded Chart:**")
            st.image(uploaded, use_container_width=True)
            sym_input = st.text_input("Symbol visible on chart (e.g. RELIANCE.NS, AAPL, BTC-USD)",
                key="photo_chart_sym", placeholder="Type the ticker you see on the chart...")
            period = st.selectbox("Data Period", ["6mo", "1y", "2y", "5y", "10y"], index=3, key="photo_chart_period")
            if st.button("\U0001f50d Load Real Chart", type="primary", key="photo_load_btn"):
                if sym_input.strip():
                    st.session_state["photo_sym"] = sym_input.strip().upper()
                    st.session_state["photo_period"] = period
                    st.rerun()
                else:
                    st.warning("Please enter the symbol visible on the chart.")
        with col_chart:
            sym = st.session_state.get("photo_sym", "")
            if sym:
                df = _fetch_data(sym, st.session_state.get("photo_period", "1y"))
                if df is not None and df.attrs.get("synthetic"):
                    st.caption("\u26a0\ufe0f Live feed rate-limited \u2014 showing simulated candles.")
                if df is not None and len(df) > 10:
                    _render_full_analysis(df, sym)
                else:
                    st.error(f"Could not fetch data for {sym}. Try a different symbol.")
            else:
                st.info("Upload a chart photo and enter the symbol to see real-time analysis here.")
    else:
        st.info("\U0001f4f7 Upload a chart screenshot to get started. Enter the symbol shown on it to load the real chart with full analysis.")


# ═══ 2. FULL TECHNICAL + QUANT ANALYSIS ═══
def _render_full_analysis(df, sym=""):
    st.markdown("v3.2")
    close = df["close"]; high = df["high"]; low = df["low"]
    vol = df.get("volume", pd.Series(0, index=df.index))
    sma50 = _sma(close, 50); sma200 = _sma(close, 200); ema20 = _ema(close, 20)
    rsi = _rsi(close); macd, macd_sig = _macd(close); macd_hist = macd - macd_sig
    bb_u, bb_m, bb_l = _bb(close); atr_val = _atr(high, low, close)
    obv = _obv(close, vol); fib = _fibonacci_levels(df)
    sup_levels, res_levels = _find_support_resistance(df)
    # NEW: Golden/Death Cross + Candlestick patterns
    cross_signals, golden_dates, death_dates = _golden_death_cross(sma50, sma200, df["date"])
    candle_patterns = _detect_candlestick_patterns(df)
    # NEW: Stochastic oscillator + composite signal score + entry/exit markers
    stoch_k, stoch_d = _stochastic(high, low, close)
    signal_score, signal_breakdown = _composite_signal_score(
        close, ema20, sma50, rsi, macd, macd_sig, macd_hist, bb_u, bb_l, stoch_k)
    entry_exit_points = _find_entry_exit_points(df, ema20, sma50, rsi)

    last = df.iloc[-1]; last_close = float(last["close"])
    last_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
    last_macd = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0
    last_sig = float(macd_sig.iloc[-1]) if not pd.isna(macd_sig.iloc[-1]) else 0
    last_atr = float(atr_val.iloc[-1]) if not pd.isna(atr_val.iloc[-1]) else 0
    last_sma50 = float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else last_close
    last_sma200 = float(sma200.iloc[-1]) if not pd.isna(sma200.iloc[-1]) else last_close

    # Cross status
    cross_status = "Golden Cross \u2764\ufe0f" if last_sma50 > last_sma200 else "Death Cross \u26b0\ufe0f" if last_sma50 < last_sma200 else "No Cross"

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Price", f"\u20b9{last_close:.2f}")
    m2.metric("RSI", f"{last_rsi:.1f}", "Overbought" if last_rsi > 70 else "Oversold" if last_rsi < 30 else "Neutral")
    m3.metric("MACD", f"{last_macd:.2f}", "Bullish" if last_macd > last_sig else "Bearish")
    m4.metric("ATR", f"{last_atr:.2f}")
    m5.metric("Trend", "Up" if last_close > last_sma50 > last_sma200 else "Down" if last_close < last_sma50 < last_sma200 else "Mixed")
    m6.metric("Cross", cross_status, "Bullish" if last_sma50 > last_sma200 else "Bearish")

    try:
    # NEW: Golden/Death Cross recent signals
        if golden_dates or death_dates:
            st.markdown("**\u2747\ufe0f Recent Golden/Death Cross Signals:**")
            cross_msgs = []
            for d in golden_dates:
                cross_msgs.append(f"\U0001f7e2 Golden Cross on {d.strftime('%Y-%m-%d')} \u2014 SMA50 crossed above SMA200 (Bullish)")
            for d in death_dates:
                cross_msgs.append(f"\U0001f534 Death Cross on {d.strftime('%Y-%m-%d')} \u2014 SMA50 crossed below SMA200 (Bearish)")
            for msg in cross_msgs:
                st.markdown(f"- {msg}")
    
    except Exception as cross_err:
        st.error(f"Golden/Death Cross display error: {type(cross_err).__name__}: {cross_err}")
        import traceback as _tb; st.text(_tb.format_exc())

    try:
        st.markdown(f"#### \U0001f4ca {sym} \u2014 Technical Analysis Chart")
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04,
            row_heights=[0.48, 0.15, 0.17, 0.16],
            subplot_titles=("Price + SMA + BB + Fibonacci + Entry/Exit", "Volume + OBV", "RSI + MACD", "Stochastic (14,3)"))
        fig.add_trace(go.Candlestick(x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
            name="OHLC", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
            increasing_fillcolor="#26a69a", decreasing_fillcolor="#ef5350", line_width=2, whiskerwidth=0.3), row=1, col=1)
        if entry_exit_points:
            entries = [p for p in entry_exit_points if p["type"] == "entry"]
            exits = [p for p in entry_exit_points if p["type"] == "exit"]
            if entries:
                fig.add_trace(go.Scatter(
                    x=[p["date"] for p in entries], y=[p["price"] * 0.985 for p in entries],
                    mode="markers+text", text=["BUY"] * len(entries), textposition="bottom center",
                    textfont=dict(size=9, color="#26a69a", family="Trebuchet MS, sans-serif"),
                    marker=dict(symbol="triangle-up", size=11, color="#26a69a", line=dict(color="#0d3b30", width=1)),
                    name="Entry (BUY)", hovertext=[f"BUY @ {p['price']:.2f}" for p in entries], hoverinfo="text",
                ), row=1, col=1)
            if exits:
                fig.add_trace(go.Scatter(
                    x=[p["date"] for p in exits], y=[p["price"] * 1.015 for p in exits],
                    mode="markers+text", text=["SELL"] * len(exits), textposition="top center",
                    textfont=dict(size=9, color="#ef5350", family="Trebuchet MS, sans-serif"),
                    marker=dict(symbol="triangle-down", size=11, color="#ef5350", line=dict(color="#4a1414", width=1)),
                    name="Exit (SELL)", hovertext=[f"SELL @ {p['price']:.2f}" for p in exits], hoverinfo="text",
                ), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=sma50, name="SMA 50", line=dict(color="#2962ff", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=sma200, name="SMA 200", line=dict(color="#ff9800", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=ema20, name="EMA 20", line=dict(color="#e91e63", width=1.2), opacity=0.7), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=bb_u, name="BB Upper", line=dict(color="#9575cd", width=1, dash="dot"), opacity=0.5, showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=bb_l, name="BB Lower", line=dict(color="#9575cd", width=1, dash="dot"), opacity=0.5, showlegend=False), row=1, col=1)
        # Volume Profile (horizontal histogram on right side)
        try:
            _close_arr = df["close"].values
            _vol_arr = df["volume"].values if "volume" in df.columns else vol.values if 'vol' in dir() else None
            if _vol_arr is not None and len(_close_arr) > 20:
                import numpy as _np
                _n_bins = min(30, max(10, len(_close_arr) // 5))
                _pmin, _pmax = float(_np.min(_close_arr)), float(_np.max(_close_arr))
                _edges = _np.linspace(_pmin, _pmax, _n_bins + 1)
                _vp = _np.zeros(_n_bins)
                for _j in range(len(_close_arr)):
                    _idx = min(int((_close_arr[_j] - _pmin) / (_pmax - _pmin) * _n_bins), _n_bins - 1)
                    if _idx >= 0:
                        _vp[_idx] += _vol_arr[_j]
                _max_vp = _vp.max() if _vp.max() > 0 else 1
                _x_range_ms = (df["date"].iloc[-1] - df["date"].iloc[0]).total_seconds() * 1000
                _bar_w_ms = int(_x_range_ms * 0.12)
                for _j in range(_n_bins):
                    if _vp[_j] > 0:
                        fig.add_shape(type="rect", xref="x", yref="y",
                            x0=df["date"].iloc[-1], x1=df["date"].iloc[-1] + pd.Timedelta(milliseconds=int(_bar_w_ms * _vp[_j] / _max_vp)),
                            y0=_edges[_j], y1=_edges[_j+1],
                            fillcolor="rgba(100,181,246,0.25)", line_width=0, row=1, col=1)
        except Exception:
            pass  # volume profile is a nice-to-have
        colors_fib = ["#ef5350", "#ff9800", "#26a69a", "#2962ff", "#ab47bc", "#26a69a"]
        for i, (label, val) in enumerate(fib.items()):
            fig.add_hline(y=val, line_dash="dash", line_color=colors_fib[i], opacity=0.4, line_width=1, row=1, col=1,
                annotation_text=f"Fib {label}: {val:.2f}", annotation_position="top left", annotation_font_size=8, annotation_font_color=colors_fib[i])
        for r in res_levels[-3:]:
            fig.add_hline(y=r, line_dash="solid", line_color="#ef5350", line_width=3, opacity=0.85, row=1, col=1,
                annotation_text=f"\u25cf R: {r:.2f}", annotation_position="top right", annotation_font_size=11, annotation_font_color="#ef5350")
            band_r = abs(r * 0.005)
            fig.add_hrect(y0=r - band_r, y1=r + band_r, fillcolor="rgba(239,83,80,0.12)", line_width=0, row=1, col=1)
        for s in sup_levels[-3:]:
            fig.add_hline(y=s, line_dash="solid", line_color="#26a69a", line_width=3, opacity=0.85, row=1, col=1,
                annotation_text=f"\u25cf S: {s:.2f}", annotation_position="bottom right", annotation_font_size=11, annotation_font_color="#26a69a")
            band_s = abs(s * 0.005)
            fig.add_hrect(y0=s - band_s, y1=s + band_s, fillcolor="rgba(38,166,154,0.12)", line_width=0, row=1, col=1)
        vol_colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(df["close"], df["open"])]
        fig.add_trace(go.Bar(x=df["date"], y=vol, name="Volume", marker_color=vol_colors, opacity=0.5), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=obv, name="OBV", line=dict(color="#ab47bc", width=1.5)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=rsi, name="RSI", line=dict(color="#7e57c2", width=1.8)), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#ef5350", opacity=0.5, row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#26a69a", opacity=0.5, row=3, col=1)
        fig.add_hline(y=50, line_dash="dash", line_color="#78909c", opacity=0.3, row=3, col=1)
        fig.add_trace(go.Bar(x=df["date"], y=macd_hist, name="MACD Hist",
            marker_color=["#26a69a" if h >= 0 else "#ef5350" for h in macd_hist], opacity=0.5), row=3, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=macd, name="MACD", line=dict(color="#2962ff", width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=macd_sig, name="Signal", line=dict(color="#ff9800", width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=stoch_k, name="%K", line=dict(color="#2962ff", width=1.5)), row=4, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=stoch_d, name="%D", line=dict(color="#ff9800", width=1.5)), row=4, col=1)
        fig.add_hline(y=80, line_dash="dot", line_color="#ef5350", opacity=0.5, row=4, col=1)
        fig.add_hline(y=20, line_dash="dot", line_color="#26a69a", opacity=0.5, row=4, col=1)

        fig.update_layout(template="plotly_dark", height=820, margin=dict(l=50, r=60, t=40, b=30),
            xaxis_rangeslider_visible=False, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            font=dict(size=10, family="Trebuchet MS, sans-serif"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            hovermode="x unified",
            dragmode="zoom",
            xaxis=dict(showspikes=True, spikethickness=1, spikedash="solid", spikemode="across", spikecolor="rgba(150,150,150,0.5)"),
            yaxis=dict(showspikes=True, spikethickness=1, spikedash="solid", spikemode="across", spikecolor="rgba(150,150,150,0.5)"))
        fig.update_xaxes(showgrid=False, showline=True, linecolor="rgba(50,50,50,0.3)")
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(50,50,50,0.2)", side="right", showline=True, linecolor="rgba(50,50,50,0.3)")
        fig.update_yaxes(tickformat=".2f", row=1, col=1)
        fig.update_yaxes(range=[0, 100], row=4, col=1)
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
        st.plotly_chart(fig, use_container_width=True, config={
            "scrollZoom": True, "displayModeBar": True, "displaylogo": False, "responsive": True,
            "modeBarButtonsToAdd": ["drawline", "drawopenpath", "drawrect", "drawcircle", "drawarrow", "eraseshape"], "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]})

    except Exception as chart_err:
        st.error(f"Chart error: {type(chart_err).__name__}: {chart_err}")
        import traceback as _tb
        st.text(_tb.format_exc())
        return

    # ── NEW: Composite Signal Score gauge + breakdown ──
    st.markdown("#### \U0001f3af Composite Signal Score")
    gcol1, gcol2 = st.columns([1, 2])
    with gcol1:
        st.plotly_chart(_signal_gauge_chart(signal_score), use_container_width=True, config={"scrollZoom": True, "displayModeBar": True, "modeBarButtonsToAdd": ["drawline", "eraseshape"], "displaylogo": False})
    with gcol2:
        for sig in signal_breakdown:
            icon = "\U0001f7e2" if sig["verdict"] == "bullish" else "\U0001f534" if sig["verdict"] == "bearish" else "\u26aa"
            st.markdown(f"{icon} **{sig['name']}** \u2014 {sig['detail']}")
    if entry_exit_points:
        with st.expander(f"\U0001f4cc Entry/Exit signals detected \u2014 EMA20/SMA50 cross + RSI confirm ({len(entry_exit_points)})"):
            for p in entry_exit_points[-10:]:
                tag = "\U0001f7e2 BUY" if p["type"] == "entry" else "\U0001f534 SELL"
                st.markdown(f"- **{p['date'].strftime('%Y-%m-%d')}** \u2014 {tag} @ \u20b9{p['price']:.2f}")
    else:
        st.caption("No EMA20/SMA50 crossover entry/exit signals in this window yet.")

    # ── NEW: Candlestick Pattern Detection ──
    try:
        st.markdown("#### \U0001f50d Candlestick Patterns (last 10 days)")
        recent_patterns = candle_patterns.tail(10)
        detected = recent_patterns[recent_patterns != ""]
        if len(detected) > 0:
            pattern_meanings = {
                "Doji": "\U0001f7e1 Doji \u2014 indecision, possible reversal",
                "Hammer": "\U0001f7e2 Hammer \u2014 bullish reversal signal",
                "Shooting Star": "\U0001f534 Shooting Star \u2014 bearish reversal signal",
                "Bullish Engulfing": "\U0001f7e2 Bullish Engulfing \u2014 buyers overwhelming sellers",
                "Bearish Engulfing": "\U0001f534 Bearish Engulfing \u2014 sellers overwhelming sellers"}
            for idx, pats in detected.items():
                try:
                    dt = df["date"].iloc[int(idx)] if isinstance(idx, (int, np.integer)) else pd.Timestamp(idx)
                except Exception:
                    dt = pd.Timestamp(idx) if not isinstance(idx, pd.Timestamp) else idx
                date_str = dt.strftime('%Y-%m-%d') if hasattr(dt, 'strftime') else str(dt)
                for pat in pats.rstrip(";").split(";"):
                    pat = pat.strip()
                    if pat in pattern_meanings:
                        st.markdown(f"- **{date_str}**: {pattern_meanings[pat]}")
                    elif pat:
                        st.markdown(f"- **{date_str}**: {pat}")
        else:
            st.markdown("- \u27a1\ufe0f No strong candlestick pattern detected in last 10 days \u2014 trend continuation likely")
    except Exception as candle_err:
        st.error(f"Candlestick pattern error: {type(candle_err).__name__}: {candle_err}")
        import traceback as _tb; st.text(_tb.format_exc())

    except Exception as candle_err:
        st.error(f"Candlestick pattern error: {type(candle_err).__name__}: {candle_err}")
        import traceback as _tb; st.text(_tb.format_exc())

    # ── Quant Analysis with Skewness/Kurtosis ──
    st.markdown("#### \U0001f4c8 Quant Analysis")
    returns = close.pct_change().dropna()
    stats = _returns_stats(returns)
    q1, q2, q3, q4, q5, q6 = st.columns(6)
    q1.metric("Sharpe Ratio", f"{_sharpe_ratio(returns):.2f}")
    q2.metric("Sortino Ratio", f"{_sortino_ratio(returns):.2f}")
    q3.metric("Max Drawdown", f"{_max_drawdown(close)*100:.2f}%")
    q4.metric("VaR (95%)", f"{_var(returns)*100:.2f}%")
    q5.metric("Ann. Volatility", f"{stats['Annualized Volatility']*100:.1f}%")
    q6.metric("Ann. Return", f"{stats['Annualized Return']*100:.1f}%")

    # NEW: Skewness & Kurtosis
    q7, q8, q9, q10 = st.columns(4)
    q7.metric("Mean Daily Return", f"{stats['Mean Daily Return']*100:.3f}%")
    q8.metric("Std Dev (Daily)", f"{stats['Std Dev (Volatility)']*100:.3f}%")
    q9.metric("Skewness", f"{stats['Skewness']:.3f}", "Right-skewed" if stats['Skewness'] > 0.5 else "Left-skewed" if stats['Skewness'] < -0.5 else "Symmetric")
    q10.metric("Kurtosis (excess)", f"{stats['Kurtosis']:.3f}", "Fat tails" if stats['Kurtosis'] > 3 else "Thin tails" if stats['Kurtosis'] < 0 else "Normal")

    st.markdown("#### \U0001f539 Fibonacci Retracement Levels (last 100 days)")
    fib_cols = st.columns(6)
    for i, (label, val) in enumerate(fib.items()):
        with fib_cols[i]: st.metric(f"Fib {label}", f"\u20b9{val:.2f}")

    st.markdown("#### \U0001f4d0 Support & Resistance Levels")
    sr_col1, sr_col2 = st.columns(2)
    with sr_col1:
        st.markdown("**\U0001f7e2 Support Levels:**")
        for s in sup_levels[-5:]: st.markdown(f"- \u20b9{s:.2f}")
    with sr_col2:
        st.markdown("**\U0001f534 Resistance Levels:**")
        for r in res_levels[-5:]: st.markdown(f"- \u20b9{r:.2f}")

    _render_ai_strategy(df, rsi, macd, macd_sig, sup_levels, res_levels, last_rsi, last_close, last_sma50, last_sma200, sym)


# ═══ 3. MONTE CARLO 30-DAY ═══
def _render_monte_carlo(df, sym=""):
    st.markdown("#### \U0001f3b2 30-Day Monte Carlo Simulation")
    st.caption("Simulates 1000 future price paths using Geometric Brownian Motion based on historical returns.")
    close = df["close"]; returns = close.pct_change().dropna()
    mu, sigma = float(returns.mean()), float(returns.std())
    last_price = float(close.iloc[-1])
    n_sims = 1000; n_days = 30; rng = np.random.default_rng(42)
    simulations = np.zeros((n_days + 1, n_sims)); simulations[0] = last_price
    for sim in range(n_sims):
        for d in range(1, n_days + 1):
            simulations[d, sim] = simulations[d-1, sim] * (1 + rng.normal(mu, sigma))
    final_prices = simulations[-1]
    p5 = np.percentile(final_prices, 5); p50 = np.percentile(final_prices, 50); p95 = np.percentile(final_prices, 95)
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Current Price", f"\u20b9{last_price:.2f}")
    mc2.metric("Expected (50th)", f"\u20b9{p50:.2f}", f"{(p50/last_price-1)*100:+.1f}%")
    mc3.metric("Bull Case (95th)", f"\u20b9{p95:.2f}", f"{(p95/last_price-1)*100:+.1f}%")
    mc4.metric("Bear Case (5th)", f"\u20b9{p5:.2f}", f"{(p5/last_price-1)*100:+.1f}%")
    mc5, mc6, mc7, mc8 = st.columns(4)
    mc5.metric("Prob. Profit", f"{(final_prices > last_price).mean()*100:.1f}%")
    mc6.metric("Prob. Loss", f"{(final_prices < last_price).mean()*100:.1f}%")
    mc7.metric("Max Gain", f"+{(final_prices.max()/last_price-1)*100:.1f}%")
    mc8.metric("Max Loss", f"{(final_prices.min()/last_price-1)*100:.1f}%")
    fig = go.Figure()
    for sim in range(min(n_sims, 200)):
        fig.add_trace(go.Scatter(x=list(range(n_days+1)), y=simulations[:, sim], mode="lines",
            line=dict(width=0.3, color="rgba(100,181,246,0.08)"), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=list(range(n_days+1)), y=np.median(simulations, axis=1), name="Median", line=dict(color="#ff9800", width=2.5)))
    fig.add_trace(go.Scatter(x=list(range(n_days+1)), y=np.percentile(simulations, 95, axis=1), name="95th Pct", line=dict(color="#26a69a", width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=list(range(n_days+1)), y=np.percentile(simulations, 5, axis=1), name="5th Pct", line=dict(color="#ef5350", width=2, dash="dash"), fill="tonexty", fillcolor="rgba(38,166,154,0.05)"))
    fig.add_hline(y=last_price, line_dash="solid", line_color="#2962ff", opacity=0.5, annotation_text=f"Current: \u20b9{last_price:.2f}", annotation_position="top left")
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=50, r=60, t=30, b=30),
        hovermode="x unified",
        xaxis_title="Days Ahead", yaxis_title="Price (\u20b9)", showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(size=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        dragmode="zoom")
    fig.update_yaxes(side="right", tickformat=".2f", fixedrange=False, showspikes=True, spikemode="across", spikesnap="cursor", spikecolor="grey", spikethickness=1); fig.update_xaxes(showgrid=False, showspikes=True, spikemode="across", spikesnap="cursor", spikecolor="grey", spikethickness=1)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(50,50,50,0.2)", fixedrange=False)
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToAdd": ["drawline", "drawopenpath", "drawrect", "drawcircle", "drawarrow", "eraseshape"], "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]})


# ═══ 4. ML PREDICTION (Logistic Regression + Random Forest) ═══
def _render_ml_prediction(df, sym=""):
    st.markdown("#### \U0001f916 ML Prediction \u2014 Next Day Direction")
    st.caption("Logistic Regression + Random Forest ensemble trained on technical indicators to predict if price goes UP or DOWN tomorrow.")
    close = df["close"]; high = df["high"]; low = df["low"]
    vol = df.get("volume", pd.Series(0, index=df.index))
    rsi = _rsi(close); macd, macd_sig = _macd(close); macd_hist = macd - macd_sig
    bb_u, bb_m, bb_l = _bb(close); sma50 = _sma(close, 50); sma200 = _sma(close, 200)
    atr_val = _atr(high, low, close)
    features = pd.DataFrame(index=df.index)
    features["ret_1d"] = close.pct_change(); features["ret_5d"] = close.pct_change(5)
    features["rsi"] = rsi; features["macd_hist"] = macd_hist
    features["bb_pos"] = (close - bb_l) / (bb_u - bb_l)
    features["vol_change"] = vol.pct_change() if vol.sum() > 0 else 0
    features["sma_ratio"] = sma50 / sma200; features["atr_pct"] = atr_val / close
    target = (close.shift(-1) > close).astype(int)
    data = features.copy(); data["target"] = target
    data = data.replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 100:
        st.warning("Not enough data for ML prediction."); return
    split = int(len(data) * 0.8)
    X_train = data.iloc[:split].drop(columns=["target"]).values; y_train = data.iloc[:split]["target"].values.astype(int)
    X_test = data.iloc[split:].drop(columns=["target"]).values; y_test = data.iloc[split:]["target"].values.astype(int)
    feature_names = list(features.columns)

    # ── Model 1: Logistic Regression (pure numpy) ──
    def sigmoid(z):
        z = np.clip(z, -500, 500); return 1 / (1 + np.exp(-z))
    n, d = X_train.shape; mu_f = X_train.mean(axis=0); std_f = X_train.std(axis=0) + 1e-8
    Xn = (X_train - mu_f) / std_f; Xn = np.c_[np.ones(n), Xn]; w = np.zeros(d + 1)
    for _ in range(1000):
        pred = sigmoid(Xn @ w); grad = Xn.T @ (pred - y_train) / n; w -= 0.01 * grad
    def predict_logreg(X):
        Xn2 = (X - mu_f) / (std_f + 1e-8); Xn2 = np.c_[np.ones(len(Xn2)), Xn2]; return sigmoid(Xn2 @ w)
    lr_train_acc = ((predict_logreg(X_train) >= 0.5).astype(int) == y_train).mean() * 100
    lr_test_acc = ((predict_logreg(X_test) >= 0.5).astype(int) == y_test).mean() * 100
    lr_importance = np.abs(w[1:])
    lr_importance = lr_importance / lr_importance.sum() if lr_importance.sum() > 0 else lr_importance

    # ── Model 2: Random Forest (pure numpy) ──
    with st.spinner("Training Random Forest (50 trees)..."):
        rf_trees = _train_random_forest(X_train, y_train, n_trees=50, max_depth=5, seed=42)
    rf_train_preds = _predict_random_forest(rf_trees, X_train)
    rf_test_preds = _predict_random_forest(rf_trees, X_test)
    rf_train_acc = ((rf_train_preds[:, 1] >= 0.5).astype(int) == y_train).mean() * 100
    rf_test_acc = ((rf_test_preds[:, 1] >= 0.5).astype(int) == y_test).mean() * 100
    rf_importance = _random_forest_importance(rf_trees, d)

    # ── Ensemble: average of both models ──
    latest_features = features.iloc[-1:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(latest_features) > 0:
        lr_prob = float(predict_logreg(latest_features.values)[0])
        rf_prob = float(_predict_random_forest(rf_trees, latest_features.values)[0, 1])
        # Ensemble: weighted average (RF gets more weight)
        prob_up = 0.35 * lr_prob + 0.65 * rf_prob
        prob_down = 1 - prob_up
        pred_direction = "UP \u2b06\ufe0f" if prob_up >= 0.5 else "DOWN \u2b07\ufe0f"
        confidence = max(prob_up, prob_down) * 100
    else:
        prob_up = prob_down = 0.5; pred_direction = "NEUTRAL"; confidence = 50

    # ── Display: Ensemble results ──
    ml1, ml2, ml3, ml4 = st.columns(4)
    ml1.metric("Prediction (Ensemble)", pred_direction)
    ml2.metric("Confidence", f"{confidence:.1f}%")
    ml3.metric("LR Test Accuracy", f"{lr_test_acc:.1f}%")
    ml4.metric("RF Test Accuracy", f"{rf_test_acc:.1f}%")

    # ── Model comparison ──
    st.markdown("**\U0001f4ca Model Comparison:**")
    comp1, comp2, comp3, comp4 = st.columns(4)
    comp1.metric("LR Train Acc", f"{lr_train_acc:.1f}%")
    comp2.metric("LR Test Acc", f"{lr_test_acc:.1f}%")
    comp3.metric("RF Train Acc", f"{rf_train_acc:.1f}%")
    comp4.metric("RF Test Acc", f"{rf_test_acc:.1f}%")

    # ── Probability bars ──
    prob_col1, prob_col2 = st.columns(2)
    with prob_col1:
        st.markdown(f"<div style='background:#1a2e1a;border:1px solid #26a69a;border-radius:10px;padding:14px;text-align:center;margin:4px;'><div style='color:#26a69a;font-size:12px;'>Probability UP (Ensemble)</div><div style='color:#26a69a;font-size:1.8rem;font-weight:bold;'>{prob_up*100:.1f}%</div><div style='background:#0d1117;border-radius:6px;height:10px;margin-top:8px;overflow:hidden;'><div style='background:#26a69a;height:100%;width:{prob_up*100:.1f}%;border-radius:6px;'></div></div></div>", unsafe_allow_html=True)
    with prob_col2:
        st.markdown(f"<div style='background:#2e1a1a;border:1px solid #ef5350;border-radius:10px;padding:14px;text-align:center;margin:4px;'><div style='color:#ef5350;font-size:12px;'>Probability DOWN (Ensemble)</div><div style='color:#ef5350;font-size:1.8rem;font-weight:bold;'>{prob_down*100:.1f}%</div><div style='background:#0d1117;border-radius:6px;height:10px;margin-top:8px;overflow:hidden;'><div style='background:#ef5350;height:100%;width:{prob_down*100:.1f}%;border-radius:6px;'></div></div></div>", unsafe_allow_html=True)

    # ── Feature importance comparison (LR vs RF) ──
    st.markdown("**\U0001f4ca Feature Importance (LR vs Random Forest):**")
    fig_imp = go.Figure()
    fig_imp.add_trace(go.Bar(x=lr_importance, y=feature_names, orientation="h", name="Logistic Regression",
        marker_color="#2962ff", opacity=0.7, xaxis="x", yaxis="y"))
    fig_imp.add_trace(go.Bar(x=rf_importance, y=feature_names, orientation="h", name="Random Forest",
        marker_color="#ff9800", opacity=0.7, xaxis="x2", yaxis="y2"))
    fig_imp.update_layout(
        template="plotly_dark", height=300, margin=dict(l=0, r=0, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        barmode="group",
        xaxis=dict(title="LR Importance", domain=[0, 0.45]),
        xaxis2=dict(title="RF Importance", domain=[0.55, 1]),
        yaxis2=dict(overlaying="y", side="right"),
    )
    st.plotly_chart(fig_imp, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToAdd": ["drawline", "drawopenpath", "drawrect", "drawcircle", "drawarrow", "eraseshape"], "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]})

    st.caption("\u26a0\ufe0f ML predictions are based on historical patterns. NOT financial advice. Use for education only.")


# ═══ 5. AI AUTO-STRATEGY ═══
def _render_ai_strategy(df, rsi, macd, macd_sig, sup_levels, res_levels, last_rsi, last_close, last_sma50, last_sma200, sym=""):
    st.markdown("#### \U0001f9e0 AI Auto-Strategy Generator")
    st.caption("AI analyzes current market conditions and generates a trading strategy automatically.")
    conditions = []; entry_rules = []; exit_rules = []
    if last_rsi < 30:
        conditions.append(f"RSI is oversold ({last_rsi:.1f}) \u2014 potential bounce")
        entry_rules.append({"desc": "RSI below 35 (oversold zone)"}); exit_rules.append({"desc": "RSI above 65 (overbought)"})
    elif last_rsi > 70:
        conditions.append(f"RSI is overbought ({last_rsi:.1f}) \u2014 potential reversal")
        entry_rules.append({"desc": "RSI above 70 (short setup)"}); exit_rules.append({"desc": "RSI back to 50"})
    else:
        conditions.append(f"RSI is neutral ({last_rsi:.1f})")
    if last_close > last_sma50 > last_sma200:
        conditions.append("Strong uptrend: Price > SMA50 > SMA200"); entry_rules.append({"desc": "Price above SMA50 (uptrend confirmed)"})
    elif last_close < last_sma50 < last_sma200:
        conditions.append("Strong downtrend: Price < SMA50 < SMA200"); entry_rules.append({"desc": "Price below SMA50 (downtrend)"})
    else:
        conditions.append("Mixed trend \u2014 SMA50 and SMA200 are diverging")
    last_macd = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0
    last_sig = float(macd_sig.iloc[-1]) if not pd.isna(macd_sig.iloc[-1]) else 0
    if last_macd > last_sig:
        conditions.append("MACD above signal line \u2014 bullish momentum"); entry_rules.append({"desc": "MACD bullish crossover"})
    else:
        conditions.append("MACD below signal line \u2014 bearish momentum"); entry_rules.append({"desc": "MACD bearish crossover"})
    nearest_sup = min(sup_levels, key=lambda x: abs(x - last_close)) if sup_levels else last_close * 0.95
    nearest_res = min(res_levels, key=lambda x: abs(x - last_close)) if res_levels else last_close * 1.05
    sl_pct = 3.0; tp_pct = 6.0
    if last_rsi < 30: sl_pct = 2.0; tp_pct = 5.0
    elif last_rsi > 70: sl_pct = 2.5; tp_pct = 4.0
    bullish_score = 0
    if last_rsi < 40: bullish_score += 2
    elif last_rsi > 60: bullish_score -= 2
    if last_macd > last_sig: bullish_score += 1
    else: bullish_score -= 1
    if last_close > last_sma50: bullish_score += 1
    else: bullish_score -= 1
    if last_sma50 > last_sma200: bullish_score += 1
    else: bullish_score -= 1
    if bullish_score >= 3:
        bias = "STRONG BULLISH"; strategy_name = "Momentum Breakout Long"
        actions = ["BUY on pullback to SMA50", "Hold until RSI > 70 or resistance hit"]
    elif bullish_score >= 1:
        bias = "MILD BULLISH"; strategy_name = "Trend Following Long"
        actions = ["BUY on MACD bullish crossover", "Exit on MACD bearish crossover"]
    elif bullish_score <= -3:
        bias = "STRONG BEARISH"; strategy_name = "Momentum Short"
        actions = ["SHORT on bounce to SMA50", "Cover when RSI < 30 or support hit"]
    elif bullish_score <= -1:
        bias = "MILD BEARISH"; strategy_name = "Trend Following Short"
        actions = ["SHORT on MACD bearish crossover", "Cover on MACD bullish crossover"]
    else:
        bias = "NEUTRAL"; strategy_name = "Range Trading"
        actions = ["BUY at support, SELL at resistance", "Use RSI < 30 for entry, RSI > 70 for exit"]
    bias_color = "#26a69a" if "BULLISH" in bias else "#ef5350" if "BEARISH" in bias else "#78909c"
    st.markdown(f"<div style='background:linear-gradient(135deg,rgba(0,20,40,0.9),rgba(5,0,30,0.85));border:2px solid {bias_color}33;border-radius:12px;padding:1.1rem 1.3rem;margin-bottom:1rem;'><div style='color:#8b949e;font-size:0.7rem;font-weight:700;letter-spacing:0.1em;'>AI GENERATED STRATEGY</div><div style='font-size:1.3rem;font-weight:bold;color:{bias_color};margin-top:4px;'>{strategy_name}</div><div style='color:#c9d1d9;font-size:0.9rem;margin-top:6px;'>Bias: {bias} (Score: {bullish_score:+d})</div></div>", unsafe_allow_html=True)
    st.markdown("**\U0001f4cb Market Conditions Detected:**")
    for c in conditions: st.markdown(f"- {c}")
    col_e, col_x = st.columns(2)
    with col_e:
        st.markdown("**\U0001f7e2 Entry Rules:**")
        for r in entry_rules: st.markdown(f"- {r['desc']}")
    with col_x:
        st.markdown("**\U0001f534 Exit Rules:**")
        for r in exit_rules: st.markdown(f"- {r['desc']}")
    st.markdown("**\u26a1 Recommended Actions:**")
    for a in actions: st.markdown(f"- {a}")
    st.markdown("**\u26a0\ufe0f Risk Management:**")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Stop Loss", f"{sl_pct}%"); r2.metric("Take Profit", f"{tp_pct}%")
    r3.metric("Position Size", "10%"); r4.metric("Risk:Reward", f"1:{tp_pct/sl_pct:.1f}")
    r5, r6 = st.columns(2)
    r5.metric("Nearest Support", f"\u20b9{nearest_sup:.2f}")
    r6.metric("Nearest Resistance", f"\u20b9{nearest_res:.2f}")
    if st.button("\U0001f680 Backtest This Strategy", type="primary", key="ai_strat_bt"):
        _run_ai_strategy_backtest(df, sym, strategy_name, {"stop_loss_pct": sl_pct, "take_profit_pct": tp_pct})


def _run_ai_strategy_backtest(df, sym, strategy_name, risk_rules):
    with st.spinner(f"Backtesting {strategy_name} on {sym}..."):
        close = df["close"]; rsi = _rsi(close); macd, macd_sig = _macd(close); sma50 = _sma(close, 50)
        signals = pd.Series(0, index=df.index)
        signals[(rsi < 35) & (close > sma50)] = 1; signals[rsi > 65] = -1
        signals[(macd > macd_sig) & (macd.shift() <= macd_sig.shift())] = 1
        signals[(macd < macd_sig) & (macd.shift() >= macd_sig.shift())] = -1
        sl = risk_rules["stop_loss_pct"] / 100; tp = risk_rules["take_profit_pct"] / 100
        capital = 100000; pos = 0.0; entry_px = 0.0; trades = []; equity = []; in_trade = False
        for i in range(len(df)):
            price = float(close.iloc[i]); sig = int(signals.iloc[i])
            if in_trade and entry_px > 0:
                if price <= entry_px * (1 - sl):
                    capital += pos * price; trades.append({"entry": entry_px, "exit": price, "pnl": (price-entry_px)*pos, "reason": "SL"})
                    pos = 0; in_trade = False; entry_px = 0
                elif price >= entry_px * (1 + tp):
                    capital += pos * price; trades.append({"entry": entry_px, "exit": price, "pnl": (price-entry_px)*pos, "reason": "TP"})
                    pos = 0; in_trade = False; entry_px = 0
            if sig == 1 and not in_trade and capital > 0:
                invest = capital * 0.95; pos = invest / price; capital -= invest; entry_px = price; in_trade = True
            elif sig == -1 and in_trade:
                capital += pos * price; trades.append({"entry": entry_px, "exit": price, "pnl": (price-entry_px)*pos, "reason": "Signal"})
                pos = 0; in_trade = False; entry_px = 0
            equity.append(capital + (pos * price if in_trade else 0))
        if in_trade:
            fp = float(close.iloc[-1]); capital += pos * fp
            trades.append({"entry": entry_px, "exit": fp, "pnl": (fp-entry_px)*pos, "reason": "End"})
        total_pnl = capital - 100000
        wins = [t for t in trades if t["pnl"] > 0]; win_rate = len(wins)/len(trades)*100 if trades else 0
        bt1, bt2, bt3, bt4 = st.columns(4)
        bt1.metric("Total P&L", f"\u20b9{total_pnl:,.2f}", f"{(total_pnl/100000)*100:+.1f}%")
        bt2.metric("Total Trades", len(trades)); bt3.metric("Win Rate", f"{win_rate:.1f}%")
        bt4.metric("Final Capital", f"\u20b9{capital:,.2f}")
        fig = go.Figure(); fig.add_trace(go.Scatter(x=df["date"], y=equity, name="Equity",
            line=dict(color="#26a69a", width=2), fill="tozeroy", fillcolor="rgba(38,166,154,0.05)"))
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=50, r=50, t=20, b=20),
            hovermode="x unified",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="Date", yaxis_title="Equity (\u20b9)",
            dragmode="zoom")
        fig.update_yaxes(side="right", tickformat=",.0f", fixedrange=False, showspikes=True, spikemode="across", spikesnap="cursor", spikecolor="grey", spikethickness=1); fig.update_xaxes(showgrid=False, showspikes=True, spikemode="across", spikesnap="cursor", spikecolor="grey", spikethickness=1)
        fig.update_yaxes(showgrid=True, gridcolor="rgba(50,50,50,0.2)", fixedrange=False)
        st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToAdd": ["drawline", "drawopenpath", "drawrect", "drawcircle", "drawarrow", "eraseshape"], "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]})


# ═══ MAIN RENDER ═══
def render_ai_analysis():
    st.markdown("""<div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,5,20,0.95));border:1px solid rgba(74,158,255,0.25);border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1rem;"><div style="display:flex;align-items:center;gap:0.9rem;flex-wrap:wrap;"><div><div style="font-size:1.1rem;font-weight:800;font-family:Orbitron,monospace;background:linear-gradient(90deg,#4a9eff,#00ff88);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">\U0001f9e0 AI Analysis Engine</div><div style="color:#8b949e;font-size:11px;margin-top:2px;">Photo-to-Chart \u00b7 Monte Carlo 30D \u00b7 ML (LR+RF) \u00b7 AI Strategy \u00b7 Golden/Death Cross \u00b7 Candlestick Patterns \u00b7 Full Quant Analysis</div></div></div></div>""", unsafe_allow_html=True)
    sub_tabs = st.tabs(["\U0001f4f8 Photo \u2192 Chart", "\U0001f4ca Full Analysis", "\U0001f3b2 Monte Carlo 30D", "\U0001f916 ML Prediction", "\U0001f916 StoxAI Chat", "\U0001f4f8 Chart Vision"])

    # -- StoxAI Chat (from FinSage AI module) --
    with sub_tabs[4]:
        from modules.finsage_ai import render_ai_chat
        render_ai_chat()

    # -- Chart Image Analyzer (from FinSage AI module) --
    with sub_tabs[5]:
        from modules.finsage_ai import render_chart_analyzer
        render_chart_analyzer()
    with sub_tabs[0]: _render_photo_upload()
    with sub_tabs[1]:
        sym = st.text_input("Symbol", value="RELIANCE.NS", placeholder="AAPL, RELIANCE.NS, BTC-USD...", key="ai_analysis_sym")
        period = st.selectbox("Period", ["6mo", "1y", "2y", "5y", "10y"], index=3, key="ai_analysis_period")
        if st.button("\U0001f50d Run Full Analysis", type="primary", key="ai_run_analysis"):
            st.session_state["ai_analysis_data"] = {"sym": sym, "period": period}; st.rerun()
        data_params = st.session_state.get("ai_analysis_data")
        if data_params:
            df = _fetch_data(data_params["sym"], data_params["period"])
            if df is not None and df.attrs.get("synthetic"):
                st.caption("\u26a0\ufe0f Live feed rate-limited \u2014 showing simulated candles.")
            if df is not None and len(df) > 10:
                _render_full_analysis(df, data_params["sym"]); st.markdown("---")
                _render_monte_carlo(df, data_params["sym"]); st.markdown("---")
                _render_ml_prediction(df, data_params["sym"])
            else:
                st.error(f"Could not fetch data for {data_params['sym']}")
        else:
            st.info("Enter a symbol and click 'Run Full Analysis' to see comprehensive technical + quant + ML analysis.")
    with sub_tabs[2]:
        mc_sym = st.text_input("Symbol", value="RELIANCE.NS", key="mc_sym_input")
        mc_period = st.selectbox("Historical Data Period", ["3mo", "6mo", "1y", "2y", "5y", "10y"], index=5, key="mc_period_select")
        if st.button("\U0001f3b2 Run Monte Carlo", type="primary", key="mc_run_btn"):
            st.session_state["mc_data"] = {"sym": mc_sym, "period": mc_period}; st.rerun()
        mc_data = st.session_state.get("mc_data")
        if mc_data:
            df = _fetch_data(mc_data["sym"], mc_data["period"])
            if df is not None and df.attrs.get("synthetic"):
                st.caption("\u26a0\ufe0f Live feed rate-limited \u2014 showing simulated candles.")
            if df is not None and len(df) > 20: _render_monte_carlo(df, mc_data["sym"])
            else: st.error(f"Could not fetch data for {mc_data['sym']}")
        else:
            st.info("Enter a symbol and click 'Run Monte Carlo' to simulate 30-day future price paths.")
    with sub_tabs[3]:
        ml_sym = st.text_input("Symbol", value="RELIANCE.NS", key="ml_sym_input")
        ml_period = st.selectbox("Training Data Period", ["6mo", "1y", "2y", "5y", "10y"], index=4, key="ml_period_select")
        if st.button("\U0001f916 Train & Predict", type="primary", key="ml_run_btn"):
            st.session_state["ml_data"] = {"sym": ml_sym, "period": ml_period}; st.rerun()
        ml_data = st.session_state.get("ml_data")
        if ml_data:
            df = _fetch_data(ml_data["sym"], ml_data["period"])
            if df is not None and df.attrs.get("synthetic"):
                st.caption("\u26a0\ufe0f Live feed rate-limited \u2014 showing simulated candles.")
            if df is not None and len(df) > 50: _render_ml_prediction(df, ml_data["sym"])
            else: st.error(f"Could not fetch data for {ml_data['sym']}")
        else:
            st.info("Enter a symbol and click 'Train & Predict' to get ML-based next-day direction prediction.")
