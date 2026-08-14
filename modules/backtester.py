"""FinSageAI - Strategy Backtesting Engine
Test RSI, MACD, EMA, BB strategies on real historical data.
"""

import streamlit as st
import yfinance as yf
from modules.data_fetch import get_history
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

def _ema(s, n): return s.ewm(span=n, adjust=False).mean()
def _rsi(s, n=14):
    d = s.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
    ag = g.ewm(com=n-1, min_periods=n).mean(); al = l.ewm(com=n-1, min_periods=n).mean()
    return 100 - 100/(1 + ag/al.replace(0, np.nan))
def _macd(s, f=12, sl=26, sig=9):
    m = _ema(s, f) - _ema(s, sl); return m, _ema(m, sig)
def _bb(s, n=20, k=2):
    m = s.rolling(n).mean(); sd = s.rolling(n).std(); return m+k*sd, m, m-k*sd

STRATEGIES = {
    "RSI Reversal": {"desc": "Buy when RSI < 30 (oversold). Sell when RSI > 70 (overbought).", "params": {"rsi_buy": 30, "rsi_sell": 70}},
    "MACD Crossover": {"desc": "Buy when MACD crosses above Signal. Sell on opposite crossover.", "params": {}},
    "EMA Crossover (9/21)": {"desc": "Buy when EMA9 crosses above EMA21. Sell on opposite.", "params": {}},
    "EMA Golden/Death Cross (50/200)": {"desc": "Golden Cross (EMA50>EMA200) = Buy. Death Cross = Sell.", "params": {}},
    "Bollinger Band Bounce": {"desc": "Buy at lower BB. Sell at upper BB.", "params": {}},
    "RSI + MACD Combo": {"desc": "Buy when RSI < 40 AND MACD > Signal. Sell when RSI > 60 AND MACD < Signal.", "params": {"rsi_buy": 40}},
}

@st.cache_data(ttl=600, show_spinner=False)
def _fetch_data(sym, period, interval):
    df, is_synthetic = get_history(sym, period=period, interval=interval)
    if df is None or df.empty: return pd.DataFrame()
    df.index = pd.to_datetime(df.index)
    df.attrs["synthetic"] = is_synthetic
    return df

def _max_drawdown(equity):
    peak = equity.cummax(); dd = (equity - peak) / peak * 100; return float(dd.min())

def _sharpe(equity, rf=0.0):
    returns = equity.pct_change().dropna()
    if returns.std() == 0: return 0.0
    return float((returns.mean() - rf/252) / returns.std() * np.sqrt(252))

