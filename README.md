# 📊 Stock Analysis Dashboard

A Streamlit-based stock analysis dashboard with candlestick charts, technical indicators (RSI, MACD, Bollinger Bands, SMA), candlestick pattern detection, and trend analysis.

## Features

- **8 Indian stocks** (RELIANCE, TCS, HDFCBANK, INFY, ITC, TATAMOTORS, SBIN, BHARTIARTL)
- **Candlestick chart** with SMA 20/50 overlays and Bollinger Bands
- **Volume chart** with average volume line
- **RSI (14)** with overbought/oversold zones
- **MACD (12, 26, 9)** with histogram
- **Cumulative return trend** chart
- **Candlestick pattern detection** (Doji, Hammer, Shooting Star, Bullish/Bearish Engulfing, Morning Star)
- **Signal summary** — bullish vs bearish bias verdict
- **Volatility & Sharpe-like ratio** calculations
- **Broker selection** UI (Zerodha, Upstox, Angel One, Fyers, Generic)
- **Seeded random data** — same stock always generates the same candles

## Tech Stack

- **Streamlit** — web framework
- **Plotly** — interactive charts
- **Pandas / NumPy** — data manipulation & calculations

## Local Development

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/stock-analysis-dashboard.git
cd stock-analysis-dashboard

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Select this repository
5. Set the main file path to `app.py`
6. Click **Deploy**

That's it! Your app will be live on a public URL.

## Data Disclaimer

All stock data is **simulated** using a seeded PRNG for educational purposes. This is **not financial advice**.
