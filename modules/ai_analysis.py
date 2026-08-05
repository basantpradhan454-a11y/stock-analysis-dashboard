"""FinSage AI - Advanced Analysis Module
Chart photo upload, 30-day Monte Carlo, ML predictions, AI auto-strategy,
Fibonacci levels, comprehensive technical + quant analysis.
"""

import streamlit as st
import yfinance as yf
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

def _fibonacci_levels(df, lookback=100):
    recent = df.tail(lookback)
    swing_high = float(recent["high"].max())
    swing_low = float(recent["low"].min())
    diff = swing_high - swing_low
    return {
        "0.0%": swing_high, "23.6%": swing_high - 0.236 * diff,
        "38.2%": swing_high - 0.382 * diff, "50.0%": swing_high - 0.5 * diff,
        "61.8%": swing_high - 0.618 * diff, "100.0%": swing_low,
    }

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


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_data(sym, period="1y"):
    df = yf.Ticker(sym).history(period=period, interval="1d")
    if df.empty:
        return None
    df = df.reset_index()
    df = df.rename(columns={"Date": "date", "Open": "open", "High": "high",
                            "Low": "low", "Close": "close", "Volume": "volume"})
    df["date"] = pd.to_datetime(df["date"])
    return df


# ═══ 1. PHOTO UPLOAD → REAL CHART ═══
def _render_photo_upload():
    st.markdown("### \U0001f4f8 Chart Photo → Real Chart")
    st.caption("Upload any chart screenshot. Enter the symbol shown on it to load real data with full analysis.")
    uploaded = st.file_uploader("Upload chart screenshot/photo", type=["png", "jpg", "jpeg", "webp"], key="chart_photo_upload")
    if uploaded:
        col_photo, col_chart = st.columns([1, 2])
        with col_photo:
            st.markdown("**\U0001f4f7 Uploaded Chart:**")
            st.image(uploaded, use_container_width=True)
            sym_input = st.text_input("Symbol visible on chart (e.g. RELIANCE.NS, AAPL, BTC-USD)",
                key="photo_chart_sym", placeholder="Type the ticker you see on the chart...")
            period = st.selectbox("Data Period", ["6mo", "1y", "2y", "5y", "10y"], index=1, key="photo_chart_period")
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
                if df is not None and len(df) > 10:
                    _render_full_analysis(df, sym)
                else:
                    st.error(f"Could not fetch data for {sym}. Try a different symbol.")
            else:
                st.info("Upload a chart photo and enter the symbol to see real-time analysis here.")
    else:
        st.info("📷 Upload a chart screenshot to get started. Enter the symbol shown on it to load the real chart with full analysis.")