def _run_backtest(df, strategy, params, initial_capital=100000, position_pct=0.95, stop_loss_pct=0.0, take_profit_pct=0.0):
    if df.empty or len(df) < 50: return {"error": "Insufficient data"}
    c = df["Close"].copy()
    signals = pd.Series(0, index=df.index)

    if strategy == "RSI Reversal":
        rsi = _rsi(c)
        signals[rsi < params.get("rsi_buy", 30)] = 1
        signals[rsi > params.get("rsi_sell", 70)] = -1
    elif strategy == "MACD Crossover":
        macd, sig = _macd(c)
        signals[(macd > sig) & (macd.shift() <= sig.shift())] = 1
        signals[(macd < sig) & (macd.shift() >= sig.shift())] = -1
    elif strategy == "EMA Crossover (9/21)":
        e9, e21 = _ema(c, 9), _ema(c, 21)
        signals[(e9 > e21) & (e9.shift() <= e21.shift())] = 1
        signals[(e9 < e21) & (e9.shift() >= e21.shift())] = -1
    elif strategy == "EMA Golden/Death Cross (50/200)":
        e50, e200 = _ema(c, 50), _ema(c, 200)
        signals[(e50 > e200) & (e50.shift() <= e200.shift())] = 1
        signals[(e50 < e200) & (e50.shift() >= e200.shift())] = -1
    elif strategy == "Bollinger Band Bounce":
        bb_u, bb_m, bb_l = _bb(c)
        signals[c <= bb_l] = 1
        signals[c >= bb_u] = -1
    elif strategy == "RSI + MACD Combo":
        rsi = _rsi(c); macd, sig = _macd(c)
        signals[(rsi < params.get("rsi_buy", 40)) & (macd > sig)] = 1
        signals[(rsi > 60) & (macd < sig)] = -1

    cash, position, entry_px, entry_date, trades, equity, in_trade = initial_capital, 0.0, 0.0, None, [], [], False

    for i, (ts, row) in enumerate(df.iterrows()):
        price = float(row["Close"]); sig = int(signals.iloc[i])
        if in_trade and entry_px > 0:
            if stop_loss_pct > 0 and price <= entry_px * (1 - stop_loss_pct/100):
                pnl = (price-entry_px)*position; cash += position*price
                trades.append({"Entry Date": entry_date.strftime("%Y-%m-%d"), "Exit Date": ts.strftime("%Y-%m-%d"), "Entry Price": round(entry_px,4), "Exit Price": round(price,4), "Units": round(position,4), "PnL ($)": round(pnl,2), "PnL %": round((price/entry_px-1)*100,2), "Exit Reason": "Stop Loss"})
                position, in_trade, entry_px = 0, False, 0
            elif take_profit_pct > 0 and price >= entry_px * (1 + take_profit_pct/100):
                pnl = (price-entry_px)*position; cash += position*price
                trades.append({"Entry Date": entry_date.strftime("%Y-%m-%d"), "Exit Date": ts.strftime("%Y-%m-%d"), "Entry Price": round(entry_px,4), "Exit Price": round(price,4), "Units": round(position,4), "PnL ($)": round(pnl,2), "PnL %": round((price/entry_px-1)*100,2), "Exit Reason": "Take Profit"})
                position, in_trade, entry_px = 0, False, 0
        if sig == 1 and not in_trade and cash > 0:
            invest = cash*position_pct; position = invest/price; cash -= invest; entry_px = price; entry_date = ts; in_trade = True
        elif sig == -1 and in_trade:
            pnl = (price-entry_px)*position; cash += position*price
            trades.append({"Entry Date": entry_date.strftime("%Y-%m-%d"), "Exit Date": ts.strftime("%Y-%m-%d"), "Entry Price": round(entry_px,4), "Exit Price": round(price,4), "Units": round(position,4), "PnL ($)": round(pnl,2), "PnL %": round((price/entry_px-1)*100,2), "Exit Reason": "Signal"})
            position, in_trade, entry_px = 0, False, 0
        equity.append({"Date": ts, "Equity": round(cash + position*price, 2), "Price": round(price, 4)})

    if in_trade and position > 0:
        price = float(df["Close"].iloc[-1]); pnl = (price-entry_px)*position; cash += position*price
        trades.append({"Entry Date": entry_date.strftime("%Y-%m-%d"), "Exit Date": df.index[-1].strftime("%Y-%m-%d"), "Entry Price": round(entry_px,4), "Exit Price": round(price,4), "Units": round(position,4), "PnL ($)": round(pnl,2), "PnL %": round((price/entry_px-1)*100,2), "Exit Reason": "Period End"})

    equity_df = pd.DataFrame(equity).set_index("Date")
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    final_equity = float(equity_df["Equity"].iloc[-1]) if not equity_df.empty else initial_capital
    total_return = (final_equity / initial_capital - 1) * 100
    bh_return = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[0]) - 1) * 100

    if not trades_df.empty:
        wins = trades_df[trades_df["PnL ($)"] > 0]; losses = trades_df[trades_df["PnL ($)"] <= 0]
        win_rate = len(wins)/len(trades_df)*100
        avg_win = wins["PnL ($)"].mean() if len(wins) else 0
        avg_loss = losses["PnL ($)"].mean() if len(losses) else 0
        pf = abs(wins["PnL ($)"].sum()/losses["PnL ($)"].sum()) if losses["PnL ($)"].sum() != 0 else float("inf")
        max_dd = _max_drawdown(equity_df["Equity"])
        sharpe = _sharpe(equity_df["Equity"])
    else:
        win_rate = avg_win = avg_loss = pf = max_dd = sharpe = 0

    return {"equity_df": equity_df, "trades_df": trades_df, "initial": initial_capital, "final": round(final_equity,2), "total_return": round(total_return,2), "bh_return": round(bh_return,2), "n_trades": len(trades_df) if not trades_df.empty else 0, "win_rate": round(win_rate,1), "avg_win": round(avg_win,2), "avg_loss": round(avg_loss,2), "profit_factor": round(pf,2) if pf != float("inf") else "inf", "max_drawdown": round(max_dd,2), "sharpe": round(sharpe,2), "alpha": round(total_return-bh_return,2), "error": None}


