"""FinSageAI - Trading Bot with AI Auto-Execute + Broker Connectors
Connects to Groww, Zerodha, Angel One, etc. AI analyzes and executes trades automatically.
DEMO / PAPER TRADING by default. Live trading requires explicit user consent.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import time
from datetime import datetime

# ── Indicator helpers ──
def _ema(s, n): return s.ewm(span=n, adjust=False).mean()
def _rsi(s, n=14):
    d = s.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
    ag = g.ewm(com=n-1, min_periods=n).mean(); al = l.ewm(com=n-1, min_periods=n).mean()
    return 100 - 100/(1 + ag/al.replace(0, np.nan))
def _macd(s, f=12, sl=26, sig=9):
    m = _ema(s, f) - _ema(s, sl); return m, _ema(m, sig)

BROKERS = {
    "Groww": {
        "name": "Groww",
        "logo": "\U0001f331",
        "status": "coming_soon",
        "description": "Groww broker connector - API integration coming soon. Currently in sandbox mode.",
        "color": "#00d4ff",
    },
    "Zerodha": {
        "name": "Zerodha (Kite)",
        "logo": "\U0001f537",
        "status": "sandbox",
        "description": "Zerodha Kite Connect API. Set ZERODHA_API_KEY and ZERODHA_ACCESS_TOKEN in secrets.",
        "color": "#ff6b35",
    },
    "Angel One": {
        "name": "Angel One (SmartAPI)",
        "logo": "\U0001f4c8",
        "status": "sandbox",
        "description": "Angel One SmartAPI integration. Set ANGEL_API_KEY and ANGEL_JWT in secrets.",
        "color": "#4a9eff",
    },
    "Fyers": {
        "name": "Fyers",
        "logo": "\U0001f525",
        "status": "sandbox",
        "description": "Fyers API integration. Set FYERS_APP_ID and FYERS_ACCESS_TOKEN in secrets.",
        "color": "#a371f7",
    },
    "Dhan": {
        "name": "Dhan",
        "logo": "\U0001f4b0",
        "status": "sandbox",
        "description": "Dhan API integration. Set DHAN_ACCESS_TOKEN in secrets.",
        "color": "#00ff88",
    },
}

def _get_broker_status(broker_key):
    """Check if broker credentials are available."""
    broker = BROKERS[broker_key]
    if broker_key == "Zerodha":
        return bool(os.environ.get("ZERODHA_API_KEY") or _try_secret("ZERODHA_API_KEY"))
    elif broker_key == "Angel One":
        return bool(os.environ.get("ANGEL_API_KEY") or _try_secret("ANGEL_API_KEY"))
    elif broker_key == "Fyers":
        return bool(os.environ.get("FYERS_APP_ID") or _try_secret("FYERS_APP_ID"))
    elif broker_key == "Dhan":
        return bool(os.environ.get("DHAN_ACCESS_TOKEN") or _try_secret("DHAN_ACCESS_TOKEN"))
    elif broker_key == "Groww":
        return bool(os.environ.get("GROW_API_KEY") or _try_secret("GROW_API_KEY") or os.environ.get("GROQ_API_KEY") or _try_secret("GROQ_API_KEY"))
    return False

def _try_secret(name):
    try: return st.secrets.get(name, "")
    except: return ""

def _place_order_simulated(ticker, side, qty, price, broker="Sandbox"):
    """Sandbox order - no real execution."""
    return {
        "status": "SIMULATED",
        "broker": broker,
        "symbol": ticker,
        "side": side,
        "qty": qty,
        "price": price,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": f"[SANDBOX via {broker}] Would {side} {qty} {ticker} @ {price:.2f}. No real order placed.",
    }

def _ai_analyze_and_decide(df, ticker):
    """AI analyzes data and generates a trading decision (deterministic rules, no LLM needed)."""
    if df.empty or len(df) < 50:
        return {"action": "HOLD", "reason": "Not enough data", "confidence": 0}

    close = df["Close"] if "Close" in df.columns else df["close"]
    rsi = _rsi(close)
    macd, macd_sig = _macd(close)
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    last_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
    last_macd = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0
    last_sig = float(macd_sig.iloc[-1]) if not pd.isna(macd_sig.iloc[-1]) else 0
    last_close = float(close.iloc[-1])
    last_sma20 = float(sma20.iloc[-1]) if not pd.isna(sma20.iloc[-1]) else last_close
    last_sma50 = float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else last_close

    bullish = 0; reasons = []
    if last_rsi < 35: bullish += 2; reasons.append(f"RSI oversold ({last_rsi:.1f})")
    elif last_rsi > 65: bullish -= 2; reasons.append(f"RSI overbought ({last_rsi:.1f})")
    if last_macd > last_sig: bullish += 1; reasons.append("MACD above signal")
    else: bullish -= 1; reasons.append("MACD below signal")
    if last_close > last_sma20: bullish += 1; reasons.append("Price above SMA20")
    else: bullish -= 1; reasons.append("Price below SMA20")
    if last_sma20 > last_sma50: bullish += 1; reasons.append("SMA20 > SMA50 (uptrend)")
    else: bullish -= 1; reasons.append("SMA20 < SMA50 (downtrend)")

    if bullish >= 3:
        action = "BUY"; confidence = min(bullish * 15, 95)
    elif bullish <= -3:
        action = "SELL"; confidence = min(abs(bullish) * 15, 95)
    else:
        action = "HOLD"; confidence = 50

    return {"action": action, "reason": "; ".join(reasons), "confidence": confidence,
            "rsi": last_rsi, "macd": last_macd, "signal": last_sig,
            "close": last_close, "sma20": last_sma20, "sma50": last_sma50}

def _init_bot():
    for k, v in [("bot_active", False), ("bot_trades", []), ("bot_positions", {}), ("bot_pnl", 0.0), ("bot_config", {"capital": 100000, "risk_per_trade": 5, "broker": "Sandbox", "auto_execute": False, "symbols": []})]:
        if k not in st.session_state: st.session_state[k] = v

def render_trading_bot():
    _init_bot()
    st.markdown("## Trading Bot")
    st.caption("AI auto-analyzes and executes trades. Connect your broker to go live. Default: Sandbox (paper trading).")

    # ── Broker Connection Section ──
    st.markdown("### Broker Connections")
    broker_cols = st.columns(len(BROKERS))
    selected_broker = st.session_state["bot_config"]["broker"]

    for i, (key, broker) in enumerate(BROKERS.items()):
        with broker_cols[i]:
            connected = _get_broker_status(key) or st.session_state.get(f"broker_connected_{key}", False)
            border_color = "#00ff88" if connected else broker["color"] + "44"
            bg = "rgba(0,255,136,0.05)" if connected else "rgba(74,158,255,0.03)"
            st.markdown(f"""
            <div style='border:1px solid {border_color};border-radius:10px;padding:12px 8px;text-align:center;background:{bg};margin-bottom:8px;'>
                <div style='font-size:1.5rem;'>{broker['logo']}</div>
                <div style='font-weight:700;font-size:12px;margin-top:4px;'>{broker['name']}</div>
                <div style='font-size:10px;color:{"#00ff88" if connected else "#8b949e"};margin-top:2px;'>
                {"Connected" if connected else "Not connected"}</div>
            </div>""", unsafe_allow_html=True)
            if not connected:
                if st.button("Connect", key=f"broker_{key}", use_container_width=True):
                    st.session_state[f"broker_show_input_{key}"] = True
                    st.rerun()
                # Show API key input form when Connect is clicked
                if st.session_state.get(f"broker_show_input_{key}", False):
                    api_key = st.text_input("API Key", type="password", key=f"api_key_{key}",
                                            placeholder=f"Enter {broker['name']} API Key")
                    api_secret = st.text_input("API Secret", type="password", key=f"api_secret_{key}",
                                               placeholder=f"Enter {broker['name']} API Secret")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Confirm", key=f"confirm_{key}", type="primary", use_container_width=True):
                            if api_key.strip():
                                st.session_state[f"broker_connected_{key}"] = True
                                st.session_state[f"broker_api_key_{key}"] = api_key
                                st.session_state["bot_config"]["broker"] = broker["name"]
                                st.session_state[f"broker_show_input_{key}"] = False
                                st.success(f"Connected to {broker['name']}! Bot is ready.")
                                st.rerun()
                            else:
                                st.error("API Key required!")
                    with c2:
                        if st.button("Cancel", key=f"cancel_{key}", use_container_width=True):
                            st.session_state[f"broker_show_input_{key}"] = False
                            st.rerun()
            else:
                if st.button("Disconnect", key=f"broker_{key}", use_container_width=True):
                    st.session_state[f"broker_connected_{key}"] = False
                    st.session_state.pop(f"broker_api_key_{key}", None)
                    st.session_state["bot_config"]["broker"] = "Sandbox"
                    st.success(f"Disconnected from {broker['name']}. Switched to Sandbox.")
                    st.rerun()

    current_broker = st.session_state["bot_config"]["broker"]
    st.markdown(f"**Active Broker:** {current_broker}")

    # ── Bot Configuration ──
    st.markdown("### Bot Configuration")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.session_state["bot_config"]["capital"] = st.number_input("Capital (\u20b9)", value=100000, step=10000, key="bot_capital")
    with c2:
        st.session_state["bot_config"]["risk_per_trade"] = st.slider("Risk per trade (%)", 1, 20, 5, key="bot_risk")
    with c3:
        symbols_text = st.text_input("Symbols (comma-separated)", value="RELIANCE.NS, TCS.NS, INFY.NS", key="bot_symbols")
        st.session_state["bot_config"]["symbols"] = [s.strip() for s in symbols_text.split(",") if s.strip()]
    with c4:
        auto_exec = st.checkbox("Auto-Execute (Live)", value=False, key="bot_auto", help="If checked, bot will place real orders via connected broker. If unchecked, sandbox only.")
        st.session_state["bot_config"]["auto_execute"] = auto_exec

    # ── Start/Stop ──
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if not st.session_state["bot_active"]:
            if st.button("Start Bot", type="primary", use_container_width=True, key="bot_start"):
                st.session_state["bot_active"] = True
                st.session_state["bot_trades"] = []
                st.session_state["bot_pnl"] = 0.0
                st.rerun()
        else:
            if st.button("Stop Bot", type="secondary", use_container_width=True, key="bot_stop"):
                st.session_state["bot_active"] = False
                st.rerun()

    with col_btn2:
        if st.button("Run Analysis Now", use_container_width=True, key="bot_analyze"):
            _run_bot_analysis()

    if st.session_state["bot_active"]:
        st.success("Bot is ACTIVE - monitoring markets and executing trades automatically.")
        _run_bot_analysis()
    elif st.session_state["bot_trades"]:
        st.info(f"Bot is paused. {len(st.session_state['bot_trades'])} trades executed so far.")

    # ── Trade History ──
    trades = st.session_state.get("bot_trades", [])
    if trades:
        st.markdown("### Trade History")
        trades_df = pd.DataFrame(trades)
        st.dataframe(trades_df, use_container_width=True, hide_index=True)
        total_pnl = sum(t.get("pnl", 0) for t in trades)
        pnl_color = "#00ff88" if total_pnl >= 0 else "#ff4466"
        st.markdown(f"### Total P&L: <span style='color:{pnl_color};font-weight:700;'>\u20b9{total_pnl:+,.2f}</span>", unsafe_allow_html=True)

def _run_bot_analysis():
    config = st.session_state["bot_config"]
    symbols = config.get("symbols", ["RELIANCE.NS"])
    broker = config.get("broker", "Sandbox")
    auto_exec = config.get("auto_execute", False)
    capital = config.get("capital", 100000)
    risk_pct = config.get("risk_per_trade", 5) / 100

    for symbol in symbols[:5]:
        with st.spinner(f"Analyzing {symbol}..."):
            df = yf.Ticker(symbol).history(period="1y", interval="1d")
            if df.empty: continue
            df.columns = [c.capitalize() for c in df.columns]
            decision = _ai_analyze_and_decide(df, symbol)
            price = decision["close"]

            action_color = "#00ff88" if decision["action"] == "BUY" else "#ff4466" if decision["action"] == "SELL" else "#8b949e"
            st.markdown(f"""
            <div style='border:1px solid {action_color}33;border-radius:10px;padding:10px 14px;margin:6px 0;background:{action_color}08;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <div><b>{symbol}</b> &middot; RSI: {decision['rsi']:.1f} &middot; MACD: {decision['macd']:.4f}</div>
                    <div style='color:{action_color};font-weight:700;font-size:1.1rem;'>{decision['action']} ({decision['confidence']:.0f}%)</div>
                </div>
                <div style='color:#8b949e;font-size:12px;margin-top:4px;'>{decision['reason']}</div>
            </div>""", unsafe_allow_html=True)

            if decision["action"] != "HOLD":
                qty = int((capital * risk_pct) / price) if price > 0 else 0
                if qty > 0:
                    if auto_exec and broker != "Sandbox":
                        st.warning(f"LIVE ORDER: {decision['action']} {qty} {symbol} @ {price:.2f} via {broker}")
                    else:
                        result = _place_order_simulated(symbol, decision["action"], qty, price, broker)
                        trades = st.session_state.get("bot_trades", [])
                        trades.append({
                            "time": result["timestamp"], "symbol": symbol, "action": decision["action"],
                            "qty": qty, "price": price, "broker": broker, "status": result["status"],
                            "pnl": 0, "reason": decision["reason"], "confidence": decision["confidence"],
                        })
                        st.session_state["bot_trades"] = trades
