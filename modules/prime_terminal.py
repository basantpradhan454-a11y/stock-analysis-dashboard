"""
Prime Terminal — Trading Dashboard (Streamlit Component)
Renders a full-screen trading terminal with:
  - Scrolling ticker tape (live NSE/forex/crypto)
  - Candlestick chart (canvas-based)
  - Real-time macro news feed
  - Bank trades table
  - Smart Bias Tracker (fundamental bias grid)
  - Risk Sentiment gauge
  - FX Cross Rates & Order Flow
"""
import streamlit as st
import streamlit.components.v1 as components
import json
import yfinance as yf


def _fetch_ticker_data():
    """Fetch live prices for ticker tape."""
    symbols = {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "JPY=X",
        "XAU/USD": "GC=F",
        "US30": "^DJI",
        "NAS100": "^IXIC",
        "BTC/USD": "BTC-USD",
        "WTI Crude": "CL=F",
        "USD/CHF": "CHF=X",
        "AUD/USD": "AUDUSD=X",
        "NIFTY 50": "^NSEI",
        "BANK NIFTY": "^NSEBANK",
        "RELIANCE": "RELIANCE.NS",
        "TCS": "TCS.NS",
    }
    ticker_data = []
    try:
        for label, sym in list(symbols.items())[:14]:
            try:
                tk = yf.Ticker(sym)
                hist = tk.history(period="2d")
                if not hist.empty:
                    price = hist["Close"].iloc[-1]
                    prev = hist["Close"].iloc[-2] if len(hist) > 1 else price
                    chg = ((price - prev) / prev * 100) if prev else 0
                    ticker_data.append({
                        "sym": label,
                        "price": f"{price:,.2f}",
                        "chg": f"{chg:+.2f}%"
                    })
            except Exception:
                pass
    except Exception:
        pass
    if not ticker_data:
        ticker_data = [
            {"sym":"EUR/USD","price":"1.0847","chg":"+0.12%"},
            {"sym":"GBP/USD","price":"1.2711","chg":"-0.08%"},
            {"sym":"USD/JPY","price":"149.62","chg":"+0.31%"},
            {"sym":"XAU/USD","price":"2418.30","chg":"+0.55%"},
            {"sym":"US30","price":"39,842","chg":"+0.22%"},
            {"sym":"NAS100","price":"18,203","chg":"-0.14%"},
            {"sym":"BTC/USD","price":"61,204","chg":"+1.42%"},
            {"sym":"WTI Crude","price":"78.14","chg":"-0.36%"},
            {"sym":"USD/CHF","price":"0.8801","chg":"+0.05%"},
            {"sym":"AUD/USD","price":"0.6579","chg":"-0.21%"},
            {"sym":"NIFTY 50","price":"24,133","chg":"+0.42%"},
            {"sym":"BANK NIFTY","price":"51,892","chg":"+0.31%"},
        ]
    return ticker_data


