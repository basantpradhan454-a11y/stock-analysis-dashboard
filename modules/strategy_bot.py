"""FinSage AI - Strategy Demo Bot
User describes a trading strategy -> AI parses it -> deterministic backtest -> AI narrates results.
DEMO / PAPER TRADING only. No real money.
"""

import streamlit as st
import yfinance as yf
from modules.data_fetch import get_history
import pandas as pd
import numpy as np
import json
import os
import re
from datetime import datetime

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

def _get_key(name):
    v = os.environ.get(name, "")
    if not v:
        try:
            v = st.secrets.get(name, "")
        except Exception:
            pass
    return v or ""

def GROQ_API_KEY():
    return _get_key("GROQ_API_KEY") or _get_key("GROW_API_KEY")

def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def _rsi(s, n=14):
    d = s.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
    ag = g.ewm(com=n-1, min_periods=n).mean()
    al = l.ewm(com=n-1, min_periods=n).mean()
    return 100 - 100/(1 + ag/al.replace(0, np.nan))

def _macd(s, f=12, sl=26, sig=9):
    m = _ema(s, f) - _ema(s, sl)
    return m, _ema(m, sig)

STRATEGY_PARSE_SYSTEM = """You are a trading strategy parser. Convert the user's plain-language strategy description into a structured JSON strategy object.
Return ONLY valid JSON. If stop loss or take profit is NOT mentioned, set is_complete=false.
indicators: RSI, EMA, SMA, MACD, Bollinger Bands, VWAP, ATR, Stochastic. Return ONLY JSON."""

NARRATION_SYSTEM = """You are a trading educator narrating a strategy backtest in Hinglish.
Return JSON with segments array. Be honest about weaknesses."""

