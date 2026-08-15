"""Fundamental Engine — NSE + Trendlyne + Yahoo Finance with Health Score (0-100)"""
import pandas as pd
import requests
import re

def _try_nse_data(ticker):
    """Try fetching fundamentals from NSE India API (using nse_fundamentals module)."""
    try:
        from modules.nse_fundamentals import fetch_nse_fundamentals
        symbol = ticker.replace(".NS", "").replace(".BO", "")
        if ticker.startswith("^"):
            return {}
        result = fetch_nse_fundamentals(symbol)
        if result and isinstance(result, dict):
            return result
    except Exception:
        pass
    # Fallback: direct API call
    try:
        symbol = ticker.replace(".NS", "").replace(".BO", "")
        if ticker.startswith("^"):
            return {}
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        session.get("https://www.nseindia.com", timeout=10)
        url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            metadata = data.get("metadata", {})
            industry_info = data.get("industryInfo", {})
            return {
                "nse_sector": industry_info.get("industry", "N/A"),
                "nse_market_cap": metadata.get("marketCap") if isinstance(metadata.get("marketCap"), (int, float)) else None,
            }
    except Exception:
        pass
    return {}


def _try_trendlyne_data(ticker):
    """Try scraping fundamentals from Trendlyne."""
    try:
        import bs4
        symbol = ticker.replace(".NS", "").replace(".BO", "")
        if ticker.startswith("^"):
            return {}
        url = f"https://trendlyne.com/equity/{symbol}/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = bs4.BeautifulSoup(resp.text, "lxml")
            data = {}
            # Try to find key metrics in the page
            for row in soup.find_all("div", class_="col-6"):
                text = row.get_text(strip=True)
                if "P/E" in text and ":" in text:
                    val = text.split(":")[-1].strip()
                    try:
                        data["pe_ratio"] = float(val.replace(",", ""))
                    except ValueError:
                        pass
                elif "P/B" in text and ":" in text:
                    val = text.split(":")[-1].strip()
                    try:
                        data["pb_ratio"] = float(val.replace(",", ""))
                    except ValueError:
                        pass
                elif "ROE" in text and ":" in text:
                    val = text.split(":")[-1].strip().replace("%", "")
                    try:
                        data["roe"] = float(val) / 100
                    except ValueError:
                        pass
                elif "Margin" in text and ":" in text:
                    val = text.split(":")[-1].strip().replace("%", "")
                    try:
                        data["profit_margin"] = float(val) / 100
                    except ValueError:
                        pass
            return data
    except Exception:
        pass
    return {}


def fetch_fundamentals(ticker):
    """Fetch fundamentals from NSE, Trendlyne, and Yahoo Finance (merged)."""
    import yfinance as yf
    
    # Start with Yahoo Finance (most reliable)
    info = (yf.Ticker(ticker).info or {})
    data = {
        "name": info.get("longName", ticker),
        "sector": info.get("sector", "N/A"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "pb_ratio": info.get("priceToBook"),
        "roe": info.get("returnOnEquity"),
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "profit_margin": info.get("profitMargins"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "dividend_yield": info.get("dividendYield"),
        "market_cap": info.get("marketCap"),
        "beta": info.get("beta"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
    }
    
    # Try to enrich with NSE data
    try:
        nse_data = _try_nse_data(ticker)
        if nse_data:
            if nse_data.get("nse_sector") and data["sector"] == "N/A":
                data["sector"] = nse_data["nse_sector"]
            if nse_data.get("nse_market_cap") and not data.get("market_cap"):
                data["market_cap"] = nse_data["nse_market_cap"]
            data["nse_source"] = True
    except Exception:
        pass
    
    # Try to enrich with Trendlyne data
    try:
        tl_data = _try_trendlyne_data(ticker)
        if tl_data:
            if tl_data.get("pe_ratio") and not data.get("pe_ratio"):
                data["pe_ratio"] = tl_data["pe_ratio"]
            if tl_data.get("pb_ratio") and not data.get("pb_ratio"):
                data["pb_ratio"] = tl_data["pb_ratio"]
            if tl_data.get("roe") and not data.get("roe"):
                data["roe"] = tl_data["roe"]
            if tl_data.get("profit_margin") and not data.get("profit_margin"):
                data["profit_margin"] = tl_data["profit_margin"]
            data["trendlyne_source"] = True
    except Exception:
        pass
    
    return data


def _score_metric(value, good, bad, higher=True):
    if value is None:
        return 5.0
    if higher:
        return 10.0 if value >= good else 0.0 if value <= bad else 10 * (value - bad) / (good - bad)
    else:
        return 10.0 if value <= good else 0.0 if value >= bad else 10 * (bad - value) / (bad - good)


def calculate_health_score(data):
    roe_s = _score_metric(data.get("roe"), 0.20, 0.0)
    margin_s = _score_metric(data.get("profit_margin"), 0.15, 0.0)
    pe = data.get("pe_ratio")
    pb = data.get("pb_ratio")
    pe_s = _score_metric(pe, 15, 40, False) if pe else 5.0
    pb_s = _score_metric(pb, 3, 8, False) if pb else 5.0
    de_s = _score_metric(data.get("debt_to_equity"), 50, 200, False)
    cr_s = _score_metric(data.get("current_ratio"), 1.5, 0.5)
    rg_s = _score_metric(data.get("revenue_growth"), 0.15, -0.10)
    eg_s = _score_metric(data.get("earnings_growth"), 0.15, -0.10)
    score = round(((roe_s + margin_s) / 2 * 0.30 + (pe_s + pb_s) / 2 * 0.25 + (de_s + cr_s) / 2 * 0.25 + (rg_s + eg_s) / 2 * 0.20) * 10, 1)
    verdict = "Fundamentally Strong" if score >= 75 else "Fundamentally Moderate" if score >= 50 else "Fundamentally Weak"
    return {
        "health_score": score,
        "verdict": verdict,
        "breakdown": {
            "Profitability": round((roe_s + margin_s) / 2 * 10, 1),
            "Valuation": round((pe_s + pb_s) / 2 * 10, 1),
            "Financial Health": round((de_s + cr_s) / 2 * 10, 1),
            "Growth": round((rg_s + eg_s) / 2 * 10, 1),
        },
        "sources": [k for k in ["nse_source", "trendlyne_source"] if data.get(k)],
    }


def run_fundamental_engine(ticker):
    try:
        raw = fetch_fundamentals(ticker)
        score = calculate_health_score(raw)
        return {"ok": True, "data": raw, "score": score}
    except Exception as e:
        return {"ok": False, "error": str(e)}