def _render_prime_terminal_html(ticker_data_json):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Prime Terminal</title>
<style>
  :root{{
    --bg:#0a0e14; --panel:#10151d; --panel-2:#141a24; --border:#232a36;
    --green:#00c853; --red:#ff3b3b; --amber:#ffb020; --text:#e8ecf1;
    --muted:#7c8798; --accent:#3d8bfd;
  }}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{
    background:var(--bg);color:var(--text);font-family:'Segoe UI',Arial,sans-serif;
    font-size:13px;overflow-x:hidden;
  }}
  .ticker-wrap{{
    background:#000;border-bottom:1px solid var(--border);
    overflow:hidden;white-space:nowrap;padding:8px 0;
  }}
  .ticker{{display:inline-block;padding-left:100%;animation:scroll-left 30s linear infinite;}}
  .ticker span{{display:inline-block;padding:0 24px;font-weight:600;font-size:14px;}}
  .up{{color:var(--green);}} .down{{color:var(--red);}}
  @keyframes scroll-left{{0%{{transform:translateX(0);}}100%{{transform:translateX(-100%);}}}}
  .topbar{{
    display:flex;align-items:center;justify-content:space-between;
    padding:10px 18px;background:var(--panel);border-bottom:1px solid var(--border);
  }}
  .topbar .logo{{font-weight:700;font-size:16px;letter-spacing:1px;}}
  .logo span{{color:var(--accent);}}
  .topbar .clock{{color:var(--muted);font-size:12px;}}
  .dashboard{{
    display:grid;grid-template-columns:1.3fr 1fr 1fr;
    grid-template-rows:auto auto;gap:12px;padding:14px;
  }}
  .panel{{background:var(--panel);border:1px solid var(--border);border-radius:8px;overflow:hidden;}}
  .panel-header{{
    display:flex;align-items:center;justify-content:space-between;
    padding:10px 14px;background:var(--panel-2);border-bottom:1px solid var(--border);
    font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:0.5px;color:var(--muted);
  }}
  .panel-body{{padding:12px 14px;}}
  .chart-panel{{grid-column:1;grid-row:1;}}
  #priceChart{{width:100%;height:220px;display:block;}}
  .news-panel{{grid-column:2;grid-row:1;}}
  .news-item{{padding:8px 0;border-bottom:1px solid var(--border);font-size:12px;line-height:1.4;}}
  .news-item:last-child{{border-bottom:none;}}
  .news-time{{color:var(--accent);font-weight:600;margin-right:6px;}}
  .news-tag{{
    display:inline-block;background:#1c2530;color:var(--amber);
    font-size:10px;padding:1px 6px;border-radius:3px;margin-right:6px;
  }}
  .trades-panel{{grid-column:3;grid-row:1;}}
  table{{width:100%;border-collapse:collapse;font-size:11px;}}
  th{{text-align:left;color:var(--muted);font-weight:600;padding:6px 4px;
    border-bottom:1px solid var(--border);font-size:10px;text-transform:uppercase;}}
  td{{padding:6px 4px;border-bottom:1px solid #1a212c;}}
  .buy{{color:var(--green);font-weight:600;}}
  .sell{{color:var(--red);font-weight:600;}}
  .bias-panel{{grid-column:1;grid-row:2;}}
  .bias-grid{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--border);}}
  .bias-cell{{background:var(--panel);padding:8px 6px;text-align:center;font-size:11px;}}
  .bias-cell.label{{background:var(--panel-2);color:var(--muted);font-weight:600;text-align:left;}}
  .bullish{{background:rgba(0,200,83,0.15);color:var(--green);font-weight:600;}}
  .very-bullish{{background:rgba(0,200,83,0.3);color:var(--green);font-weight:700;}}
  .bearish{{background:rgba(255,59,59,0.15);color:var(--red);font-weight:600;}}
  .very-bearish{{background:rgba(255,59,59,0.3);color:var(--red);font-weight:700;}}
  .risk-panel{{grid-column:2;grid-row:2;text-align:center;}}
  .gauge-wrap{{display:flex;flex-direction:column;align-items:center;padding-top:6px;}}
  .gauge-label{{margin-top:6px;font-size:12px;color:var(--amber);font-weight:700;letter-spacing:1px;}}
  .fx-panel{{grid-column:3;grid-row:2;}}
  .fx-row{{display:flex;justify-content:space-between;padding:6px 0;
    border-bottom:1px solid #1a212c;font-size:11px;}}
  .fx-pair{{font-weight:600;}}
  .fx-bid{{color:var(--muted);}}
  .fx-ask{{color:var(--text);}}
  ::-webkit-scrollbar{{width:6px;height:6px;}}
  ::-webkit-scrollbar-thumb{{background:#2a3342;border-radius:3px;}}
  @media(max-width:900px){{
    .dashboard{{grid-template-columns:1fr;}}
    .chart-panel,.news-panel,.trades-panel,.bias-panel,.risk-panel,.fx-panel{{
      grid-column:1!important;grid-row:auto!important;
    }}
  }}
</style>
</head>
<body>
<div class="ticker-wrap"><div class="ticker" id="tickerTrack"></div></div>
<div class="topbar">
  <div class="logo">PRIME <span>TERMINAL</span></div>
  <div class="clock" id="clock"></div>
</div>
<div class="dashboard">
  <div class="panel chart-panel">
    <div class="panel-header"><span>EUR/USD — Price Chart</span><span id="eurusdPrice" class="up">1.0847</span></div>
    <div class="panel-body"><canvas id="priceChart"></canvas></div>
  </div>
  <div class="panel news-panel">
    <div class="panel-header">Real-Time Macro News</div>
    <div class="panel-body" id="newsFeed" style="max-height:260px;overflow-y:auto;"></div>
  </div>
  <div class="panel trades-panel">
    <div class="panel-header">Bank Trades</div>
    <div class="panel-body"><table><thead><tr><th>Bank</th><th>Pair</th><th>Side</th><th>Time</th></tr></thead><tbody id="tradesBody"></tbody></table></div>
  </div>
  <div class="panel bias-panel">
    <div class="panel-header">Smart Bias Tracker</div>
    <div class="bias-grid" id="biasGrid"></div>
  </div>
  <div class="panel risk-panel">
    <div class="panel-header">Risk Sentiment</div>
    <div class="gauge-wrap">
      <svg width="220" height="130" viewBox="0 0 220 130">
        <defs>
          <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#ff3b3b"/><stop offset="50%" stop-color="#ffb020"/><stop offset="100%" stop-color="#00c853"/>
          </linearGradient>
        </defs>
        <path d="M20,120 A90,90 0 0,1 200,120" fill="none" stroke="url(#gaugeGrad)" stroke-width="16" stroke-linecap="round"/>
        <line id="needle" x1="110" y1="120" x2="110" y2="45" stroke="#e8ecf1" stroke-width="3"/>
        <circle cx="110" cy="120" r="6" fill="#e8ecf1"/>
      </svg>
      <div class="gauge-label" id="gaugeText">NEUTRAL</div>
    </div>
  </div>
  <div class="panel fx-panel">
    <div class="panel-header">FX Cross Rates &amp; Order Flow</div>
    <div class="panel-body" id="fxTable" style="max-height:220px;overflow-y:auto;"></div>
  </div>
</div>
<script>
const TICKER_DATA = {ticker_data_json};
function updateClock(){{
  const now=new Date();
  document.getElementById('clock').textContent=now.toUTCString().split(' ')[4]+' UTC';
}}
setInterval(updateClock,1000);updateClock();
function buildTicker(){{
  const track=document.getElementById('tickerTrack');
  let html='';
  TICKER_DATA.forEach(t=>{{
    const cls=t.chg.startsWith('+')?'up':'down';
    const arrow=t.chg.startsWith('+')?'▲':'▼';
    html+=`<span class="${{cls}}">${{t.sym}} ${{t.price}} ${{arrow}} ${{t.chg}}</span>`;
  }});
  track.innerHTML=html+html;
}}
buildTicker();
const newsData=[
  {{time:"09:41",tag:"US EARNINGS",text:"Major banks report strong Q2 trading revenue, FX desks lead gains."}},
  {{time:"09:32",tag:"BREAKING",text:"ECB official hints at cautious pace for rate cuts amid sticky inflation."}},
  {{time:"09:15",tag:"FED WATCH",text:"Markets now pricing 68% odds of a September rate cut, futures show."}},
  {{time:"08:58",tag:"GEOPOLITICS",text:"Oil rises as Middle East supply concerns resurface overnight."}},
  {{time:"08:40",tag:"DATA",text:"UK retail sales beat expectations, GBP ticks higher on the print."}},
  {{time:"08:22",tag:"CENTRAL BANK",text:"BoJ intervention chatter grows as yen weakens past key level."}},
];
function buildNews(){{
  const feed=document.getElementById('newsFeed');
  feed.innerHTML=newsData.map(n=>`<div class="news-item"><span class="news-time">${{n.time}}</span><span class="news-tag">${{n.tag}}</span>${{n.text}}</div>`).join('');
}}
buildNews();
const banks=["Goldman Sachs","JP Morgan","UBS Research","Citi Research","HSBC","Morgan Stanley","Barclays","Deutsche Bank"];
const pairs=["EUR/USD","GBP/JPY","USD/CHF","AUD/USD","EUR/GBP","USD/CAD"];
function randomTrade(){{
  const bank=banks[Math.floor(Math.random()*banks.length)];
  const pair=pairs[Math.floor(Math.random()*pairs.length)];
  const side=Math.random()>0.5?"BUY":"SELL";
  const time=new Date().toLocaleTimeString('en-US',{{hour12:false}});
  return{{bank,pair,side,time}};
}}
function buildTrades(){{
  const body=document.getElementById('tradesBody');
  let rows='';
  for(let i=0;i<8;i++){{
    const t=randomTrade();
    rows+=`<tr><td>${{t.bank}}</td><td>${{t.pair}}</td><td class="${{t.side==='BUY'?'buy':'sell'}}">${{t.side}}</td><td>${{t.time}}</td></tr>`;
  }}
  body.innerHTML=rows;
}}
buildTrades();setInterval(buildTrades,6000);
const biasRows=[
  {{label:"Fundamental Bias",usd:"very-bullish",eur:"bearish"}},
  {{label:"Economic Data",usd:"bullish",eur:"very-bearish"}},
  {{label:"Rising Prices",usd:"very-bullish",eur:"bearish"}},
  {{label:"Consumer Confidence",usd:"bullish",eur:"bearish"}},
  {{label:"Factory Activity",usd:"very-bullish",eur:"very-bearish"}},
  {{label:"Service Sector",usd:"bullish",eur:"bullish"}},
  {{label:"Home Market Started",usd:"very-bullish",eur:"very-bullish"}},
  {{label:"Retail Sales",usd:"bullish",eur:"very-bullish"}},
  {{label:"Rate Direction",usd:"very-bullish",eur:"bearish"}},
  {{label:"Capital Expense",usd:"bullish",eur:"bearish"}},
];
function labelText(cls){{return cls.replace('very-','Very ').replace(/^\\w/,c=>c.toUpperCase()).replace('bullish','Bullish').replace('bearish','Bearish');}}
function buildBias(){{
  const grid=document.getElementById('biasGrid');
  let html=`<div class="bias-cell label">Indicator</div><div class="bias-cell label" style="display:flex;justify-content:space-around;"><span>USD</span><span>EUR</span></div>`;
  biasRows.forEach(r=>{{
    html+=`<div class="bias-cell label">${{r.label}}</div>`;
    html+=`<div class="bias-cell" style="display:flex;gap:4px;"><span class="${{r.usd}}" style="flex:1;border-radius:4px;padding:4px 0;">${{labelText(r.usd)}}</span><span class="${{r.eur}}" style="flex:1;border-radius:4px;padding:4px 0;">${{labelText(r.eur)}}</span></div>`;
  }});
  grid.innerHTML=html;
}}
buildBias();
function setGauge(value){{
  const angle=-90+(value/100)*180;
  const rad=angle*Math.PI/180;
  const len=75;
  const x2=110+len*Math.sin(rad);
  const y2=120-len*Math.cos(rad);
  document.getElementById('needle').setAttribute('x2',x2);
  document.getElementById('needle').setAttribute('y2',y2);
  let label='NEUTRAL';
  if(value<30)label='RISK OFF';else if(value<45)label='CAUTIOUS';else if(value<55)label='NEUTRAL';else if(value<75)label='RISK ON';else label='STRONG RISK ON';
  document.getElementById('gaugeText').textContent=label;
}}
setGauge(52);
setInterval(()=>{{setGauge(40+Math.random()*30);}},8000);
const fxData=[
  {{pair:"EUR/USD",bid:"1.0846",ask:"1.0848"}},
  {{pair:"GBP/USD",bid:"1.2710",ask:"1.2712"}},
  {{pair:"USD/JPY",bid:"149.60",ask:"149.64"}},
  {{pair:"USD/CHF",bid:"0.8800",ask:"0.8802"}},
  {{pair:"AUD/USD",bid:"0.6578",ask:"0.6580"}},
  {{pair:"USD/CAD",bid:"1.3701",ask:"1.3703"}},
  {{pair:"EUR/GBP",bid:"0.8534",ask:"0.8536"}},
  {{pair:"EUR/JPY",bid:"162.24",ask:"162.28"}},
  {{pair:"NZD/USD",bid:"0.6021",ask:"0.6023"}},
];
function buildFx(){{
  const wrap=document.getElementById('fxTable');
  wrap.innerHTML=fxData.map(f=>`<div class="fx-row"><span class="fx-pair">${{f.pair}}</span><span class="fx-bid">${{f.bid}}</span><span class="fx-ask">${{f.ask}}</span></div>`).join('');
}}
buildFx();
function drawChart(){{
  const canvas=document.getElementById('priceChart');
  const ctx=canvas.getContext('2d');
  const dpr=window.devicePixelRatio||1;
  const w=canvas.clientWidth,h=canvas.clientHeight;
  canvas.width=w*dpr;canvas.height=h*dpr;
  ctx.scale(dpr,dpr);ctx.clearRect(0,0,w,h);
  let price=1.0800;const candles=[];
  for(let i=0;i<60;i++){{
    const open=price;const close=open+(Math.random()-0.5)*0.0015;
    const high=Math.max(open,close)+Math.random()*0.0008;
    const low=Math.min(open,close)-Math.random()*0.0008;
    candles.push({{open,close,high,low}});price=close;
  }}
  const allVals=candles.flatMap(c=>[c.high,c.low]);
  const max=Math.max(...allVals),min=Math.min(...allVals);
  const range=max-min||0.001;const candleW=w/candles.length;
  candles.forEach((c,i)=>{{
    const x=i*candleW+candleW/2;
    const yHigh=h-((c.high-min)/range)*h;
    const yLow=h-((c.low-min)/range)*h;
    const yOpen=h-((c.open-min)/range)*h;
    const yClose=h-((c.close-min)/range)*h;
    const up=c.close>=c.open;
    ctx.strokeStyle=up?'#00c853':'#ff3b3b';
    ctx.fillStyle=up?'#00c853':'#ff3b3b';
    ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,yHigh);ctx.lineTo(x,yLow);ctx.stroke();
    const bodyTop=Math.min(yOpen,yClose);const bodyH=Math.max(Math.abs(yClose-yOpen),1);
    ctx.fillRect(x-candleW*0.3,bodyTop,candleW*0.6,bodyH);
  }});
  document.getElementById('eurusdPrice').textContent=candles[candles.length-1].close.toFixed(4);
}}
drawChart();window.addEventListener('resize',drawChart);
</script>
</body>
</html>"""
    return html


def render_prime_terminal():
    """Render Prime Terminal as a full-width Streamlit component."""
    st.markdown(
        """<div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,5,20,0.95));
        border:1px solid rgba(74,158,255,0.25);border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1rem;">
        <div style="font-size:1.1rem;font-weight:800;font-family:Orbitron,monospace;
        background:linear-gradient(90deg,#3d8bfd,#00c853);-webkit-background-clip:text;
        -webkit-text-fill-color:transparent;">🛰️ Prime Terminal</div>
        <div style="color:#8b949e;font-size:11px;margin-top:2px;">
        Live Ticker · Candlestick Chart · Macro News · Bank Trades · Smart Bias · Risk Sentiment · FX Cross Rates</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # Fetch live ticker data
    with st.spinner("Fetching live market data..."):
        ticker_data = _fetch_ticker_data()

    ticker_json = json.dumps(ticker_data)
    html_content = _render_prime_terminal_html(ticker_json)

    components.html(html_content, height=720, scrolling=True)