def _call_groq(messages, max_tokens=2000, temperature=0.3):
    import urllib.request
    api_key = GROQ_API_KEY()
    if not api_key:
        return None
    payload = json.dumps({"model": GROQ_MODEL, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(GROQ_URL, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"Groq API error: {e}")
        return None

def parse_strategy_text(text):
    if not GROQ_API_KEY():
        return _rule_parse_strategy(text)
    messages = [{"role": "system", "content": STRATEGY_PARSE_SYSTEM}, {"role": "user", "content": f"Parse this strategy: {text}"}]
    raw = _call_groq(messages, max_tokens=1500, temperature=0.2)
    if not raw:
        return _rule_parse_strategy(text)
    try:
        start = raw.find("{"); end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except json.JSONDecodeError:
        pass
    return _rule_parse_strategy(text)

def _rule_parse_strategy(text):
    t = text.lower()
    strategy = {"strategy_name": "Custom Strategy", "timeframe": "1d", "entry_conditions": [], "exit_conditions": [], "filters": [], "risk_rules": {"stop_loss_pct": 0, "take_profit_pct": 0, "position_size_pct": 95}, "indicators_needed": [], "is_complete": True, "missing_fields": [], "clarification_questions": []}
    if "rsi" in t:
        m = re.search(r'rsi\s*(?:below|<|less than|under)\s*(\d+)', t)
        if m: strategy["entry_conditions"].append({"indicator": "RSI", "operator": "<", "value": int(m.group(1)), "description": f"RSI below {m.group(1)}"})
        m2 = re.search(r'rsi\s*(?:above|>|greater than|over)\s*(\d+)', t)
        if m2: strategy["exit_conditions"].append({"indicator": "RSI", "operator": ">", "value": int(m2.group(1)), "description": f"RSI above {m2.group(1)}"})
        strategy["indicators_needed"].append("RSI")
    if "ema" in t or "moving average" in t:
        em = re.search(r'ema\s*(\d+)', t); period = int(em.group(1)) if em else 200
        strategy["filters"].append({"indicator": "EMA", "period": period, "operator": ">", "reference": "price", "description": f"Price above EMA {period}"})
        strategy["indicators_needed"].append(f"EMA{period}")
    if "macd" in t:
        strategy["entry_conditions"].append({"indicator": "MACD", "operator": "crosses_above", "value": "signal", "description": "MACD crosses above signal"})
        strategy["exit_conditions"].append({"indicator": "MACD", "operator": "crosses_below", "value": "signal", "description": "MACD crosses below signal"})
        strategy["indicators_needed"].append("MACD")
    sl = re.search(r'stop.?loss\s*(?:of|at)?\s*(\d+(?:\.\d+)?)\s*%', t)
    if sl: strategy["risk_rules"]["stop_loss_pct"] = float(sl.group(1))
    else: strategy["is_complete"] = False; strategy["missing_fields"].append("stop_loss"); strategy["clarification_questions"].append("What stop-loss percentage would you like?")
    tp = re.search(r'(?:take.?profit|target)\s*(?:of|at)?\s*(\d+(?:\.\d+)?)\s*%', t)
    if tp: strategy["risk_rules"]["take_profit_pct"] = float(tp.group(1))
    return strategy

def run_strategy_backtest(df, strategy, initial_capital=100000):
    if df.empty or len(df) < 50:
        return {"error": "Insufficient data (need 50+ candles)"}
    c = df["Close"].copy()
    signals = pd.Series(0, index=df.index)
    indicators_data = {}
    needed = strategy.get("indicators_needed", [])
    if any("RSI" in n for n in needed): indicators_data["RSI"] = _rsi(c)
    if any("MACD" in n for n in needed):
        macd, sig = _macd(c); indicators_data["MACD"] = macd; indicators_data["MACD_Signal"] = sig
    for n in needed:
        em = re.match(r'EMA(\d+)', n); sm = re.match(r'SMA(\d+)', n)
        if em: indicators_data[f"EMA{em.group(1)}"] = _ema(c, int(em.group(1)))
        if sm: indicators_data[f"SMA{sm.group(1)}"] = c.rolling(int(sm.group(1))).mean()

    for cond in strategy.get("entry_conditions", []):
        ind, op, val = cond.get("indicator",""), cond.get("operator",""), cond.get("value",0)
        if ind == "RSI" and "RSI" in indicators_data:
            if op == "<": signals[indicators_data["RSI"] < val] = 1
            elif op == ">": signals[indicators_data["RSI"] > val] = 1
        elif ind == "MACD" and "MACD" in indicators_data:
            m, s = indicators_data["MACD"], indicators_data["MACD_Signal"]
            if op == "crosses_above": signals[(m > s) & (m.shift() <= s.shift())] = 1
    for cond in strategy.get("exit_conditions", []):
        ind, op, val = cond.get("indicator",""), cond.get("operator",""), cond.get("value",0)
        if ind == "RSI" and "RSI" in indicators_data:
            if op == ">": signals[indicators_data["RSI"] > val] = -1
        elif ind == "MACD" and "MACD" in indicators_data:
            m, s = indicators_data["MACD"], indicators_data["MACD_Signal"]
            if op == "crosses_below": signals[(m < s) & (m.shift() >= s.shift())] = -1
    for filt in strategy.get("filters", []):
        ind, period = filt.get("indicator",""), filt.get("period",200)
        if ind == "EMA" and f"EMA{period}" in indicators_data:
            signals[(signals == 1) & (c < indicators_data[f"EMA{period}"])] = 0

    risk = strategy.get("risk_rules", {})
    sl_pct, tp_pct = risk.get("stop_loss_pct",0), risk.get("take_profit_pct",0)
    pos_pct = risk.get("position_size_pct",95)/100
    cash, position, entry_px, entry_date = initial_capital, 0.0, 0.0, None
    trades, equity, in_trade, markers = [], [], False, []

    for i, (ts, row) in enumerate(df.iterrows()):
        price = float(row["Close"]); sig = int(signals.iloc[i])
        if in_trade and entry_px > 0:
            exit_reason = None
            if sl_pct > 0 and price <= entry_px*(1-sl_pct/100): exit_reason = "Stop Loss"
            elif tp_pct > 0 and price >= entry_px*(1+tp_pct/100): exit_reason = "Take Profit"
            if exit_reason:
                pnl = (price-entry_px)*position; cash += position*price
                trades.append({"entry_date": entry_date.strftime("%Y-%m-%d"), "exit_date": ts.strftime("%Y-%m-%d"), "entry_price": round(entry_px,4), "exit_price": round(price,4), "units": round(position,4), "pnl": round(pnl,2), "pnl_pct": round((price/entry_px-1)*100,2), "exit_reason": exit_reason, "entry_index": df.index.get_loc(entry_date), "exit_index": i})
                markers.append({"type":"exit","index":i,"price":price,"reason":exit_reason,"pnl":round(pnl,2)})
                position, in_trade, entry_px = 0, False, 0
        if sig == 1 and not in_trade and cash > 0:
            invest = cash*pos_pct; position = invest/price; cash -= invest; entry_px = price; entry_date = ts; in_trade = True
            markers.append({"type":"entry","index":i,"price":price,"reason":"Signal"})
        elif sig == -1 and in_trade:
            pnl = (price-entry_px)*position; cash += position*price
            trades.append({"entry_date": entry_date.strftime("%Y-%m-%d"), "exit_date": ts.strftime("%Y-%m-%d"), "entry_price": round(entry_px,4), "exit_price": round(price,4), "units": round(position,4), "pnl": round(pnl,2), "pnl_pct": round((price/entry_px-1)*100,2), "exit_reason":"Signal Exit","entry_index": df.index.get_loc(entry_date),"exit_index":i})
            markers.append({"type":"exit","index":i,"price":price,"reason":"Signal","pnl":round(pnl,2)})
            position, in_trade, entry_px = 0, False, 0
        equity.append({"date": ts.strftime("%Y-%m-%d"), "equity": round(cash+(position*price if in_trade else 0), 2)})

    if in_trade and entry_px > 0:
        fp = float(df["Close"].iloc[-1]); pnl = (fp-entry_px)*position; cash += position*fp
        trades.append({"entry_date": entry_date.strftime("%Y-%m-%d"), "exit_date": df.index[-1].strftime("%Y-%m-%d"), "entry_price": round(entry_px,4), "exit_price": round(fp,4), "units": round(position,4), "pnl": round(pnl,2), "pnl_pct": round((fp/entry_px-1)*100,2), "exit_reason":"End of Data","entry_index": df.index.get_loc(entry_date),"exit_index": len(df)-1})

    total = len(trades); wins = [t for t in trades if t["pnl"]>0]; losses = [t for t in trades if t["pnl"]<=0]
    wr = (len(wins)/total*100) if total else 0
    aw = np.mean([t["pnl"] for t in wins]) if wins else 0
    al = np.mean([t["pnl"] for t in losses]) if losses else 0
    tpnl = sum(t["pnl"] for t in trades)
    tr = ((cash-initial_capital)/initial_capital*100) if initial_capital else 0
    eqv = [e["equity"] for e in equity]; peak = eqv[0] if eqv else initial_capital; mdd = 0
    for ev in eqv:
        if ev > peak: peak = ev
        dd = (peak-ev)/peak*100
        if dd > mdd: mdd = dd
    rr = abs(aw/al) if al != 0 else 0

    return {"trades": trades, "markers": markers, "equity_curve": equity, "stats": {"total_trades": total, "wins": len(wins), "losses": len(losses), "win_rate": round(wr,2), "avg_win": round(aw,2), "avg_loss": round(al,2), "total_pnl": round(tpnl,2), "total_return": round(tr,2), "max_drawdown": round(mdd,2), "risk_reward": round(rr,2), "initial_capital": initial_capital, "final_capital": round(cash,2)}, "indicators_data": {}}


def render_strategy_bot():
    st.markdown("## Strategy Demo Bot")
    st.caption("Describe a strategy in plain language -> AI parses -> deterministic backtest. DEMO ONLY.")
    col_input, col_type = st.columns([4,1])
    with col_type:
        input_type = st.radio("Input", ["Plain Language", "Pine Script"], horizontal=True, key="sb_type")
    with col_input:
        strategy_text = st.text_area("Describe your strategy", placeholder="e.g. Buy when RSI below 30, sell when RSI above 70, stop loss 5%, take profit 10%", height=100, key="sb_text")
    if st.button("Parse Strategy", type="primary", use_container_width=True, key="sb_parse"):
        if not strategy_text.strip(): st.warning("Please enter a strategy."); return
        with st.spinner("AI parsing..."):
            parsed = parse_strategy_text(strategy_text) if input_type == "Plain Language" else _rule_parse_strategy(strategy_text)
        st.session_state["sb_parsed"] = parsed
    parsed = st.session_state.get("sb_parsed")
    if not parsed: return
    st.markdown("### Parsed Strategy")
    st.json(parsed)
    if not parsed.get("is_complete", True):
        st.warning("Strategy incomplete. Please clarify:")
        for q in parsed.get("clarification_questions", []): st.markdown(f"- {q}")
        return
    st.markdown("### Backtest Config")
    bc1, bc2, bc3 = st.columns(3)
    with bc1: bt_symbol = st.text_input("Symbol", value="RELIANCE.NS", key="sb_symbol")
    with bc2: bt_period = st.selectbox("Period", ["1y","2y","5y","10y","max"], index=3, key="sb_period")
    with bc3: bt_capital = st.number_input("Capital", value=100000, step=10000, key="sb_capital")
    if st.button("Run Backtest", type="primary", use_container_width=True, key="sb_run"):
        with st.spinner(f"Fetching {bt_period} data..."):
            df, is_synthetic = get_history(bt_symbol, period=bt_period, interval="1d")
            if df is None or df.empty: st.error(f"No data for {bt_symbol}"); return
            if is_synthetic: st.caption("\u26a0\ufe0f Live feed rate-limited \u2014 showing simulated candles.")
            df.columns = [c.capitalize() for c in df.columns]
        with st.spinner("Running backtest..."):
            result = run_strategy_backtest(df, parsed, initial_capital=bt_capital)
        if result.get("error"): st.error(result["error"]); return
        st.session_state["sb_result"] = result
    result = st.session_state.get("sb_result")
    if not result: return
    stats = result["stats"]
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("Total Return", f"{stats['total_return']:+.2f}%")
    s2.metric("Win Rate", f"{stats['win_rate']:.1f}%")
    s3.metric("Trades", stats["total_trades"])
    s4.metric("Max DD", f"{stats['max_drawdown']:.2f}%")
    if result["trades"]:
        st.markdown("### Trade Log")
        st.dataframe(pd.DataFrame(result["trades"]), use_container_width=True, hide_index=True)
