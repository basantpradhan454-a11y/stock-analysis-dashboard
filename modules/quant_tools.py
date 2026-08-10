"""Quant Tools Module
Position sizing, Black-Scholes options pricer, correlation matrix,
Monte Carlo simulator, VaR, factor exposure, quant signal screener, P&L calendar.
"""

import streamlit as st
import yfinance as yf
from modules.data_fetch import get_history
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
# Normal distribution functions (no scipy needed)
import math as _m

def _norm_cdf(x):
    return 0.5 * (1 + _m.erf(x / _m.sqrt(2)))

def _norm_pdf(x):
    return _m.exp(-x**2 / 2) / _m.sqrt(2 * _m.pi)

class norm:
    cdf = staticmethod(_norm_cdf)
    pdf = staticmethod(_norm_pdf)
import math

# ═══════════════════════════════════════════════════════════════════════════
# 1. POSITION SIZE & RISK CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════
def render_risk_calculator():
    st.markdown("## Position Size & Risk Calculator")
    st.caption("Calculate optimal position size based on your risk tolerance and stop loss.")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: capital = st.number_input("Total Capital", value=100000, step=10000, key="rc_cap")
    with c2: risk_pct = st.slider("Risk per trade (%)", 0.5, 20.0, 2.0, 0.5, key="rc_risk")
    with c3: entry_price = st.number_input("Entry Price", value=100.0, step=0.5, format="%.2f", key="rc_entry")
    with c4: stop_price = st.number_input("Stop Loss Price", value=95.0, step=0.5, format="%.2f", key="rc_stop")
    
    risk_amount = capital * (risk_pct / 100)
    per_share_risk = abs(entry_price - stop_price)
    
    if per_share_risk > 0:
        max_shares = int(risk_amount / per_share_risk)
        position_value = max_shares * entry_price
        position_pct = (position_value / capital) * 100 if capital > 0 else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Risk Amount", f"\u20b9{risk_amount:,.2f}")
        m2.metric("Risk per Share", f"\u20b9{per_share_risk:.2f}")
        m3.metric("Max Position", f"{max_shares:,} shares")
        m4.metric("Position Value", f"\u20b9{position_value:,.2f}", f"{position_pct:.1f}% of capital")
        
        # Risk reward
        c5, c6 = st.columns(2)
        with c5: target_price = st.number_input("Target Price", value=110.0, step=0.5, format="%.2f", key="rc_target")
        with c6:
            reward = target_price - entry_price
            rr_ratio = reward / per_share_risk if per_share_risk > 0 else 0
            st.metric("Risk:Reward Ratio", f"1:{rr_ratio:.2f}")
        
        # Visual bar
        risk_bar = min(risk_pct / 20.0 * 100, 100)
        st.markdown(f"""
        <div style='background:#1c2431;border:1px solid #2a3441;border-radius:10px;padding:14px;margin-top:10px;'>
            <div style='color:#8b949e;font-size:12px;margin-bottom:6px;'>Risk as % of Capital</div>
            <div style='background:#0d1117;border-radius:6px;height:24px;overflow:hidden;'>
                <div style='background:linear-gradient(90deg,#22c55e,#f59e0b,#ef4444);height:100%;width:{risk_bar}%;border-radius:6px;'></div>
            </div>
            <div style='display:flex;justify-content:space-between;font-size:11px;color:#8b949e;margin-top:4px;'>
                <span>Safe (0.5%)</span><span>Moderate (5%)</span><span>High Risk (20%)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Entry and stop loss prices cannot be the same.")


# ═══════════════════════════════════════════════════════════════════════════
# 2. BLACK-SCHOLES OPTIONS PRICER
# ═══════════════════════════════════════════════════════════════════════════
def _black_scholes(S, K, T, r, sigma, option_type="call"):
    if T <= 0 or sigma <= 0:
        intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
        return intrinsic, 0, 0, 0, 0, 0
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    N_d1 = norm.cdf(d1)
    N_d2 = norm.cdf(d2)
    N_neg_d1 = norm.cdf(-d1)
    N_neg_d2 = norm.cdf(-d2)
    
    if option_type == "call":
        price = S * N_d1 - K * math.exp(-r * T) * N_d2
        delta = N_d1
    else:
        price = K * math.exp(-r * T) * N_neg_d2 - S * N_neg_d1
        delta = N_d1 - 1
    
    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * math.sqrt(T) * norm.pdf(d1) / 100  # per 1% change in vol
    theta = (-(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * (N_d2 if option_type == "call" else N_neg_d2)) / 365
    rho = (K * T * math.exp(-r * T) * (N_d2 if option_type == "call" else N_neg_d2)) / 100
    
    return price, delta, gamma, vega, theta, rho

def render_option_pricer():
    st.markdown("## Options Pricer (Black-Scholes)")
    st.caption("Price European call and put options using the Black-Scholes-Merton model.")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: S = st.number_input("Spot Price (S)", value=100.0, step=0.5, format="%.2f", key="op_S")
    with c2: K = st.number_input("Strike Price (K)", value=100.0, step=0.5, format="%.2f", key="op_K")
    with c3: T = st.number_input("Time to Expiry (days)", value=30, step=1, key="op_T")
    with c4: r = st.number_input("Risk-free Rate (%)", value=6.5, step=0.1, format="%.1f", key="op_r")
    with c5: sigma = st.number_input("Volatility (\u03c3 %)", value=25.0, step=0.5, format="%.1f", key="op_sigma")
    
    T_years = T / 365.0
    r_dec = r / 100
    sigma_dec = sigma / 100
    
    call_price, call_d, call_g, call_v, call_th, call_rho = _black_scholes(S, K, T_years, r_dec, sigma_dec, "call")
    put_price, put_d, put_g, put_v, put_th, put_rho = _black_scholes(S, K, T_years, r_dec, sigma_dec, "put")
    
    st.markdown("### Prices")
    p1, p2 = st.columns(2)
    with p1:
        st.metric("Call Price", f"\u20b9{call_price:.2f}", f"Delta: {call_d:.4f}")
    with p2:
        st.metric("Put Price", f"\u20b9{put_price:.2f}", f"Delta: {put_d:.4f}")
    
    st.markdown("### Greeks")
    greeks_df = pd.DataFrame({
        "Greek": ["Price", "Delta", "Gamma", "Vega (per 1%)", "Theta (per day)", "Rho (per 1%)"],
        "Call": [f"\u20b9{call_price:.2f}", f"{call_d:.4f}", f"{call_g:.6f}", f"{call_v:.4f}", f"{call_th:.4f}", f"{call_rho:.4f}"],
        "Put": [f"\u20b9{put_price:.2f}", f"{put_d:.4f}", f"{put_g:.6f}", f"{put_v:.4f}", f"{put_th:.4f}", f"{put_rho:.4f}"],
    })
    st.dataframe(greeks_df, use_container_width=True, hide_index=True)
    
    # Payoff diagram
    st.markdown("### Payoff Diagram at Expiry")
    prices = np.linspace(S * 0.7, S * 1.3, 50)
    call_payoff = np.maximum(prices - K, 0) - call_price
    put_payoff = np.maximum(K - prices, 0) - put_price
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices, y=call_payoff, name="Call P&L", line=dict(color="#22c55e", width=2)))
    fig.add_trace(go.Scatter(x=prices, y=put_payoff, name="Put P&L", line=dict(color="#ef4444", width=2)))
    fig.add_hline(y=0, line=dict(color="#8b949e", width=1, dash="dash"))
    fig.add_vline(x=K, line=dict(color="#3b82f6", width=1, dash="dot"), name="Strike")
    fig.update_layout(height=350, margin=dict(l=0,r=0,t=10,b=0), xaxis_title="Spot at Expiry", yaxis_title="P&L", dragmode="pan")
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })


# ═══════════════════════════════════════════════════════════════════════════
# 3. CORRELATION MATRIX
# ═══════════════════════════════════════════════════════════════════════════
def render_correlation():
    st.markdown("## Correlation Matrix")
    st.caption("Compare return correlations between assets to diversify your portfolio.")
    
    symbols_text = st.text_input("Symbols (comma-separated)", value="RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, ^NSEI", key="corr_sym")
    period = st.selectbox("Period", ["3mo", "6mo", "1y", "2y", "5y", "10y"], index=5, key="corr_period")
    
    symbols = [s.strip() for s in symbols_text.split(",") if s.strip()]
    
    if st.button("Compute Correlation", type="primary", key="corr_btn"):
        with st.spinner(f"Fetching data for {len(symbols)} assets..."):
            returns_df = pd.DataFrame()
            for sym in symbols:
                try:
                    df, _ = get_history(sym, period=period, interval="1d")
                    if df is not None and not df.empty:
                        returns_df[sym] = df["Close"].pct_change()
                except Exception:
                    pass
        
        if returns_df.empty or len(returns_df.columns) < 2:
            st.error("Could not fetch enough data.")
            return
        
        corr = returns_df.corr()
        
        fig = go.Figure(go.Heatmap(
            z=corr.values, x=corr.columns, y=corr.columns,
            colorscale="RdYlGn", zmid=0, zmin=-1, zmax=1,
            text=corr.values.round(2), texttemplate="%{text}", textfont=dict(size=10),
        ))
        fig.update_layout(height=450, margin=dict(l=0,r=0,t=10,b=0), dragmode="pan")
        st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })
        
        st.dataframe(corr.style.background_gradient(cmap="RdYlGn", vmin=-1, vmax=1), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# 4. MONTE CARLO SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════
def render_monte_carlo():
    st.markdown("## Monte Carlo Simulator")
    st.caption("Simulate future price paths using Geometric Brownian Motion (GBM).")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: sym = st.text_input("Symbol", value="RELIANCE.NS", key="mc_sym")
    with c2: days = st.slider("Days to Simulate", 10, 365, 90, key="mc_days")
    with c3: n_sims = st.slider("Simulations", 100, 5000, 500, 50, key="mc_sims")
    with c4: confidence = st.selectbox("Confidence", [90, 95, 99], index=1, key="mc_conf")
    with c5: period = st.selectbox("Historical Data", ["3mo", "6mo", "1y", "2y", "5y", "10y"], index=5, key="mc_period")
    
    if st.button("Run Simulation", type="primary", key="mc_run"):
        with st.spinner("Running Monte Carlo simulation..."):
            df, is_synthetic = get_history(sym, period=period, interval="1d")
            if df is None or df.empty:
                st.error(f"No data for {sym}")
                return
            if is_synthetic:
                st.caption("\u26a0\ufe0f Live feed rate-limited \u2014 showing simulated candles.")
            
            S0 = float(df["Close"].iloc[-1])
            returns = df["Close"].pct_change().dropna()
            mu = returns.mean() * 252  # annualized
            sigma = returns.std() * math.sqrt(252)  # annualized
            dt = 1 / 252
            
            # Run simulations
            np.random.seed(42)
            paths = np.zeros((n_sims, days + 1))
            paths[:, 0] = S0
            for t in range(1, days + 1):
                z = np.random.standard_normal(n_sims)
                paths[:, t] = paths[:, t-1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z)
        
        # Results
        final_prices = paths[:, -1]
        p5 = np.percentile(final_prices, (100 - confidence) / 2)
        p50 = np.percentile(final_prices, 50)
        p95 = np.percentile(final_prices, 100 - (100 - confidence) / 2)
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Current Price", f"\u20b9{S0:.2f}")
        m2.metric(f"{confidence}% Low", f"\u20b9{p5:.2f}", f"{(p5/S0-1)*100:+.1f}%")
        m3.metric("Median", f"\u20b9{p50:.2f}", f"{(p50/S0-1)*100:+.1f}%")
        m4.metric(f"{confidence}% High", f"\u20b9{p95:.2f}", f"{(p95/S0-1)*100:+.1f}%")
        m5.metric("Drift (\u03bc)", f"{mu*100:.1f}%")
        
        # Plot sample paths
        fig = go.Figure()
        for i in range(min(n_sims, 50)):
            fig.add_trace(go.Scatter(x=list(range(days+1)), y=paths[i], mode="lines", line=dict(width=0.5), opacity=0.3, showlegend=False))
        
        # Percentile bands
        p10_path = np.percentile(paths, 5, axis=0)
        p90_path = np.percentile(paths, 95, axis=0)
        p50_path = np.percentile(paths, 50, axis=0)
        fig.add_trace(go.Scatter(x=list(range(days+1)), y=p10_path, name=f"{confidence}% Low", line=dict(color="#ef4444", width=2)))
        fig.add_trace(go.Scatter(x=list(range(days+1)), y=p50_path, name="Median", line=dict(color="#3b82f6", width=2)))
        fig.add_trace(go.Scatter(x=list(range(days+1)), y=p90_path, name=f"{confidence}% High", line=dict(color="#22c55e", width=2)))
        fig.update_layout(height=400, margin=dict(l=0,r=0,t=10,b=0), xaxis_title="Days", yaxis_title="Price", dragmode="pan")
        st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })


# ═══════════════════════════════════════════════════════════════════════════
# 5. VALUE AT RISK (VaR)
# ═══════════════════════════════════════════════════════════════════════════
def render_var():
    st.markdown("## Value at Risk (VaR)")
    st.caption("Estimate potential portfolio losses using historical and parametric methods.")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: portfolio_value = st.number_input("Portfolio Value", value=1000000, step=100000, key="var_pv")
    with c2: symbols_text = st.text_input("Holdings (comma-sep)", value="RELIANCE.NS, TCS.NS, INFY.NS", key="var_sym")
    with c3: weights_text = st.text_input("Weights (comma-sep)", value="0.4, 0.35, 0.25", key="var_w")
    with c4: period = st.selectbox("Lookback Period", ["3mo", "6mo", "1y", "2y", "5y", "10y"], index=5, key="var_period")
    
    confidence_levels = st.multiselect("Confidence Levels", [90, 95, 99], default=[95, 99], key="var_conf")
    horizon = st.slider("Time Horizon (days)", 1, 20, 1, key="var_horizon")
    
    if st.button("Calculate VaR", type="primary", key="var_btn"):
        symbols = [s.strip() for s in symbols_text.split(",") if s.strip()]
        try:
            weights = [float(w.strip()) for w in weights_text.split(",")]
        except Exception:
            st.error("Invalid weights format.")
            return
        
        if len(symbols) != len(weights):
            st.error("Number of symbols and weights must match.")
            return
        
        with st.spinner("Fetching data..."):
            returns_df = pd.DataFrame()
            for sym in symbols:
                try:
                    df, _ = get_history(sym, period=period, interval="1d")
                    if df is not None and not df.empty:
                        returns_df[sym] = df["Close"].pct_change()
                except Exception:
                    pass
        
        if returns_df.empty:
            st.error("No data.")
            return
        
        # Portfolio returns
        port_returns = (returns_df[symbols] * weights).sum(axis=1).dropna()
        
        for conf in confidence_levels:
            alpha = 1 - conf / 100
            z = norm.ppf(alpha)
            
            # Parametric VaR
            mean = port_returns.mean()
            std = port_returns.std()
            param_var = portfolio_value * (mean * horizon + z * std * math.sqrt(horizon)) * -1
            
            # Historical VaR
            hist_var = portfolio_value * np.percentile(port_returns, alpha * 100) * math.sqrt(horizon) * -1
            
            # Expected Shortfall (CVaR)
            es_threshold = np.percentile(port_returns, alpha * 100)
            cvar = portfolio_value * port_returns[port_returns <= es_threshold].mean() * math.sqrt(horizon) * -1
            
            col_color = "#ef4444" if conf == 99 else "#f59e0b" if conf == 95 else "#3b82f6"
            st.markdown(f"""
            <div style='border:1px solid {col_color}33;border-radius:10px;padding:14px;margin:8px 0;background:{col_color}08;'>
                <div style='font-weight:700;color:{col_color};'>{conf}% Confidence ({horizon}d horizon)</div>
                <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:8px;'>
                    <div><div style='font-size:11px;color:#8b949e;'>Parametric VaR</div><div style='font-weight:600;font-size:18px;'>-\u20b9{param_var:,.0f}</div></div>
                    <div><div style='font-size:11px;color:#8b949e;'>Historical VaR</div><div style='font-weight:600;font-size:18px;'>-\u20b9{hist_var:,.0f}</div></div>
                    <div><div style='font-size:11px;color:#8b949e;'>Expected Shortfall</div><div style='font-weight:600;font-size:18px;'>-\u20b9{cvar:,.0f}</div></div>
                </div>
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# 6. FACTOR EXPOSURE
# ═══════════════════════════════════════════════════════════════════════════
def render_factor_exposure():
    st.markdown("## Factor Exposure")
    st.caption("Analyze your portfolio's exposure to common risk factors.")
    
    factors = ["Momentum", "Value", "Size", "Quality", "Volatility", "Growth", "Profitability", "Leverage"]
    default_vals = [0.42, -0.18, 0.09, 0.31, -0.22, 0.15, 0.28, -0.11]
    
    col_edit, col_chart = st.columns([1, 2])
    with col_edit:
        st.markdown("#### Factor Values")
        factor_vals = []
        for i, f in enumerate(factors):
            v = st.slider(f, -1.0, 1.0, float(default_vals[i]), 0.01, key=f"fe_{f}")
            factor_vals.append(v)
    
    with col_chart:
        colors = ["#22c55e" if v >= 0 else "#ef4444" for v in factor_vals]
        fig = go.Figure(go.Bar(x=factor_vals, y=factors, orientation="h", marker_color=colors,
                               text=[f"{v:+.2f}" for v in factor_vals], textposition="outside"))
        fig.update_layout(height=400, margin=dict(l=0,r=0,t=10,b=0), dragmode="pan", xaxis=dict(range=[-1, 1], gridcolor="#2a3441"),
                          yaxis=dict(gridcolor="#2a3441"))
        st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })
    
    # Summary
    positive = sum(1 for v in factor_vals if v > 0)
    positive = sum(1 for v in factor_vals if v > 0)
    negative = sum(1 for v in factor_vals if v < 0)
    strongest = factors[factor_vals.index(max(factor_vals))]
    weakest = factors[factor_vals.index(min(factor_vals))]
    st.info(f"Your portfolio has **{positive} positive** and **{negative} negative** factor exposures. Strongest: **{strongest}** ({max(factor_vals):+.2f}). Weakest: **{weakest}** ({min(factor_vals):+.2f}).")


