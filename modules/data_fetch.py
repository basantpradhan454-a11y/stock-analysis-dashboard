"""
Centralized, crash-proof market data fetching.

Yahoo Finance aggressively rate-limits shared IPs (Streamlit Cloud runs many
apps behind the same egress IPs), which used to raise yfinance.exceptions.
YFRateLimitError straight through the app and crash it. Every fetch in this
app now goes through get_history()/get_download() below, which:

  1. Throttles requests app-wide (min gap between real Yahoo Finance calls).
  2. Retries briefly on any error (including rate limits).
  3. Falls back to deterministic seeded synthetic candles (same technique the
     README already promises: "same stock always generates the same candles")
     instead of ever raising into the UI.

Callers get back (df, is_synthetic) so they can show a small "simulated data"
notice when the fallback kicked in.
"""

import time
import numpy as np
import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

_MIN_GAP_SECONDS = 1.2  # app-wide minimum gap between real Yahoo Finance calls
_last_call_ts = {"t": 0.0}

_PERIOD_TO_BARS = {
    "1d": 1, "5d": 5, "1mo": 22, "3mo": 66, "6mo": 130,
    "1y": 252, "2y": 504, "5y": 1260, "10y": 2520, "ytd": 160, "max": 2520}


def _throttle():
    now = time.time()
    wait = _MIN_GAP_SECONDS - (now - _last_call_ts["t"])
    if wait > 0:
        time.sleep(wait)
    _last_call_ts["t"] = time.time()


def _seeded_rand(seed):
    state = [seed % 233280 or 1]

    def rand():
        state[0] = (state[0] * 9301 + 49297) % 233280
        return state[0] / 233280

    return rand


def synthetic_ohlcv(symbol, period="1y", interval="1d"):
    """Deterministic synthetic OHLCV, shaped exactly like yfinance's raw output
    (DatetimeIndex + Open/High/Low/Close/Volume columns). Same symbol always
    produces the same candles."""
    n = _PERIOD_TO_BARS.get(period, 180)
    if interval not in ("1d", "1wk", "1mo"):
        n = min(n * 2, 500)  # rough bump for intraday intervals

    seed = (sum(ord(c) for c in symbol) * 97 + 42) % 233280
    rand = _seeded_rand(seed)
    price = 80 + (seed % 500)
    trend = 0.0
    rows = []
    end = pd.Timestamp.today().normalize()
    dates = pd.bdate_range(end=end, periods=n)
    for i in range(n):
        trend += (rand() - 0.5) * 0.35
        trend = max(-3.0, min(3.0, trend))
        drift = trend * 0.3 + np.sin(i / 14) * 0.6
        vol = 1.1 + rand() * 1.6
        o = price
        c = o + drift + (rand() - 0.5) * vol
        h = max(o, c) + rand() * vol * 0.6
        l = min(o, c) - rand() * vol * 0.6
        v = 1_200_000 + rand() * 3_800_000 + abs(c - o) * 900_000
        rows.append((o, h, l, c, v))
        price = c
    df = pd.DataFrame(
        rows, columns=["Open", "High", "Low", "Close", "Volume"],
        index=pd.DatetimeIndex(dates, name="Date"),
    )
    return df


@st.cache_data(ttl=300, show_spinner=False)
def get_history(symbol, period="1y", interval="1d"):
    """Safe replacement for yf.Ticker(symbol).history(...). Never raises."""
    if yf is not None:
        for attempt in range(2):
            try:
                _throttle()
                df = yf.Ticker(symbol).history(period=period, interval=interval)
                if df is not None and not df.empty:
                    return df, False
            except Exception:
                time.sleep(0.8 * (attempt + 1))
    return synthetic_ohlcv(symbol, period, interval), True


@st.cache_data(ttl=300, show_spinner=False)
def get_download(symbol, period="1y", interval="1d"):
    """Safe replacement for yf.download(...). Never raises."""
    if yf is not None:
        for attempt in range(2):
            try:
                _throttle()
                df = yf.download(symbol, period=period, interval=interval,
                                  progress=False, auto_adjust=True)
                if df is not None and not df.empty:
                    return df, False
            except Exception:
                time.sleep(0.8 * (attempt + 1))
    return synthetic_ohlcv(symbol, period, interval), True


def synthetic_notice(container=st):
    """Small, consistent banner to show whenever fallback data was used."""
    container.caption(
        "⚠️ Live feed rate-limited by Yahoo Finance right now — showing "
        "deterministic simulated candles so the app keeps working. Real data "
        "will resume automatically once the limit clears."
    )
