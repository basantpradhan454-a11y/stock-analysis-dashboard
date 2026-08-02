"""
Trading Dashboard Backend
--------------------------
Run:  pip install fastapi uvicorn yfinance pandas numpy
      uvicorn main:app --reload --port 8000

Endpoints:
  GET /api/assets                       -> static/dynamic watchlist
  GET /api/ohlc/{ticker}?period=6mo&interval=1d   -> candlestick data from yfinance
  GET /api/analysis/{ticker}?period=6mo&interval=1d -> quant + technical summary
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import numpy as np

app = FastAPI(title="Trading Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ASSETS = [
    {"ticker": "AAPL", "name": "Apple Inc.", "type": "Stock"},
    {"ticker": "RELIANCE.NS", "name": "Reliance Industries", "type": "Stock (NSE)"},
    {"ticker": "TCS.NS", "name": "Tata Consultancy Services", "type": "Stock (NSE)"},
    {"ticker": "^NSEI", "name": "Nifty 50 Index", "type": "Index"},
    {"ticker": "BTC-USD", "name": "Bitcoin", "type": "Crypto"},
    {"ticker": "ETH-USD", "name": "Ethereum", "type": "Crypto"},
    {"ticker": "GC=F", "name": "Gold Futures", "type": "Commodity"},
]


@app.get("/api/assets")
def get_assets():
    return ASSETS


def fetch_ohlc(ticker: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    date_col = "Date" if "Date" in df.columns else "Datetime"
    df = df.rename(columns={date_col: "date"})
    return df


@app.get("/api/ohlc/{ticker}")
def get_ohlc(
    ticker: str,
    period: str = Query("6mo", description="1d,5d,1mo,3mo,6mo,1y,2y,5y,max"),
    interval: str = Query("1d", description="1m,5m,15m,1h,1d,1wk,1mo"),
):
    df = fetch_ohlc(ticker, period, interval)
    candles = [
        {
            "time": row["date"].strftime("%Y-%m-%d") if interval in ("1d", "1wk", "1mo") else row["date"].isoformat(),
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
        }
        for _, row in df.iterrows()
    ]
    return {"ticker": ticker, "candles": candles}


def compute_indicators(df: pd.DataFrame) -> dict:
    close = df["Close"]

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    daily_returns = close.pct_change().dropna()
    volatility = float(daily_returns.std() * np.sqrt(252) * 100)
    sharpe = float((daily_returns.mean() / daily_returns.std()) * np.sqrt(252)) if daily_returns.std() != 0 else 0

    last_close = float(close.iloc[-1])
    last_sma20 = float(sma20.iloc[-1]) if not pd.isna(sma20.iloc[-1]) else None
    last_sma50 = float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else None
    last_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
    last_macd = float(macd.iloc[-1])
    last_signal = float(signal.iloc[-1])

    high_52w = float(close.max())
    low_52w = float(close.min())

    return {
        "last_close": round(last_close, 2),
        "sma20": round(last_sma20, 2) if last_sma20 else None,
        "sma50": round(last_sma50, 2) if last_sma50 else None,
        "rsi14": round(last_rsi, 2) if last_rsi else None,
        "macd": round(last_macd, 4),
        "macd_signal": round(last_signal, 4),
        "volatility_annualized_pct": round(volatility, 2),
        "sharpe_ratio": round(sharpe, 2),
        "period_high": round(high_52w, 2),
        "period_low": round(low_52w, 2),
    }


def build_summary(ind: dict) -> dict:
    trend = "uptrend" if ind["sma20"] and ind["last_close"] > ind["sma20"] else "downtrend"
    if ind["sma20"] and ind["sma50"]:
        trend_strength = "strong" if (ind["sma20"] > ind["sma50"]) == (trend == "uptrend") else "weak/mixed"
    else:
        trend_strength = "insufficient data"

    rsi = ind["rsi14"]
    if rsi is None:
        rsi_state = "not enough data"
    elif rsi > 70:
        rsi_state = "overbought"
    elif rsi < 30:
        rsi_state = "oversold"
    else:
        rsi_state = "neutral"

    macd_state = "bullish crossover" if ind["macd"] > ind["macd_signal"] else "bearish crossover"

    quant_text = (
        f"Annualized volatility is {ind['volatility_annualized_pct']}%, with a Sharpe ratio of "
        f"{ind['sharpe_ratio']}. Price is trading between a period low of {ind['period_low']} and "
        f"high of {ind['period_high']}, currently at {ind['last_close']}."
    )

    technical_text = (
        f"Price is in a {trend} ({trend_strength}) relative to the 20/50-day SMA "
        f"({ind['sma20']}/{ind['sma50']}). RSI(14) is at {rsi} ({rsi_state}). "
        f"MACD ({ind['macd']}) vs signal ({ind['macd_signal']}) indicates a {macd_state}."
    )

    overall_summary = (
        f"Overall bias leans {'bullish' if trend == 'uptrend' and ind['macd'] > ind['macd_signal'] else 'cautious/bearish' if trend == 'downtrend' and ind['macd'] < ind['macd_signal'] else 'mixed'}. "
        f"RSI suggests {rsi_state} conditions, so {'watch for a pullback before entry' if rsi_state=='overbought' else 'watch for reversal confirmation' if rsi_state=='oversold' else 'no extreme momentum signal currently'}. "
        f"Use the period range ({ind['period_low']}\u2013{ind['period_high']}) as reference support/resistance."
    )

    return {"quant": quant_text, "technical": technical_text, "summary": overall_summary}


@app.get("/api/analysis/{ticker}")
def get_analysis(
    ticker: str,
    period: str = Query("6mo"),
    interval: str = Query("1d"),
):
    df = fetch_ohlc(ticker, period, interval)
    df = df.set_index("date")
    indicators = compute_indicators(df)
    summary = build_summary(indicators)
    return {"ticker": ticker, "indicators": indicators, "analysis": summary}


@app.get("/")
def root():
    return {"status": "ok", "message": "Trading dashboard API is running"}
