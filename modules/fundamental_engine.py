"""Fundamental Engine — Yahoo Finance + Health Score (0-100)"""
import pandas as pd

def fetch_fundamentals(ticker):
    import yfinance as yf
    info = (yf.Ticker(ticker).info or {})
    return {"name":info.get("longName",ticker),"sector":info.get("sector","N/A"),
            "current_price":info.get("currentPrice") or info.get("regularMarketPrice"),
            "pe_ratio":info.get("trailingPE"),"forward_pe":info.get("forwardPE"),
            "pb_ratio":info.get("priceToBook"),"roe":info.get("returnOnEquity"),
            "debt_to_equity":info.get("debtToEquity"),"current_ratio":info.get("currentRatio"),
            "profit_margin":info.get("profitMargins"),"revenue_growth":info.get("revenueGrowth"),
            "earnings_growth":info.get("earningsGrowth"),"dividend_yield":info.get("dividendYield"),
            "market_cap":info.get("marketCap"),"beta":info.get("beta"),
            "52w_high":info.get("fiftyTwoWeekHigh"),"52w_low":info.get("fiftyTwoWeekLow")}

def _score_metric(value,good,bad,higher=True):
    if value is None: return 5.0
    if higher: return 10.0 if value>=good else 0.0 if value<=bad else 10*(value-bad)/(good-bad)
    else:      return 10.0 if value<=good else 0.0 if value>=bad  else 10*(bad-value)/(bad-good)

def calculate_health_score(data):
    roe_s    = _score_metric(data.get("roe"),          0.20,  0.0)
    margin_s = _score_metric(data.get("profit_margin"),0.15,  0.0)
    pe = data.get("pe_ratio"); pb = data.get("pb_ratio")
    pe_s = _score_metric(pe,15,40,False) if pe else 5.0
    pb_s = _score_metric(pb,3,8,False)   if pb else 5.0
    de_s = _score_metric(data.get("debt_to_equity"),50,200,False)
    cr_s = _score_metric(data.get("current_ratio"),1.5,0.5)
    rg_s = _score_metric(data.get("revenue_growth"),0.15,-0.10)
    eg_s = _score_metric(data.get("earnings_growth"),0.15,-0.10)
    score = round(((roe_s+margin_s)/2*0.30 + (pe_s+pb_s)/2*0.25 + (de_s+cr_s)/2*0.25 + (rg_s+eg_s)/2*0.20)*10,1)
    verdict = "Fundamentally Strong" if score>=75 else "Fundamentally Moderate" if score>=50 else "Fundamentally Weak"
    return {"health_score":score,"verdict":verdict,
            "breakdown":{"Profitability":round((roe_s+margin_s)/2*10,1),"Valuation":round((pe_s+pb_s)/2*10,1),
                         "Financial Health":round((de_s+cr_s)/2*10,1),"Growth":round((rg_s+eg_s)/2*10,1)}}

def run_fundamental_engine(ticker):
    try:
        raw = fetch_fundamentals(ticker)
        score = calculate_health_score(raw)
        return {"ok":True,"data":raw,"score":score}
    except Exception as e:
        return {"ok":False,"error":str(e)}
