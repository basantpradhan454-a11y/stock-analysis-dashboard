"""
Backtester
----------
Simulates the signal strategy on historical OHLC data with a starting cash
balance. No real orders — pure simulation for evaluating a strategy.
"""

import pandas as pd
from signals import generate_signals


def run_backtest(df: pd.DataFrame, initial_cash: float = 100000.0, qty_per_trade: int = 10) -> dict:
    sig_df = generate_signals(df).dropna(subset=["sma_slow"]).reset_index(drop=True)

    cash = initial_cash
    position = 0
    trades = []
    equity_curve = []

    for _, row in sig_df.iterrows():
        price = float(row["Close"])
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

    final_price = float(sig_df.iloc[-1]["Close"])
    final_equity = cash + position * final_price
    total_return_pct = ((final_equity - initial_cash) / initial_cash) * 100

    equity_series = pd.Series([e["equity"] for e in equity_curve])
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max * 100
    max_drawdown_pct = round(float(drawdown.min()), 2) if len(drawdown) else 0

    completed = [t for t in trades if t["action"] == "SELL"]
    wins = 0
    buy_price_stack = []
    for t in trades:
        if t["action"] == "BUY":
            buy_price_stack.append(t["price"])
        elif t["action"] == "SELL" and buy_price_stack:
            avg_buy = sum(buy_price_stack) / len(buy_price_stack)
            if t["price"] > avg_buy:
                wins += 1
            buy_price_stack = []

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
