"""
Signal Engine
-------------
Rule-based buy/sell/hold signal generator using SMA crossover + RSI + MACD.
This is a STRATEGY, not financial advice — tune thresholds before relying on it.
"""

import pandas as pd
import numpy as np


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sma_fast"] = df["Close"].rolling(20).mean()
    df["sma_slow"] = df["Close"].rolling(50).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    return df


def generate_signals(df: pd.DataFrame, rsi_buy=40, rsi_sell=65) -> pd.DataFrame:
    """
    Rules:
      BUY  = sma_fast > sma_slow (uptrend) AND rsi < rsi_buy (not overbought) AND macd > macd_signal
      SELL = sma_fast < sma_slow (downtrend) OR rsi > rsi_sell OR macd < macd_signal
      HOLD = otherwise
    """
    df = add_indicators(df)
    df["signal"] = "HOLD"

    buy_cond = (df["sma_fast"] > df["sma_slow"]) & (df["rsi"] < rsi_buy) & (df["macd"] > df["macd_signal"])
    sell_cond = (df["sma_fast"] < df["sma_slow"]) | (df["rsi"] > rsi_sell) | (df["macd"] < df["macd_signal"])

    df.loc[buy_cond, "signal"] = "BUY"
    df.loc[sell_cond & ~buy_cond, "signal"] = "SELL"

    return df


def latest_signal(df: pd.DataFrame) -> dict:
    sig_df = generate_signals(df)
    last = sig_df.iloc[-1]
    return {
        "signal": last["signal"],
        "close": round(float(last["Close"]), 2),
        "sma_fast": round(float(last["sma_fast"]), 2) if not pd.isna(last["sma_fast"]) else None,
        "sma_slow": round(float(last["sma_slow"]), 2) if not pd.isna(last["sma_slow"]) else None,
        "rsi": round(float(last["rsi"]), 2) if not pd.isna(last["rsi"]) else None,
        "macd": round(float(last["macd"]), 4),
        "macd_signal": round(float(last["macd_signal"]), 4),
    }