# ═══ 2. FULL TECHNICAL + QUANT ANALYSIS ═══
def _render_full_analysis(df, sym=""):
    close = df["close"]; high = df["high"]; low = df["low"]
    vol = df.get("volume", pd.Series(0, index=df.index))
    sma50 = _sma(close, 50); sma200 = _sma(close, 200); ema20 = _ema(close, 20)
    rsi = _rsi(close); macd, macd_sig = _macd(close); macd_hist = macd - macd_sig
    bb_u, bb_m, bb_l = _bb(close); atr_val = _atr(high, low, close)
    obv = _obv(close, vol); fib = _fibonacci_levels(df)
    sup_levels, res_levels = _find_support_resistance(df)
    last = df.iloc[-1]; last_close = float(last["close"])
    last_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
    last_macd = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0
    last_sig = float(macd_sig.iloc[-1]) if not pd.isna(macd_sig.iloc[-1]) else 0
    last_atr = float(atr_val.iloc[-1]) if not pd.isna(atr_val.iloc[-1]) else 0
    last_sma50 = float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else last_close
    last_sma200 = float(sma200.iloc[-1]) if not pd.isna(sma200.iloc[-1]) else last_close

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Price", f"\u20b9{last_close:.2f}")
    m2.metric("RSI", f"{last_rsi:.1f}", "Overbought" if last_rsi > 70 else "Oversold" if last_rsi < 30 else "Neutral")
    m3.metric("MACD", f"{last_macd:.2f}", "Bullish" if last_macd > last_sig else "Bearish")
    m4.metric("ATR", f"{last_atr:.2f}")
    m5.metric("Trend", "Up" if last_close > last_sma50 > last_sma200 else "Down" if last_close < last_sma50 < last_sma200 else "Mixed")

    st.markdown(f"#### \U0001f4ca {sym} — Technical Analysis Chart")
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=("Price + SMA + BB + Fibonacci", "Volume + OBV", "RSI + MACD"))
    fig.add_trace(go.Candlestick(x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="OHLC", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
        increasing_fillcolor="#26a69a", decreasing_fillcolor="#ef5350", line_width=1.5, whiskerwidth=0.5), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=sma50, name="SMA 50", line=dict(color="#2962ff", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=sma200, name="SMA 200", line=dict(color="#ff9800", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=ema20, name="EMA 20", line=dict(color="#e91e63", width=1.2), opacity=0.7), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=bb_u, name="BB Upper", line=dict(color="#9575cd", width=1, dash="dot"), opacity=0.5, showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=bb_l, name="BB Lower", line=dict(color="#9575cd", width=1, dash="dot"), opacity=0.5, showlegend=False), row=1, col=1)
    colors_fib = ["#ef5350", "#ff9800", "#26a69a", "#2962ff", "#ab47bc", "#26a69a"]
    for i, (label, val) in enumerate(fib.items()):
        fig.add_hline(y=val, line_dash="dash", line_color=colors_fib[i], opacity=0.4, line_width=1, row=1, col=1,
            annotation_text=f"Fib {label}: {val:.2f}", annotation_position="top left", annotation_font_size=8, annotation_font_color=colors_fib[i])
    for r in res_levels[-3:]:
        fig.add_hline(y=r, line_dash="solid", line_color="#ef5350", line_width=1.5, opacity=0.7, row=1, col=1,
            annotation_text=f"R: {r}", annotation_position="top right", annotation_font_size=9, annotation_font_color="#ef5350")
    for s in sup_levels[-3:]:
        fig.add_hline(y=s, line_dash="solid", line_color="#26a69a", line_width=1.5, opacity=0.7, row=1, col=1,
            annotation_text=f"S: {s}", annotation_position="bottom right", annotation_font_size=9, annotation_font_color="#26a69a")
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
    fig.update_layout(template="plotly_dark", height=700, margin=dict(l=50, r=60, t=40, b=30),
        xaxis_rangeslider_visible=False, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(size=10, family="Trebuchet MS, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified", dragmode="zoom")
    fig.update_xaxes(showgrid=False, showline=True, linecolor="rgba(50,50,50,0.3)")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(50,50,50,0.2)", side="right", showline=True, linecolor="rgba(50,50,50,0.3)")
    fig.update_yaxes(tickformat=".2f", row=1, col=1)
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "displayModeBar": True, "displaylogo": False, "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]})

    st.markdown("#### \U0001f4c8 Quant Analysis")
    returns = close.pct_change().dropna()
    q1, q2, q3, q4, q5, q6 = st.columns(6)
    q1.metric("Sharpe Ratio", f"{_sharpe_ratio(returns):.2f}")
    q2.metric("Sortino Ratio", f"{_sortino_ratio(returns):.2f}")
    q3.metric("Max Drawdown", f"{_max_drawdown(close)*100:.2f}%")
    q4.metric("VaR (95%)", f"{_var(returns)*100:.2f}%")
    q5.metric("Ann. Volatility", f"{returns.std()*np.sqrt(252)*100:.1f}%")
    q6.metric("Ann. Return", f"{((1+returns.mean())**252-1)*100:.1f}%")

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
        xaxis_title="Days Ahead", yaxis_title="Price (\u20b9)", showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(size=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_yaxes(side="right", tickformat=".2f"); fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(50,50,50,0.2)")
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displaylogo": False, "modeBarButtonsToRemove": ["select2d", "lasso2d"]})


# ═══ 4. ML PREDICTION (Pure numpy) ═══
def _render_ml_prediction(df, sym=""):
    st.markdown("#### \U0001f916 ML Prediction — Next Day Direction")
    st.caption("Logistic Regression trained on technical indicators to predict if price goes UP or DOWN tomorrow.")
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
    X_train = data.iloc[:split].drop(columns=["target"]).values; y_train = data.iloc[:split]["target"].values
    X_test = data.iloc[split:].drop(columns=["target"]).values; y_test = data.iloc[split:]["target"].values

    def sigmoid(z):
        z = np.clip(z, -500, 500); return 1 / (1 + np.exp(-z))
    n, d = X_train.shape; mu_f = X_train.mean(axis=0); std_f = X_train.std(axis=0) + 1e-8
    Xn = (X_train - mu_f) / std_f; Xn = np.c_[np.ones(n), Xn]; w = np.zeros(d + 1)
    for _ in range(1000):
        pred = sigmoid(Xn @ w); grad = Xn.T @ (pred - y_train) / n; w -= 0.01 * grad
    def predict_logreg(X):
        Xn = (X - mu_f) / (std_f + 1e-8); Xn = np.c_[np.ones(len(Xn)), Xn]; return sigmoid(Xn @ w)
    train_acc = ((predict_logreg(X_train) >= 0.5).astype(int) == y_train).mean() * 100
    test_acc = ((predict_logreg(X_test) >= 0.5).astype(int) == y_test).mean() * 100
    latest_features = features.iloc[-1:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(latest_features) > 0:
        prob_up = float(predict_logreg(latest_features.values)[0]); prob_down = 1 - prob_up
        pred_direction = "UP \u2b06\ufe0f" if prob_up >= 0.5 else "DOWN \u2b07\ufe0f"
        confidence = max(prob_up, prob_down) * 100
    else:
        prob_up = prob_down = 0.5; pred_direction = "NEUTRAL"; confidence = 50
    ml1, ml2, ml3, ml4 = st.columns(4)
    ml1.metric("Prediction", pred_direction); ml2.metric("Confidence", f"{confidence:.1f}%")
    ml3.metric("Train Accuracy", f"{train_acc:.1f}%"); ml4.metric("Test Accuracy", f"{test_acc:.1f}%")
    prob_col1, prob_col2 = st.columns(2)
    with prob_col1:
        st.markdown(f"<div style='background:#1a2e1a;border:1px solid #26a69a;border-radius:10px;padding:14px;text-align:center;margin:4px;'><div style='color:#26a69a;font-size:12px;'>Probability UP</div><div style='color:#26a69a;font-size:1.8rem;font-weight:bold;'>{prob_up*100:.1f}%</div><div style='background:#0d1117;border-radius:6px;height:10px;margin-top:8px;overflow:hidden;'><div style='background:#26a69a;height:100%;width:{prob_up*100:.1f}%;border-radius:6px;'></div></div></div>", unsafe_allow_html=True)
    with prob_col2:
        st.markdown(f"<div style='background:#2e1a1a;border:1px solid #ef5350;border-radius:10px;padding:14px;text-align:center;margin:4px;'><div style='color:#ef5350;font-size:12px;'>Probability DOWN</div><div style='color:#ef5350;font-size:1.8rem;font-weight:bold;'>{prob_down*100:.1f}%</div><div style='background:#0d1117;border-radius:6px;height:10px;margin-top:8px;overflow:hidden;'><div style='background:#ef5350;height:100%;width:{prob_down*100:.1f}%;border-radius:6px;'></div></div></div>", unsafe_allow_html=True)
    feature_names = list(features.columns); importance = np.abs(w[1:])
    importance = importance / importance.sum() if importance.sum() > 0 else importance
    fig_imp = go.Figure(go.Bar(x=importance, y=feature_names, orientation="h",
        marker_color=["#2962ff" if imp > 0 else "#ef5350" for imp in importance],
        text=[f"{imp*100:.1f}%" for imp in importance], textposition="outside"))
    fig_imp.update_layout(template="plotly_dark", height=250, margin=dict(l=0, r=50, t=10, b=10),
        xaxis_title="Importance", yaxis_title="", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig_imp, use_container_width=True, config={"displaylogo": False})
    st.caption("⚠️ ML predictions are based on historical patterns. NOT financial advice. Use for education only.")


# ═══ 5. AI AUTO-STRATEGY ═══
def _render_ai_strategy(df, rsi, macd, macd_sig, sup_levels, res_levels, last_rsi, last_close, last_sma50, last_sma200, sym=""):
    st.markdown("#### \U0001f9e0 AI Auto-Strategy Generator")
    st.caption("AI analyzes current market conditions and generates a trading strategy automatically.")
    conditions = []; entry_rules = []; exit_rules = []
    if last_rsi < 30:
        conditions.append(f"RSI is oversold ({last_rsi:.1f}) — potential bounce")
        entry_rules.append({"desc": "RSI below 35 (oversold zone)"}); exit_rules.append({"desc": "RSI above 65 (overbought)"})
    elif last_rsi > 70:
        conditions.append(f"RSI is overbought ({last_rsi:.1f}) — potential reversal")
        entry_rules.append({"desc": "RSI above 70 (short setup)"}); exit_rules.append({"desc": "RSI back to 50"})
    else:
        conditions.append(f"RSI is neutral ({last_rsi:.1f})")
    if last_close > last_sma50 > last_sma200:
        conditions.append("Strong uptrend: Price > SMA50 > SMA200"); entry_rules.append({"desc": "Price above SMA50 (uptrend confirmed)"})
    elif last_close < last_sma50 < last_sma200:
        conditions.append("Strong downtrend: Price < SMA50 < SMA200"); entry_rules.append({"desc": "Price below SMA50 (downtrend)"})
    else:
        conditions.append("Mixed trend — SMA50 and SMA200 are diverging")
    last_macd = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0
    last_sig = float(macd_sig.iloc[-1]) if not pd.isna(macd_sig.iloc[-1]) else 0
    if last_macd > last_sig:
        conditions.append("MACD above signal line — bullish momentum"); entry_rules.append({"desc": "MACD bullish crossover"})
    else:
        conditions.append("MACD below signal line — bearish momentum"); entry_rules.append({"desc": "MACD bearish crossover"})
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
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="Date", yaxis_title="Equity (\u20b9)")
        fig.update_yaxes(side="right", tickformat=",.0f"); fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="rgba(50,50,50,0.2)")
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


# ═══ MAIN RENDER ═══
def render_ai_analysis():
    st.markdown("""<div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,5,20,0.95));border:1px solid rgba(74,158,255,0.25);border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1rem;"><div style="display:flex;align-items:center;gap:0.9rem;flex-wrap:wrap;"><div><div style="font-size:1.1rem;font-weight:800;font-family:Orbitron,monospace;background:linear-gradient(90deg,#4a9eff,#00ff88);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">\U0001f9e0 AI Analysis Engine</div><div style="color:#8b949e;font-size:11px;margin-top:2px;">Photo-to-Chart · Monte Carlo 30D · ML Prediction · AI Strategy · Full Quant Analysis</div></div></div></div>""", unsafe_allow_html=True)
    sub_tabs = st.tabs(["\U0001f4f8 Photo → Chart", "\U0001f4ca Full Analysis", "\U0001f3b2 Monte Carlo 30D", "\U0001f916 ML Prediction"])
    with sub_tabs[0]: _render_photo_upload()
    with sub_tabs[1]:
        sym = st.text_input("Symbol", value="RELIANCE.NS", placeholder="AAPL, RELIANCE.NS, BTC-USD...", key="ai_analysis_sym")
        period = st.selectbox("Period", ["6mo", "1y", "2y", "5y", "10y"], index=1, key="ai_analysis_period")
        if st.button("\U0001f50d Run Full Analysis", type="primary", key="ai_run_analysis"):
            st.session_state["ai_analysis_data"] = {"sym": sym, "period": period}; st.rerun()
        data_params = st.session_state.get("ai_analysis_data")
        if data_params:
            df = _fetch_data(data_params["sym"], data_params["period"])
            if df is not None and len(df) > 10:
                _render_full_analysis(df, data_params["sym"]); st.markdown("---")
                _render_monte_carlo(df, data_params["sym"]); st.markdown("---")
                _render_ml_prediction(df, data_params["sym"])
            else:
                st.error(f"Could not fetch data for {data_params['sym']}")
        else:
            st.info("👆 Enter a symbol and click 'Run Full Analysis' to see comprehensive technical + quant + ML analysis.")
    with sub_tabs[2]:
        mc_sym = st.text_input("Symbol", value="RELIANCE.NS", key="mc_sym_input")
        mc_period = st.selectbox("Historical Data Period", ["3mo", "6mo", "1y", "2y", "5y"], index=2, key="mc_period_select")
        if st.button("\U0001f3b2 Run Monte Carlo", type="primary", key="mc_run_btn"):
            st.session_state["mc_data"] = {"sym": mc_sym, "period": mc_period}; st.rerun()
        mc_data = st.session_state.get("mc_data")
        if mc_data:
            df = _fetch_data(mc_data["sym"], mc_data["period"])
            if df is not None and len(df) > 20: _render_monte_carlo(df, mc_data["sym"])
            else: st.error(f"Could not fetch data for {mc_data['sym']}")
        else:
            st.info("👆 Enter a symbol and click 'Run Monte Carlo' to simulate 30-day future price paths.")
    with sub_tabs[3]:
        ml_sym = st.text_input("Symbol", value="RELIANCE.NS", key="ml_sym_input")
        ml_period = st.selectbox("Training Data Period", ["6mo", "1y", "2y", "5y"], index=1, key="ml_period_select")
        if st.button("\U0001f916 Train & Predict", type="primary", key="ml_run_btn"):
            st.session_state["ml_data"] = {"sym": ml_sym, "period": ml_period}; st.rerun()
        ml_data = st.session_state.get("ml_data")
        if ml_data:
            df = _fetch_data(ml_data["sym"], ml_data["period"])
            if df is not None and len(df) > 50: _render_ml_prediction(df, ml_data["sym"])
            else: st.error(f"Could not fetch data for {ml_data['sym']}")
        else:
            st.info("👆 Enter a symbol and click 'Train & Predict' to get ML-based next-day direction prediction.")
