"""FinsageAI - Live Portfolio Tracker v2
Track multiple assets, Live P&L, Add Position, Price Alerts.
Data: yfinance (stocks/NSE) + CoinGecko (crypto)
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import time
from datetime import datetime

GECKO_IDS = {
    "BTC":"bitcoin","ETH":"ethereum","BNB":"binancecoin","SOL":"solana",
    "XRP":"ripple","ADA":"cardano","AVAX":"avalanche-2","MATIC":"matic-network",
    "DOGE":"dogecoin","SHIB":"shiba-inu","PEPE":"pepe","FLOKI":"floki",
    "BONK":"bonk","WIF":"dogwifcoin","LINK":"chainlink","DOT":"polkadot",
    "ATOM":"cosmos","UNI":"uniswap","LTC":"litecoin","BCH":"bitcoin-cash",
}

ASSET_CATEGORIES = {
    "NSE India": [("RELIANCE","RELIANCE.NS"),("TCS","TCS.NS"),("INFY","INFY.NS"),("HDFC Bank","HDFCBANK.NS"),("ICICI Bank","ICICIBANK.NS"),("WIPRO","WIPRO.NS"),("ADANI ENT","ADANIENT.NS"),("BAJFINANCE","BAJFINANCE.NS")],
    "US Stocks": [("Apple","AAPL"),("Tesla","TSLA"),("NVIDIA","NVDA"),("Google","GOOGL"),("Microsoft","MSFT"),("Amazon","AMZN"),("Meta","META"),("Netflix","NFLX")],
    "Crypto": [("Bitcoin","BTC"),("Ethereum","ETH"),("BNB","BNB"),("Solana","SOL"),("XRP","XRP"),("ADA","ADA"),("AVAX","AVAX"),("DOGE","DOGE")],
    "Meme": [("SHIB","SHIB"),("PEPE","PEPE"),("FLOKI","FLOKI"),("BONK","BONK"),("WIF","WIF")],
}

def _get_live_price(sym):
    sym_up = sym.upper().replace("-USD","").replace("-USDT","")
    if sym_up in GECKO_IDS:
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price", params={"ids": GECKO_IDS[sym_up], "vs_currencies":"usd"}, timeout=8)
            return r.json()[GECKO_IDS[sym_up]]["usd"]
        except: return None
    try:
        h = yf.Ticker(sym).history(period="1d")
        return float(h["Close"].iloc[-1]) if not h.empty else None
    except: return None

def _fmt_price(p):
    if p < 0.0001: return f"${p:.8f}"
    if p < 0.01: return f"${p:.6f}"
    if p < 1: return f"${p:.4f}"
    return f"${p:,.2f}"

def _init_portfolio():
    for k, v in [("pf_holdings",[]),("pf_alerts",[]),("pf_live_px",{}),("pf_last_refresh",0),("pf_txn_log",[])]:
        if k not in st.session_state: st.session_state[k] = v

def _refresh_prices(force=False):
    now = time.time()
    if force or (now - st.session_state.get("pf_last_refresh",0)) > 60:
        for h in st.session_state.get("pf_holdings",[]):
            px = _get_live_price(h["symbol"])
            if px: st.session_state["pf_live_px"][h["symbol"]] = round(px, 8)
        st.session_state["pf_last_refresh"] = now

def _add_position(symbol, qty, avg_price, notes="", txn_type="BUY"):
    symbol = symbol.upper().strip()
    holdings = st.session_state["pf_holdings"]
    existing = next((h for h in holdings if h["symbol"]==symbol), None)
    if existing:
        if txn_type == "BUY":
            total_qty = existing["qty"] + qty
            new_avg = (existing["qty"]*existing["avg_price"] + qty*avg_price)/total_qty
            existing["qty"] = round(total_qty,8); existing["avg_price"] = round(new_avg,8)
            msg = f"Updated {symbol} - avg: {_fmt_price(new_avg)}, qty: {total_qty:.6f}"
        else:
            if qty > existing["qty"]: return False, f"Cant sell {qty} - only have {existing['qty']} {symbol}"
            existing["qty"] = round(existing["qty"]-qty,8)
            if existing["qty"] <= 0: st.session_state["pf_holdings"] = [h for h in holdings if h["symbol"]!=symbol]
            msg = f"Sold {qty} {symbol}"
    else:
        if txn_type == "SELL": return False, f"{symbol} not in portfolio"
        holdings.append({"symbol":symbol,"qty":round(qty,8),"avg_price":round(avg_price,8),"notes":notes,"added_at":datetime.now().strftime("%Y-%m-%d %H:%M")})
        msg = f"Added {qty} {symbol} @ {_fmt_price(avg_price)}"
    st.session_state["pf_txn_log"].append({"time":datetime.now().strftime("%Y-%m-%d %H:%M"),"type":txn_type,"symbol":symbol,"qty":qty,"price":avg_price,"notes":notes})
    return True, msg

def render_portfolio_tracker():
    _init_portfolio()
    tab_port, tab_add, tab_alerts, tab_log = st.tabs(["My Portfolio","Add/Sell","Price Alerts","Transaction Log"])
    with tab_port:
        holdings = st.session_state.get("pf_holdings",[])
        if not holdings:
            st.info("Portfolio is empty. Go to Add/Sell tab.")
            return
        if st.button("Refresh Prices", key="pf_refresh"):
            _refresh_prices(force=True); st.rerun()
        _refresh_prices()
        rows = []
        for h in holdings:
            sym, qty, avg = h["symbol"], h["qty"], h["avg_price"]
            live = st.session_state["pf_live_px"].get(sym, avg)
            invested, current = qty*avg, qty*live
            pnl, pnl_pct = current-invested, (live/avg-1)*100 if avg>0 else 0
            rows.append({"Symbol":sym,"Qty":qty,"Avg Price":avg,"Live Price":live,"Invested":round(invested,2),"Current Val":round(current,2),"P&L ($)":round(pnl,2),"P&L %":round(pnl_pct,2),"Notes":h.get("notes","")})
        df = pd.DataFrame(rows)
        tot_inv = df["Invested"].sum(); tot_cur = df["Current Val"].sum()
        tot_pnl = tot_cur-tot_inv; tot_pct = (tot_pnl/tot_inv*100) if tot_inv>0 else 0
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Invested", f"${tot_inv:,.2f}")
        m2.metric("Current Value", f"${tot_cur:,.2f}")
        m3.metric("Total P&L", f"${tot_pnl:+,.2f}")
        m4.metric("Return", f"{tot_pct:+.2f}%")
        st.dataframe(df.drop(columns=["Notes"]), use_container_width=True, hide_index=True)
        rem = st.selectbox("Remove position:", ["-"]+[h["symbol"] for h in holdings], key="pf_rem")
        if st.button("Remove", key="pf_rem_btn") and rem != "-":
            st.session_state["pf_holdings"] = [h for h in holdings if h["symbol"]!=rem]; st.rerun()
        if len(df) > 0:
            c1, c2 = st.columns(2)
            with c1:
                fig = go.Figure(go.Pie(labels=df["Symbol"], values=df["Current Val"], hole=0.45))
                fig.update_layout(height=280, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                colors = ["#00ff88" if v>=0 else "#ff4466" for v in df["P&L ($)"]]
                fig2 = go.Figure(go.Bar(x=df["Symbol"], y=df["P&L ($)"], marker_color=colors))
                fig2.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0), showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

    with tab_add:
        st.markdown("#### Add or Sell a Position")
        txn_type = st.radio("Type", ["BUY / Add","SELL / Reduce"], horizontal=True, key="pf_txn_type")
        is_buy = "BUY" in txn_type
        new_sym = st.text_input("Symbol", placeholder="e.g. AAPL, RELIANCE.NS, BTC", key="pf_add_sym").upper().strip()
        cat = st.selectbox("Or pick category", ["-"]+list(ASSET_CATEGORIES.keys()), key="pf_cat")
        if cat != "-":
            assets = ASSET_CATEGORIES[cat]
            cols = st.columns(min(4, len(assets)))
            for i, (name, sym) in enumerate(assets):
                with cols[i % len(cols)]:
                    if st.button(f"{name}\n`{sym}`", key=f"pf_cat_{sym}"):
                        new_sym = sym
        if new_sym:
            if st.button("Fetch Live Price", key="pf_fetch"):
                lp = _get_live_price(new_sym)
                if lp: st.session_state["pf_fetched_price"] = lp; st.success(f"Live: {_fmt_price(lp)}")
                else: st.error("Could not fetch price.")
        fetched = st.session_state.get("pf_fetched_price", 0.0)
        q1, q2 = st.columns(2)
        with q1: new_qty = st.number_input("Quantity", min_value=0.0000001, value=1.0, step=0.1, format="%.6f", key="pf_add_qty")
        with q2:
            dp = fetched if fetched > 0 else 100.0
            new_avg = st.number_input(f"{'Buy' if is_buy else 'Sell'} Price", min_value=0.000001, value=float(dp), step=0.01, format="%.6f", key="pf_add_avg")
        notes = st.text_input("Notes (optional)", key="pf_notes")
        if st.button(f"{'Add' if is_buy else 'Sell'} Position", type="primary", key="pf_add_btn") and new_sym and new_qty > 0:
            ok, msg = _add_position(new_sym, new_qty, new_avg, notes, "BUY" if is_buy else "SELL")
            if ok: st.success(msg)
            else: st.error(msg)

    with tab_alerts:
        st.markdown("#### Price Alerts")
        alerts = st.session_state.get("pf_alerts", [])
        a1, a2, a3 = st.columns(3)
        with a1: al_sym = st.text_input("Symbol", key="al_sym")
        with a2: al_price = st.number_input("Target Price", value=0.0, key="al_price")
        with a3: al_dir = st.selectbox("Direction", ["Above", "Below"], key="al_dir")
        if st.button("Add Alert", key="al_add") and al_sym:
            alerts.append({"symbol": al_sym.upper(), "price": al_price, "dir": al_dir})
            st.session_state["pf_alerts"] = alerts
            st.success(f"Alert added for {al_sym.upper()}")
        for i, a in enumerate(alerts):
            live = _get_live_price(a["symbol"])
            triggered = (a["dir"]=="Above" and live and live>=a["price"]) or (a["dir"]=="Below" and live and live<=a["price"])
            if triggered: st.error(f"ALERT: {a['symbol']} {a['dir']} {a['price']} - Current: {live}")
            else: st.info(f"{a['symbol']} {a['dir']} {a['price']} - Current: {live or 'N/A'}")
            if st.button("Remove", key=f"al_rm_{i}"):
                alerts.pop(i); st.session_state["pf_alerts"] = alerts; st.rerun()

    with tab_log:
        st.markdown("#### Transaction Log")
        log = st.session_state.get("pf_txn_log", [])
        if log:
            st.dataframe(pd.DataFrame(log), use_container_width=True, hide_index=True)
        else:
            st.info("No transactions yet.")