# ═══════════════════════════════════════════════════════════════════════════
# 7. QUANT SIGNAL SCREENER
# ═══════════════════════════════════════════════════════════════════════════
def render_quant_screener():
    st.markdown("## Quant Signal Screener")
    st.caption("Screen multiple stocks for buy/sell signals based on technical indicators.")
    
    symbols_text = st.text_input("Symbols to scan (comma-separated)", 
                                  value="RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, ICICIBANK.NS, SBIN.NS, TATAMOTORS.NS, WIPRO.NS",
                                  key="qs_sym")
    symbols = [s.strip() for s in symbols_text.split(",") if s.strip()]
    
    if st.button("Scan Signals", type="primary", use_container_width=True, key="qs_scan"):
        results = []
        progress = st.progress(0)
        for i, sym in enumerate(symbols):
            progress.progress((i + 1) / max(len(symbols), 1))
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
                
                last_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
                last_close = float(close.iloc[-1])
                last_sma20 = float(sma20.iloc[-1]) if not pd.isna(sma20.iloc[-1]) else last_close
                last_sma50 = float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else last_close
                last_macd = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0
                last_signal = float(signal.iloc[-1]) if not pd.isna(signal.iloc[-1]) else 0
                
                bull = 0
                if last_rsi < 35: bull += 2
                elif last_rsi > 65: bull -= 2
                if last_macd > last_signal: bull += 1
                else: bull -= 1
                if last_close > last_sma20: bull += 1
                else: bull -= 1
                if last_sma20 > last_sma50: bull += 1
                else: bull -= 1
                
                action = "BUY" if bull >= 3 else "SELL" if bull <= -3 else "HOLD"
                color = "#22c55e" if action == "BUY" else "#ef4444" if action == "SELL" else "#8b949e"
                
                results.append({
                    "Symbol": sym, "Price": round(last_close, 2), "RSI": round(last_rsi, 1),
                    "MACD": "Bull" if last_macd > last_signal else "Bear",
                    "Trend": "Up" if last_sma20 > last_sma50 else "Down",
                    "Signal": action, "Score": bull,
                })
            except Exception:
                pass
        
        progress.empty()
        
        if not results:
            st.warning("No results.")
            return
        
        df_results = pd.DataFrame(results)
        
        # Color-coded signal column
        def color_signal(val):
            if val == "BUY": return "color:#22c55e;font-weight:700"
            elif val == "SELL": return "color:#ef4444;font-weight:700"
            return "color:#8b949e"
        
        styled = df_results.style.map(color_signal, subset=["Signal"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
        
        # Summary
        buys = len(df_results[df_results["Signal"] == "BUY"])
        sells = len(df_results[df_results["Signal"] == "SELL"])
        holds = len(df_results[df_results["Signal"] == "HOLD"])
        b1, b2, b3 = st.columns(3)
        b1.metric("Buy Signals", buys)
        b2.metric("Sell Signals", sells)
        b3.metric("Hold", holds)


# ═══════════════════════════════════════════════════════════════════════════
# 8. P&L CALENDAR
# ═══════════════════════════════════════════════════════════════════════════
def render_pnl_calendar():
    st.markdown("## P&L Calendar")
    st.caption("Daily profit and loss calendar view.")
    
    # Generate sample P&L data
    np.random.seed(42)
    today = datetime.now()
    days_back = st.slider("Days to show", 30, 180, 60, key="pc_days")
    start_date = today - timedelta(days=days_back)
    
    dates = pd.date_range(start=start_date, end=today, freq="B")  # business days
    daily_pnl = np.random.normal(5000, 15000, len(dates))
    cum_pnl = np.cumsum(daily_pnl)
    
    # Summary metrics
    total_pnl = cum_pnl[-1]
    best_day = max(daily_pnl)
    worst_day = min(daily_pnl)
    win_days = sum(1 for p in daily_pnl if p > 0)
    loss_days = sum(1 for p in daily_pnl if p < 0)
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total P&L", f"\u20b9{total_pnl:+,.0f}")
    m2.metric("Best Day", f"\u20b9{best_day:+,.0f}")
    m3.metric("Worst Day", f"\u20b9{worst_day:+,.0f}")
    m4.metric("Win Days", f"{win_days}/{len(dates)}")
    m5.metric("Loss Days", f"{loss_days}/{len(dates)}")
    
    # Cumulative P&L chart
    fig = go.Figure()
    colors = ["#22c55e" if p >= 0 else "#ef4444" for p in daily_pnl]
    fig.add_trace(go.Bar(x=dates, y=daily_pnl, name="Daily P&L", marker_color=colors))
    fig.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0), xaxis_title="Date", yaxis_title="Daily P&L", dragmode="pan")
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })
    
    # Cumulative P&L line
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=dates, y=cum_pnl, name="Cumulative P&L", 
                              line=dict(color="#3b82f6", width=2), fill="tozeroy",
                              fillcolor="rgba(59,130,246,0.1)"))
    fig2.add_hline(y=0, line=dict(color="#8b949e", width=1, dash="dash"))
    fig2.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), xaxis_title="Date", yaxis_title="Cumulative P&L", dragmode="pan")
    st.plotly_chart(fig2, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    })
    
    # Calendar table
    st.markdown("### Daily Breakdown")
    pnl_df = pd.DataFrame({"Date": dates.strftime("%Y-%m-%d"), "Daily P&L": [f"\u20b9{p:+,.0f}" for p in daily_pnl], "Cumulative": [f"\u20b9{c:+,.0f}" for c in cum_pnl]})
    st.dataframe(pnl_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ═══════════════════════════════════════════════════════════════════════════
def render_quant_tools():
    tools = [
        "Position Size & Risk Calculator",
        "Options Pricer (Black-Scholes)",
        "Correlation Matrix",
        "Monte Carlo Simulator",
        "Value at Risk (VaR)",
        "Factor Exposure",
        "Quant Signal Screener",
        "P&L Calendar",
    ]
    
    selected = st.sidebar.selectbox("Quant Tool", tools, key="qt_select")
    
    if selected == "Position Size & Risk Calculator":
        render_risk_calculator()
    elif selected == "Options Pricer (Black-Scholes)":
        render_option_pricer()
    elif selected == "Correlation Matrix":
        render_correlation()
    elif selected == "Monte Carlo Simulator":
        render_monte_carlo()
    elif selected == "Value at Risk (VaR)":
        render_var()
    elif selected == "Factor Exposure":
        render_factor_exposure()
    elif selected == "Quant Signal Screener":
        render_quant_screener()
    elif selected == "P&L Calendar":
        render_pnl_calendar()
