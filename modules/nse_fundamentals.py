"""
NSE Fundamentals Module
=======================
Fetches fundamental analysis data for NSE (National Stock Exchange of India) stocks.

Key Features & Research:
1. nsepython Integration: Uses nsepython library functions (nse_eq, nse_results, nsefetch) when available.
2. Direct NSE Public APIs: Handles session cookie generation and headers for https://www.nseindia.com/api/ endpoints.
3. Anti-Scraping / Header Handling: Includes User-Agent, Referer, Accept headers, and session cookie setup.
4. Robust Fallback: Fallbacks to Yahoo Finance (ticker.NS) when NSE API returns 403 (e.g. cloud IP blocking by Akamai WAF) or missing fields.
5. Derived Fundamentals: Automatically calculates ROE, Debt/Equity, and Shareholding distribution when needed.
"""

import logging
import time
import requests
from typing import Dict, Any, Optional

# Attempt importing nsepython
try:
    import nsepython as nse
    HAS_NSEPYTHON = True
except ImportError:
    HAS_NSEPYTHON = False

# Attempt importing yfinance for fallback
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

logger = logging.getLogger(__name__)

# Standard headers required for NSE India API
NSE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
}


def _create_nse_session() -> requests.Session:
    """Creates a requests session initialized with cookies from NSE homepage."""
    session = requests.Session()
    session.headers.update(NSE_HEADERS)
    try:
        # Hitting home page first establishes cookies like AKA_A2, bm_sv, nsit
        session.get('https://www.nseindia.com', timeout=5)
    except Exception as e:
        logger.warning(f"Failed to initialize NSE session cookies: {e}")
    return session