def render_backtester():
    st.markdown("## Strategy Backtester")
    st.caption("Test predefined strategies on real historical data. Pure deterministic backtesting.")

    c1, c2, c3 = st.columns(3)
    with c1: sym = st.text_input("Symbol", value="RELIANCE.NS", key="bt_sym")
    with c2: strategy = st.selectbox("Strategy", list(STRATEGIES.keys()), key="bt_strat")
    with c3: period = st.selectbox("Period", ["1y","2y","5y","10y","max"], index=3, key="bt_period")

    st.info(f"**{strategy}:** {STRATEGIES[strategy]['desc']}")

    with st.expander("Advanced Settings"):
        a1, a2, a3, a4 = st.columns(4)
        with a1: capital = st.number_input("Initial Capital", 1000, 10000000, 100000, step=1000, key="bt_cap")
        with a2: pos_pct = st.slider("Position Size %", 10, 100, 95, key="bt_pos")
        with a3: sl_pct = st.number_input("Stop Loss %", 0.0, 50.0, 0.0, step=0.5, key="bt_sl", help="0 = disabled")
        with a4: tp_pct = st.number_input("Take Profit %", 0.0, 200.0, 0.0, step=1.0, key="bt_tp", help="0 = disabled")
        if "RSI" in strategy:
            p1, p2 = st.columns(2)
            with p1: STRATEGIES[strategy]["params"]["rsi_buy"] = st.slider("RSI Buy", 10, 50, 30, key="bt_rbuy")
            with p2: STRATEGIES[strategy]["params"]["rsi_sell"] = st.slider("RSI Sell", 50, 90, 70, key="bt_rsell")

    if st.button("Run Backtest", type="primary", use_container_width=True, key="bt_run"):
        with st.spinner(f"Running {strategy} on {sym} ({period})..."):
            df_raw = _fetch_data(sym, period, "1d")
            if df_raw.empty: st.error(f"No data for {sym}"); return
            result = _run_backtest(df_raw, strategy, STRATEGIES[strategy]["params"], initial_capital=capital, position_pct=pos_pct/100, stop_loss_pct=sl_pct, take_profit_pct=tp_pct)
        if result.get("error"): st.error(result["error"]); return
        st.session_state["bt_result"] = result
        st.session_state["bt_df_raw"] = df_raw

    result = st.session_state.get("bt_result")
    if not result: st.info("Configure strategy and click Run Backtest."); return

    total_ret = result["total_return"]
    ret_color = "#00ff88" if total_ret > 0 else "#ff4466"
    alpha = result["alpha"]
    alpha_col = "#00ff88" if alpha > 0 else "#ff4466"

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Strategy Return", f"{total_ret:+.1f}%")
    m2.metric("Buy & Hold", f"{result['bh_return']:+.1f}%")
    m3.metric("Alpha", f"{alpha:+.1f}%")
    m4.metric("Win Rate", f"{result['win_rate']:.1f}%")

    m5,m6,m7,m8 = st.columns(4)
    m5.metric("Final", f"\u20b9{result['final']:,.0f}", delta=f"{total_ret:+.1f}%")
    m6.metric("Trades", result["n_trades"])
    m7.metric("Max DD", f"{result['max_drawdown']:.1f}%")
    m8.metric("Sharpe", result["sharpe"])

    tab_eq, tab_tr = st.tabs(["Equity Curve", "Trade Log"])
    with tab_eq:
        eq_df = result["equity_df"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=eq_df.index, y=eq_df["Equity"], name="Strategy", line=dict(color="#00ff88", width=2.5), fill="tozeroy", fillcolor="rgba(0,255,136,0.05)"))
        bh = (result["equity_df"]["Price"] / float(result["equity_df"]["Price"].iloc[0])) * result["initial"]
        fig.add_trace(go.Scatter(x=eq_df.index, y=bh, name="Buy & Hold", line=dict(color="#4a9eff", width=1.5, dash="dot")))
        fig.update_layout(height=380, margin=dict(l=0,r=0,t=10,b=0), hovermode="x unified", dragmode="zoom")
        st.plotly_chart(fig, use_container_width=True, config={
            "scrollZoom": True, "doubleClick": "reset", "modeBarButtonsToAdd": ["drawline", "eraseshape"], "displayModeBar": True, "displaylogo": False,
            "responsive": True, "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
        })

    with tab_tr:
        trades_df = result["trades_df"]
        if trades_df.empty: st.warning("No completed trades.")
        else: st.dataframe(trades_df, use_container_width=True, hide_index=True)