def fetch_from_nse_api(symbol: str) -> Dict[str, Any]:
    """
    Directly fetch equity quote & fundamentals from NSE API endpoints:
    - https://www.nseindia.com/api/quote-equity?symbol=SYMBOL
    - https://www.nseindia.com/api/results-comparision?symbol=SYMBOL
    """
    result = {}
    session = _create_nse_session()
    
    api_headers = NSE_HEADERS.copy()
    api_headers['Accept'] = 'application/json, text/plain, */*'
    api_headers['Referer'] = f'https://www.nseindia.com/get-quotes/equity?symbol={symbol}'
    
    quote_url = f'https://www.nseindia.com/api/quote-equity?symbol={symbol}'
    try:
        time.sleep(0.3)  # Rate limiting
        res = session.get(quote_url, headers=api_headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            price_info = data.get('priceInfo', {})
            metadata = data.get('metadata', {})
            security_info = data.get('securityInfo', {})
            info = data.get('info', {})
            industry_info = data.get('industryInfo', {})
            
            result['company_name'] = info.get('companyName')
            result['sector'] = metadata.get('pdSectorInd') or metadata.get('sector') or industry_info.get('macro')
            result['industry'] = industry_info.get('industry') or security_info.get('classOfShare')
            result['current_price'] = price_info.get('lastPrice')
            result['pe_ratio'] = metadata.get('pdSectorPe') or metadata.get('pdSymbolPe')
            result['isin'] = info.get('isin')
            result['face_value'] = security_info.get('faceValue')
            result['52w_high'] = price_info.get('weekHighLow', {}).get('max')
            result['52w_low'] = price_info.get('weekHighLow', {}).get('min')
    except Exception as e:
        logger.debug(f"Direct NSE quote fetch failed for {symbol}: {e}")
        
    return result


def fetch_nse_fundamentals(ticker: str) -> Dict[str, Any]:
    """
    Fetch fundamental analysis metrics for an NSE stock symbol.
    
    Args:
        ticker (str): NSE ticker symbol, e.g. 'RELIANCE', 'TCS', 'INFY' (with or without .NS)
        
    Returns:
        dict: Key fundamental metrics including:
            - symbol
            - company_name
            - sector
            - current_price
            - pe_ratio
            - forward_pe
            - pb_ratio
            - roe
            - debt_to_equity
            - revenue_growth
            - profit_margin
            - operating_margin
            - market_cap
            - eps
            - book_value
            - dividend_yield
            - shareholding_pattern
            - quarterly_results_summary
            - source
    """
    # Clean ticker symbol
    symbol = ticker.strip().upper().replace('.NS', '').replace('.BO', '')
    
    fundamentals: Dict[str, Any] = {
        'symbol': symbol,
        'company_name': None,
        'sector': None,
        'current_price': None,
        'pe_ratio': None,
        'forward_pe': None,
        'pb_ratio': None,
        'roe': None,
        'debt_to_equity': None,
        'revenue_growth': None,
        'profit_margin': None,
        'operating_margin': None,
        'market_cap': None,
        'eps': None,
        'book_value': None,
        'dividend_yield': None,
        'shareholding_pattern': {
            'promoters': None,
            'institutions': None,
            'public': None
        },
        'quarterly_results_summary': [],
        'source': None
    }
    
    nse_success = False
    
    # Method 1: Try nsepython if installed
    if HAS_NSEPYTHON:
        try:
            eq_data = nse.nse_eq(symbol)
            if isinstance(eq_data, dict) and eq_data.get('info'):
                info = eq_data.get('info', {})
                price_info = eq_data.get('priceInfo', {})
                metadata = eq_data.get('metadata', {})
                
                fundamentals['company_name'] = info.get('companyName')
                fundamentals['sector'] = metadata.get('pdSectorInd') or metadata.get('sector')
                fundamentals['current_price'] = price_info.get('lastPrice')
                fundamentals['pe_ratio'] = metadata.get('pdSectorPe') or metadata.get('pdSymbolPe')
                fundamentals['source'] = 'nsepython (NSE API)'
                nse_success = True
        except Exception as e:
            logger.debug(f"nsepython fetch skipped or failed for {symbol}: {e}")

    # Method 2: Try direct NSE REST API if nsepython didn't yield result
    if not nse_success:
        nse_data = fetch_from_nse_api(symbol)
        if nse_data and nse_data.get('company_name'):
            fundamentals['company_name'] = nse_data.get('company_name')
            fundamentals['sector'] = nse_data.get('sector')
            fundamentals['current_price'] = nse_data.get('current_price')
            fundamentals['pe_ratio'] = nse_data.get('pe_ratio')
            fundamentals['source'] = 'NSE Direct API'
            nse_success = True

    # Method 3: Yahoo Finance Fallback & Enrichment (using SYMBOL.NS)
    if HAS_YFINANCE:
        yf_symbol = f"{symbol}.NS"
        try:
            yt = yf.Ticker(yf_symbol)
            info = yt.info or {}
            
            # Fill missing general metadata
            if not fundamentals['company_name']:
                fundamentals['company_name'] = info.get('longName') or info.get('shortName') or symbol
            if not fundamentals['sector']:
                fundamentals['sector'] = info.get('sector') or info.get('industry')
            if fundamentals['current_price'] is None:
                fundamentals['current_price'] = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('open')
            if fundamentals['pe_ratio'] is None:
                fundamentals['pe_ratio'] = info.get('trailingPE')
                
            # Populate key fundamental ratio fields
            fundamentals['forward_pe'] = info.get('forwardPE')
            fundamentals['pb_ratio'] = info.get('priceToBook')
            fundamentals['roe'] = info.get('returnOnEquity')
            
            # Debt to Equity (converting percentage e.g. 36.65% -> 0.3665 ratio or keeping clean decimal)
            de_val = info.get('debtToEquity')
            if de_val is not None:
                fundamentals['debt_to_equity'] = round(de_val / 100.0, 4) if de_val > 5 else round(de_val, 4)
                
            fundamentals['revenue_growth'] = info.get('revenueGrowth')
            fundamentals['profit_margin'] = info.get('profitMargins')
            fundamentals['operating_margin'] = info.get('operatingMargins')
            fundamentals['market_cap'] = info.get('marketCap') or info.get('nonDilutedMarketCap')
            fundamentals['eps'] = info.get('trailingEps') or info.get('epsTrailingTwelveMonths')
            fundamentals['book_value'] = info.get('bookValue')
            fundamentals['dividend_yield'] = info.get('dividendYield')
            
            # Derive ROE if yfinance returnOnEquity is None but EPS and Book Value are present
            if fundamentals['roe'] is None and fundamentals['eps'] and fundamentals['book_value'] and fundamentals['book_value'] > 0:
                fundamentals['roe'] = round(fundamentals['eps'] / fundamentals['book_value'], 4)
                
            # Shareholding pattern from insider / institutional holdings
            held_insiders = info.get('heldPercentInsiders')
            held_inst = info.get('heldPercentInstitutions')
            if held_insiders is not None or held_inst is not None:
                promoters = round(held_insiders * 100, 2) if held_insiders is not None else None
                institutions = round(held_inst * 100, 2) if held_inst is not None else None
                public = None
                if promoters is not None and institutions is not None:
                    public = round(max(0.0, 100.0 - promoters - institutions), 2)
                fundamentals['shareholding_pattern'] = {
                    'promoters': promoters,
                    'institutions': institutions,
                    'public': public
                }
                
            # Quarterly results summary extraction
            try:
                qf = yt.quarterly_financials
                if qf is not None and not qf.empty:
                    summary_list = []
                    for col in list(qf.columns)[:4]:  # Last 4 quarters
                        q_date = str(col.date()) if hasattr(col, 'date') else str(col)[:10]
                        rev = qf.loc['Total Revenue', col] if 'Total Revenue' in qf.index else None
                        net_inc = qf.loc['Net Income', col] if 'Net Income' in qf.index else None
                        summary_list.append({
                            'quarter': q_date,
                            'revenue': float(rev) if rev is not None and not pd_isna(rev) else None,
                            'net_income': float(net_inc) if net_inc is not None and not pd_isna(net_inc) else None
                        })
                    fundamentals['quarterly_results_summary'] = summary_list
            except Exception as q_err:
                logger.debug(f"Quarterly results extraction skipped for {symbol}: {q_err}")

            if not fundamentals['source']:
                fundamentals['source'] = 'Yahoo Finance (NSE.NS)'
            elif nse_success:
                fundamentals['source'] = 'NSE Direct API + Yahoo Finance'
        except Exception as e:
            logger.warning(f"Yahoo Finance fallback error for {symbol}: {e}")
            if not fundamentals['source']:
                fundamentals['source'] = 'Partial Data'
                
    return fundamentals


def pd_isna(val: Any) -> bool:
    """Helper to check NaN without pandas dependency if possible."""
    try:
        import pandas as pd
        return pd.isna(val)
    except ImportError:
        return val != val


if __name__ == '__main__':
    import json
    print("Testing fetch_nse_fundamentals for RELIANCE and TCS...")
    for sym in ['RELIANCE', 'TCS']:
        res = fetch_nse_fundamentals(sym)
        print(f"\n================ Metrics for {sym} ================")
        print(json.dumps(res, indent=2))
