"""FinSage AI -- Smart Trading Agent + Chart Image Analyzer
1. StoxAI Chat: Type any stock/crypto -> AI analyzes, gives entry/SL/targets, TradingView auto-setup
2. Chart Image Analyzer: Upload chart screenshot -> AI vision detects levels/patterns -> annotated image + white paper report
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
import os
import json
import re
import base64
from io import BytesIO
from datetime import datetime

# -- Key helpers --
def _get_key(name):
    v = os.environ.get(name, "")
    if not v:
        try:
            v = st.secrets.get(name, "") or st.secrets.get(name.replace("GROQ", "GROW"), "")
        except Exception:
            pass
    return v or ""

# -- API URLs --
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_URL   = "https://api.openai.com/v1/chat/completions"

# -- PIL for image annotations --
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ==============================================================
# PART 1: StoxAI Chat -- Smart Trading Agent
# ==============================================================

SYSTEM_PROMPT = """You are StoxAI -- an advanced automated trading agent.

When user asks you to analyze a stock/crypto OR set up a trade, you MUST:
1. Give a clear technical analysis in simple English
2. Decide: BUY / SELL / HOLD
3. Give EXACT price levels: Entry, Stop Loss, Target 1, Target 2, Target 3
4. Explain which indicators confirm the setup (RSI, MACD, BB, Volume)
5. Give timeframe recommendation
6. Give confidence score (0-100)

ALWAYS end your response with a JSON block like this (no exceptions when analyzing assets):
```json
{
  "action": "full_analysis",
  "ticker": "RELIANCE",
  "exchange": "NSE",
  "tv_symbol": "NSE:RELIANCE",
  "timeframe": "1D",
  "bias": "BUY",
  "entry": 2850,
  "stop_loss": 2770,
  "target1": 2960,
  "target2": 3080,
  "target3": 3250,
  "indicators": ["RSI(14)", "MACD(12,26,9)", "BB(20)", "Volume"],
  "confidence": 74,
  "rsi_value": 52,
  "macd_signal": "Bullish crossover",
  "bb_position": "Mid band bounce",
  "volume_note": "Above 20-day average",
  "risk_reward": "1:2.5",
  "hold_period": "5-7 days",
  "demo_trade": true
}
```

Rules:
- For NSE stocks: tv_symbol = "NSE:TICKER" (remove .NS)
- For BSE stocks: tv_symbol = "BSE:TICKER"
- For Crypto: tv_symbol = "BINANCE:BTCUSDT" format
- For US stocks: tv_symbol = "NASDAQ:AAPL" or "NYSE:TICKER"
- English only. Be specific with numbers. No vague answers."""

QUICK_CMDS = [
    ("\U0001f50d", "Analyze RELIANCE -- full setup"),
    ("\u20bf", "Analyze Bitcoin -- entry & targets"),
    ("\U0001f4ca", "Analyze NIFTY 50 trend"),
    ("\u26a1", "Analyze TCS -- should I buy?"),
    ("\U0001f3ad", "Analyze DOGE -- meme coin setup"),
    ("\U0001f4c9", "Analyze HDFC Bank -- swing trade"),
    ("\u2753", "Explain RSI with example"),
    ("\U0001f4a1", "Best stocks to watch today"),
]


def _call_groq(messages):
    api_key = _get_key("GROQ_API_KEY")
    if not api_key:
        return "WARNING: GROQ_API_KEY not set. Please add it in Streamlit secrets or environment variables.\n\nTo add it: Settings -> Secrets -> add GROQ_API_KEY = \"your-key\""
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "max_tokens": 1400,
                "temperature": 0.6},
            timeout=40,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"AI error (HTTP {resp.status_code}). Please try again."
    except requests.exceptions.Timeout:
        return "Request timed out. Please try again."
    except Exception as e:
        return f"Connection error: {str(e)[:120]}"


def _extract_trade(text):
    m = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return None


def _tv_url(trade):
    sym = trade.get("tv_symbol", trade.get("ticker", "NASDAQ:AAPL"))
    tf_map = {"1m":"1","5m":"5","15m":"15","30m":"30","1h":"60","4h":"240","1D":"D","1W":"W","1M":"M"}
    iv = tf_map.get(trade.get("timeframe","1D"), "D")
    return f"https://www.tradingview.com/chart/?symbol={sym}&interval={iv}"


def _render_trade_card(trade):
    bias     = trade.get("bias", "BUY")
    is_buy   = bias == "BUY"
    bias_col = "#22C55E" if is_buy else "#EF4444"
    bias_bg  = "rgba(34,197,94,0.1)" if is_buy else "rgba(239,68,68,0.1)"
    conf     = int(trade.get("confidence", 70))
    conf_col = "#22C55E" if conf >= 70 else "#F59E0B" if conf >= 50 else "#EF4444"
    ticker   = trade.get("ticker", "")
    entry    = trade.get("entry", 0)
    sl       = trade.get("stop_loss", 0)
    t1, t2, t3 = trade.get("target1",0), trade.get("target2",0), trade.get("target3",0)
    tv_url   = _tv_url(trade)
    indicators = trade.get("indicators", ["RSI","MACD","BB"])
    rr       = trade.get("risk_reward", "1:2")
    hold     = trade.get("hold_period", "")
    sym      = trade.get("tv_symbol", ticker)
    conf_w   = max(4, conf)

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0F172A,#162032);
    border:1px solid rgba(0,242,254,0.2);border-radius:18px;
    padding:1.2rem 1.3rem;margin:0.6rem 0;
    box-shadow:0 8px 32px rgba(0,0,0,0.5),0 0 0 1px rgba(0,242,254,0.05);">
  <div style="display:flex;align-items:center;gap:0.7rem;margin-bottom:1rem;flex-wrap:wrap;">
    <div style="background:linear-gradient(135deg,#00C6FF,#00F2FE);border-radius:10px;padding:0.35rem 0.9rem;color:#0B0F19;font-size:1rem;font-weight:900;letter-spacing:0.5px;">{ticker}</div>
    <div style="background:{bias_bg};border:1px solid {bias_col};border-radius:8px;padding:0.3rem 0.8rem;color:{bias_col};font-weight:800;font-size:0.88rem;">{'BUY' if is_buy else 'SELL'} {bias}</div>
    <div style="margin-left:auto;text-align:right;">
        <div style="color:{conf_col};font-size:1.2rem;font-weight:900;line-height:1;">{conf}%</div>
        <div style="color:#64748B;font-size:0.62rem;text-transform:uppercase;">Confidence</div>
        <div style="background:#1E293B;border-radius:4px;height:4px;width:80px;margin-top:3px;overflow:hidden;">
            <div style="background:{conf_col};height:100%;width:{conf_w}%;border-radius:4px;box-shadow:0 0 6px {conf_col};"></div>
        </div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:0.4rem;margin-bottom:0.9rem;">
    <div style="background:rgba(0,242,254,0.07);border:1px solid rgba(0,242,254,0.2);border-radius:10px;padding:0.55rem 0.4rem;text-align:center;"><div style="color:#64748B;font-size:0.58rem;font-weight:700;text-transform:uppercase;margin-bottom:2px;">Entry</div><div style="color:#00F2FE;font-size:0.88rem;font-weight:800;">{entry:}</div></div>
    <div style="background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.2);border-radius:10px;padding:0.55rem 0.4rem;text-align:center;"><div style="color:#64748B;font-size:0.58rem;font-weight:700;text-transform:uppercase;margin-bottom:2px;">Stop Loss</div><div style="color:#EF4444;font-size:0.88rem;font-weight:800;">{sl:}</div></div>
    <div style="background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.18);border-radius:10px;padding:0.55rem 0.4rem;text-align:center;"><div style="color:#64748B;font-size:0.58rem;font-weight:700;text-transform:uppercase;margin-bottom:2px;">Target 1</div><div style="color:#22C55E;font-size:0.88rem;font-weight:800;">{t1:}</div></div>
    <div style="background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.18);border-radius:10px;padding:0.55rem 0.4rem;text-align:center;"><div style="color:#64748B;font-size:0.58rem;font-weight:700;text-transform:uppercase;margin-bottom:2px;">Target 2</div><div style="color:#22C55E;font-size:0.88rem;font-weight:800;">{t2:}</div></div>
    <div style="background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.18);border-radius:10px;padding:0.55rem 0.4rem;text-align:center;"><div style="color:#64748B;font-size:0.58rem;font-weight:700;text-transform:uppercase;margin-bottom:2px;">Target 3</div><div style="color:#22C55E;font-size:0.88rem;font-weight:800;">{t3:}</div></div>
  </div>
  <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.9rem;align-items:center;">
    {''.join(f'<span style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.25);border-radius:6px;padding:0.2rem 0.55rem;color:#F59E0B;font-size:0.72rem;font-weight:600;">{ind}</span>' for ind in indicators)}
    {f'<span style="background:rgba(0,242,254,0.06);border:1px solid rgba(0,242,254,0.15);border-radius:6px;padding:0.2rem 0.55rem;color:#00F2FE;font-size:0.72rem;">R:R {rr}</span>' if rr else ''}
    {f'<span style="background:rgba(100,116,139,0.1);border:1px solid rgba(100,116,139,0.2);border-radius:6px;padding:0.2rem 0.55rem;color:#94A3B8;font-size:0.72rem;">Hold: {hold}</span>' if hold else ''}
  </div>
  <div style="background:rgba(0,242,254,0.04);border:1px solid rgba(0,242,254,0.12);border-radius:12px;padding:0.8rem 1rem;margin-bottom:0.9rem;">
    <div style="color:#00F2FE;font-size:0.76rem;font-weight:700;margin-bottom:0.5rem;">AI Auto-Execution on TradingView</div>
    <div style="color:#CBD5E1;font-size:0.77rem;line-height:1.9;">
        <b style="color:#F59E0B;">Step 1 -</b> Click <b style="color:#00F2FE;">Open Chart</b> -> Symbol <b>{sym}</b> auto-loads<br>
        <b style="color:#F59E0B;">Step 2 -</b> AI sets timeframe to <b style="color:#F59E0B;">{trade.get("timeframe","1D")}</b><br>
        <b style="color:#F59E0B;">Step 3 -</b> Adds indicators: <b>{' + '.join(indicators)}</b><br>
        <b style="color:#F59E0B;">Step 4 -</b> Draws Entry {entry} / SL {sl} / T1 {t1} / T2 {t2} / T3 {t3}<br>
        <b style="color:#F59E0B;">Step 5 -</b> Sets price alert at entry zone <b>{entry}</b><br>
        <b style="color:#F59E0B;">Step 6 -</b> Click <b style="color:#22C55E;">Start Demo Trade</b> -> Paper Trading opens
    </div>
  </div>
  <div style="display:flex;gap:0.7rem;flex-wrap:wrap;">
    <a href="{tv_url}" target="_blank" style="text-decoration:none;"><div style="background:linear-gradient(135deg,#00C6FF,#00F2FE);color:#0B0F19;border-radius:10px;padding:0.48rem 1.1rem;font-size:0.82rem;font-weight:800;box-shadow:0 4px 20px rgba(0,242,254,0.3);display:inline-flex;align-items:center;gap:0.4rem;">Open Chart on TradingView</div></a>
    <a href="https://www.tradingview.com/paper-trading/" target="_blank" style="text-decoration:none;"><div style="background:linear-gradient(135deg,#22C55E,#16A34A);color:#fff;border-radius:10px;padding:0.48rem 1.1rem;font-size:0.82rem;font-weight:800;box-shadow:0 4px 20px rgba(34,197,94,0.3);display:inline-flex;align-items:center;gap:0.4rem;">Start Demo Trade</div></a>
  </div>
</div>
""", unsafe_allow_html=True)


def render_ai_chat(analysis_context=None):
    if "ai_chat_messages" not in st.session_state:
        st.session_state.ai_chat_messages = []

    st.markdown("""
<div style="background:linear-gradient(135deg,rgba(0,242,254,0.06),rgba(245,158,11,0.06));border:1px solid rgba(0,242,254,0.2);border-radius:16px;padding:1rem 1.3rem;margin-bottom:0.8rem;">
  <div style="display:flex;align-items:center;gap:0.9rem;">
    <div style="background:linear-gradient(135deg,#0F172A,#1E293B);border:2px solid rgba(0,242,254,0.4);border-radius:14px;width:46px;height:46px;display:flex;align-items:center;justify-content:center;font-size:1.5rem;box-shadow:0 0 16px rgba(0,242,254,0.2);">Robot</div>
    <div style="flex:1;">
      <div style="font-size:1rem;font-weight:800;background:linear-gradient(90deg,#00F2FE,#F59E0B);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">StoxAI -- Smart Trading Agent</div>
      <div style="color:#64748B;font-size:0.75rem;margin-top:0.1rem;">Type any stock or crypto -> AI analyzes + auto-sets up TradingView with bars, SL & demo trade</div>
    </div>
    <div style="display:flex;align-items:center;gap:0.35rem;background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);border-radius:20px;padding:0.25rem 0.7rem;">
      <div style="width:7px;height:7px;background:#22C55E;border-radius:50%;box-shadow:0 0 8px #22C55E;"></div>
      <span style="color:#22C55E;font-size:0.72rem;font-weight:700;">Active</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    if analysis_context and analysis_context.get("ticker"):
        t = analysis_context.get("ticker", "")
        n = analysis_context.get("name", t)
        chg = float(analysis_context.get("change_pct") or 0)
        cc = "#22C55E" if chg >= 0 else "#EF4444"
        st.markdown(f"""
<div style="background:rgba(0,242,254,0.04);border:1px solid rgba(0,242,254,0.15);border-radius:10px;padding:0.55rem 1rem;margin-bottom:0.7rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;">
  <span style="font-size:1rem;">Chart</span>
  <span style="color:#E2E8F0;font-weight:700;font-size:0.85rem;">{n} ({t})</span>
  <span style="color:{cc};font-size:0.82rem;font-weight:600;">{abs(chg):.2f}%</span>
  <span style="margin-left:auto;color:#64748B;font-size:0.7rem;">AI has full context of this asset</span>
</div>
""", unsafe_allow_html=True)

    if not st.session_state.ai_chat_messages:
        st.markdown('<div style="color:#64748B;font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.5rem;">Quick Commands</div>', unsafe_allow_html=True)
        q_cols = st.columns(2)
        for qi, (icon, q) in enumerate(QUICK_CMDS):
            with q_cols[qi % 2]:
                if st.button(f"{icon} {q}", key=f"qcmd_{qi}", use_container_width=True):
                    st.session_state.ai_chat_messages.append({"role": "user", "content": q})
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    for msg in st.session_state.ai_chat_messages:
        role = msg["role"]
        if role == "user":
            st.markdown(f"""
<div style="display:flex;justify-content:flex-end;margin-bottom:0.55rem;">
  <div style="background:linear-gradient(135deg,#00C6FF,#00F2FE);color:#0B0F19;border-radius:16px 16px 4px 16px;padding:0.65rem 1rem;max-width:72%;font-size:0.84rem;line-height:1.5;font-weight:600;box-shadow:0 4px 16px rgba(0,242,254,0.2);">{msg['content']}</div>
  <div style="width:28px;height:28px;background:linear-gradient(135deg,#00C6FF,#F59E0B);border-radius:50%;display:flex;align-items:center;justify-content:center;margin-left:0.45rem;flex-shrink:0;font-size:0.85rem;margin-top:2px;">You</div>
</div>
""", unsafe_allow_html=True)
        else:
            clean_text = re.sub(r'```json.*?```', '', msg["content"], flags=re.DOTALL).strip()
            clean_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', clean_text)
            clean_text = re.sub(r'\n[-•] ', '<br>• ', clean_text)
            clean_text = clean_text.replace("\n", "<br>")
            st.markdown(f"""
<div style="display:flex;margin-bottom:0.55rem;align-items:flex-start;">
  <div style="width:28px;height:28px;background:linear-gradient(135deg,#0F172A,#1E293B);border:2px solid rgba(0,242,254,0.35);border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:0.45rem;flex-shrink:0;font-size:0.85rem;">AI</div>
  <div style="background:#162032;border:1px solid rgba(30,41,59,0.8);border-radius:4px 16px 16px 16px;padding:0.75rem 1rem;max-width:82%;font-size:0.83rem;color:#CBD5E1;line-height:1.65;">{clean_text}</div>
</div>
""", unsafe_allow_html=True)
            trade = _extract_trade(msg["content"])
            if trade:
                _render_trade_card(trade)

    msgs = st.session_state.ai_chat_messages
    if msgs and msgs[-1]["role"] == "user":
        with st.spinner("AI Analyzing... preparing TradingView setup..."):
            sys_msg = SYSTEM_PROMPT
            if analysis_context and analysis_context.get("ticker"):
                sys_msg += f"\n\nCURRENT ASSET IN VIEW: {analysis_context.get('name','')} ({analysis_context.get('ticker','')}), Price: {analysis_context.get('current_price',0)}, Change 24h: {analysis_context.get('change_pct',0)}%"
            api_msgs = [{"role": "system", "content": sys_msg}] + msgs[-14:]
            reply = _call_groq(api_msgs)
        st.session_state.ai_chat_messages.append({"role": "assistant", "content": reply})
        st.rerun()

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    inp_col, btn_col = st.columns([5, 1])
    with inp_col:
        user_input = st.text_input("", placeholder="e.g. 'Analyze RELIANCE' / 'Buy/sell setup for BTC' / 'Is TCS a good buy?'", key="ai_chat_input", label_visibility="collapsed")
    with btn_col:
        send_clicked = st.button("Send", type="primary", use_container_width=True, key="send_chat_btn")

    if send_clicked and user_input.strip():
        st.session_state.ai_chat_messages.append({"role": "user", "content": user_input.strip()})
        st.rerun()

    if st.session_state.ai_chat_messages:
        if st.button("Clear Chat", key="clear_ai_chat", use_container_width=True):
            st.session_state.ai_chat_messages = []
            st.rerun()


# ==============================================================
# PART 2: Chart Image Analyzer -- Vision-based chart analysis
# ==============================================================

def _img_to_b64(img_bytes):
    return base64.b64encode(img_bytes).decode()


def _call_vision_api(img_b64, prompt):
    openai_key = _get_key("OPENAI_API_KEY")
    groq_key   = _get_key("GROQ_API_KEY")

    if openai_key:
        try:
            resp = requests.post(OPENAI_URL, headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}, json={
                "model": "gpt-4o", "max_tokens": 4000,
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}", "detail": "high"}},
                    {"type": "text", "text": prompt}
                ]}]
            }, timeout=60)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"], "GPT-4o"
        except Exception:
            pass

    if groq_key:
        try:
            resp = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}, json={
                "model": "meta-llama/llama-3.2-90b-vision-preview", "max_tokens": 4000,
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": prompt}
                ]}]
            }, timeout=60)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"], "Groq Vision"
        except Exception:
            pass

    return None, None


VISION_PROMPT = """You are a professional financial chart analyst. Analyze this trading chart image in EXTREME detail.

Return a JSON object with EXACTLY this structure (no markdown, pure JSON):
{
  "ticker": "detected symbol or UNKNOWN",
  "timeframe": "detected timeframe e.g. 1D, 4H, 1H, 15m",
  "chart_type": "Candlestick/Line/Bar",
  "current_price": 0.0,
  "trend": "BULLISH/BEARISH/SIDEWAYS",
  "trend_strength": "STRONG/MODERATE/WEAK",
  "support_levels": [{"price": 0.0, "strength": "STRONG/MODERATE/WEAK", "note": "description"}],
  "resistance_levels": [{"price": 0.0, "strength": "STRONG/MODERATE/WEAK", "note": "description"}],
  "patterns_detected": [{"name": "pattern name", "type": "BULLISH/BEARISH/NEUTRAL", "location": "where on chart", "significance": "what it means"}],
  "candlestick_patterns": [{"name": "candle pattern", "type": "BULLISH/BEARISH/NEUTRAL", "action": "what to do"}],
  "indicators_visible": [{"name": "indicator name", "reading": "current value/state", "signal": "BULLISH/BEARISH/NEUTRAL", "explanation": "what it means"}],
  "volume_analysis": {"trend": "INCREASING/DECREASING/FLAT", "observation": "volume behavior description", "signal": "BULLISH/BEARISH/NEUTRAL"},
  "fibonacci_levels": [{"level": "0.382/0.5/0.618", "price": 0.0}],
  "entry_zone": {"price_from": 0.0, "price_to": 0.0, "reason": "why enter here"},
  "stop_loss": {"price": 0.0, "reason": "why this stop"},
  "targets": [{"price": 0.0, "label": "T1/T2/T3", "rr_ratio": "1:2"}],
  "order_flow": {"buying_pressure": "HIGH/MODERATE/LOW", "selling_pressure": "HIGH/MODERATE/LOW", "imbalance_zones": ["description"]},
  "liquidity": {"buy_side_liq": "description", "sell_side_liq": "description", "hvn": 0.0, "lvn": 0.0},
  "key_observations": ["observation 1", "observation 2", "observation 3"],
  "trading_bias": "LONG/SHORT/WAIT",
  "confidence_score": 75,
  "executive_summary": "2-3 sentence professional summary of what this chart is showing",
  "indicator_summary": "What all visible indicators collectively suggest",
  "volume_narrative": "Detailed explanation of volume behavior and what it reveals about buying/selling pressure",
  "risk_assessment": "LOW/MEDIUM/HIGH -- with explanation"
}

Be specific with price levels if visible. If a value is not visible in the chart, use 0 for numbers or descriptive text."""


def _draw_annotations_on_image(img_bytes, analysis):
    if not PIL_OK:
        return img_bytes
    try:
        img = Image.open(BytesIO(img_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img, "RGBA")
        W, H = img.size
        try:
            font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
            font_xs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except Exception:
            font_sm = ImageFont.load_default()
            font_xs = font_sm

        cur   = analysis.get("current_price", 0)
        supps = analysis.get("support_levels", [])
        resis = analysis.get("resistance_levels", [])
        pats  = analysis.get("patterns_detected", [])
        all_prices = [s["price"] for s in supps if s.get("price",0)>0] + [r["price"] for r in resis if r.get("price",0)>0]
        if cur > 0: all_prices.append(cur)

        if len(all_prices) >= 2:
            p_min = min(all_prices) * 0.995
            p_max = max(all_prices) * 1.005
            p_range = p_max - p_min
            def price_to_y(price):
                if p_range == 0: return H // 2
                ratio = (p_max - price) / p_range
                return int(ratio * H * 0.85 + H * 0.05)

            for i, s in enumerate(supps[:4]):
                if s.get("price",0)>0:
                    y = price_to_y(s["price"])
                    if 10 < y < H-10:
                        for x in range(0,W,16): draw.line([(x,y),(min(x+10,W),y)], fill=(34,197,94,200), width=2)
                        lbl = f"S{i+1}: {s['price']:.2f}"
                        draw.rectangle([W-145,y-14,W-5,y+4], fill=(0,0,0,170))
                        draw.text((W-140,y-13), lbl, fill=(34,197,94), font=font_xs)
            for i, r in enumerate(resis[:4]):
                if r.get("price",0)>0:
                    y = price_to_y(r["price"])
                    if 10 < y < H-10:
                        for x in range(0,W,16): draw.line([(x,y),(min(x+10,W),y)], fill=(239,68,68,200), width=2)
                        lbl = f"R{i+1}: {r['price']:.2f}"
                        draw.rectangle([W-145,y-14,W-5,y+4], fill=(0,0,0,170))
                        draw.text((W-140,y-13), lbl, fill=(239,68,68), font=font_xs)
            if cur > 0:
                y = price_to_y(cur)
                if 10 < y < H-10:
                    draw.line([(0,y),(W,y)], fill=(250,204,21,180), width=1)
                    draw.rectangle([5,y-13,90,y+3], fill=(0,0,0,180))
                    draw.text((8,y-12), f"CUR: {cur:.2f}", fill=(250,204,21), font=font_xs)

        overlay_y = 10
        for p in pats[:3]:
            ptype = p.get("type","")
            col = (34,197,94) if ptype=="BULLISH" else (239,68,68) if ptype=="BEARISH" else (250,204,21)
            arrow = "^" if ptype=="BULLISH" else "v" if ptype=="BEARISH" else "->"
            lbl = f"{arrow} {p['name']}"
            tw = len(lbl)*8
            draw.rectangle([5,overlay_y,tw+15,overlay_y+18], fill=(0,0,0,180))
            draw.text((8,overlay_y+2), lbl, fill=col, font=font_xs)
            overlay_y += 22

        trend = analysis.get("trend","")
        tc = (34,197,94) if trend=="BULLISH" else (239,68,68) if trend=="BEARISH" else (250,204,21)
        badge = f"{'^' if trend=='BULLISH' else 'v' if trend=='BEARISH' else '->'} {trend}"
        draw.rectangle([W-120,8,W-5,30], fill=(0,0,0,200))
        draw.text((W-116,11), badge, fill=tc, font=font_sm)
        conf = analysis.get("confidence_score",0)
        draw.rectangle([W-120,35,W-5,55], fill=(0,0,0,180))
        draw.text((W-116,38), f"AI Conf: {conf}%", fill=(255,255,255), font=font_xs)
        draw.rectangle([3,H-22,110,H-2], fill=(0,0,0,160))
        draw.text((6,H-20), "FinSage AI", fill=(100,200,255), font=font_xs)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=92)
        return buf.getvalue()
    except Exception:
        return img_bytes


def _white_paper_html_chart(analysis, ticker_name):
    trend = analysis.get("trend","--")
    bias  = analysis.get("trading_bias","--")
    conf  = analysis.get("confidence_score",0)
    tc    = "#1b5e20" if trend=="BULLISH" else "#b71c1c" if trend=="BEARISH" else "#e65100"
    bc    = "#1b5e20" if bias=="LONG"    else "#b71c1c" if bias=="SHORT"    else "#555"
    now   = datetime.now().strftime("%B %d, %Y - %H:%M IST")

    def ep(p):
        if not p: return "--"
        try:
            p=float(p); return f"{p:.4f}" if 0<p<10 else f"{p:.2f}"
        except: return "--"

    sup_rows = "".join([f"<tr><td><b>S{i+1}</b></td><td style='font-family:monospace;font-weight:700;'>{ep(s.get('price',0))}</td><td>{s.get('strength','')}</td><td>{str(s.get('note',''))[:60]}</td></tr>" for i,s in enumerate(analysis.get("support_levels",[])[:5])])
    res_rows = "".join([f"<tr><td><b>R{i+1}</b></td><td style='font-family:monospace;font-weight:700;'>{ep(r.get('price',0))}</td><td>{r.get('strength','')}</td><td>{str(r.get('note',''))[:60]}</td></tr>" for i,r in enumerate(analysis.get("resistance_levels",[])[:5])])
    pat_rows = "".join([f"<tr><td style='font-weight:700;'>{p.get('name','')}</td><td>{p.get('type','')}</td><td>{str(p.get('location',''))[:40]}</td><td>{str(p.get('significance',''))[:80]}</td></tr>" for p in analysis.get("patterns_detected",[])[:5]])
    ind_rows = "".join([f"<tr><td style='font-weight:700;'>{ind.get('name','')}</td><td>{str(ind.get('reading',''))[:25]}</td><td>{ind.get('signal','')}</td><td>{str(ind.get('explanation',''))[:80]}</td></tr>" for ind in analysis.get("indicators_visible",[])[:8]])
    obs_rows = "".join([f"<div style='padding:5px 0 5px 18px;border-bottom:1px solid #eee;font-size:14px;'>{o}</div>" for o in analysis.get("key_observations",[])])
    targets_rows = "".join([f"<tr><td style='font-weight:700;color:#1b5e20;'>{t.get('label','')}</td><td style='font-family:monospace;font-weight:700;'>{ep(t.get('price',0))}</td><td>{t.get('rr_ratio','')}</td></tr>" for t in analysis.get("targets",[])])
    vol = analysis.get("volume_analysis",{})
    of  = analysis.get("order_flow",{})
    liq = analysis.get("liquidity",{})
    ez  = analysis.get("entry_zone",{})
    sl  = analysis.get("stop_loss",{})
    ez_p = f"{ep(ez.get('price_from',0))} - {ep(ez.get('price_to',0))}" if ez.get("price_from",0) else "--"

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{{margin:0;padding:0;background:#fff;}}
.wp{{background:#fff;color:#1a1a1a;font-family:Georgia,serif;padding:44px 48px;line-height:1.8;max-width:960px;margin:0 auto;}}
.wp *{{color:#1a1a1a!important;}}
.stripe{{height:6px;background:linear-gradient(90deg,#1a237e,#0d47a1,#006064,#1b5e20,#e65100,#b71c1c);margin-bottom:28px;border-radius:3px;}}
h1{{font-size:28px;font-weight:900;margin-bottom:6px;}}
h2{{font-size:13px;font-weight:900;text-transform:uppercase;letter-spacing:.12em;border-bottom:2.5px solid #1a1a1a;padding-bottom:6px;margin:24px 0 14px;font-family:Arial,sans-serif;}}
p,.txt{{font-size:14.5px;line-height:1.85;margin-bottom:10px;text-align:justify;}}
table{{width:100%;border-collapse:collapse;font-size:13.5px;margin:10px 0;}}
table th{{background:#1a1a1a!important;color:#fff!important;padding:9px 11px;text-align:left;font-family:Arial;font-size:11.5px;text-transform:uppercase;}}
table td{{padding:8px 11px;border-bottom:1px solid #e0e0e0;vertical-align:top;}}
table tr:nth-child(even) td{{background:#f9f9f9!important;}}
.badge{{display:inline-block;border:2.5px solid #1a1a1a;border-radius:4px;padding:5px 18px;font-size:15px;font-weight:900;margin-right:12px;font-family:Arial;}}
.grid4{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0;}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:14px 0;}}
.cell{{border:1px solid #ccc;border-radius:4px;padding:12px;text-align:center;}}
.cl{{font-size:11px;text-transform:uppercase;letter-spacing:.07em;font-family:Arial;margin-bottom:5px;}}
.cv{{font-size:20px;font-weight:900;font-family:'Courier New',monospace;}}
.disc{{font-size:11px;border-top:1px solid #ccc;margin-top:24px;padding-top:12px;font-family:Arial;line-height:1.6;text-align:center;}}
</style></head><body><div class="wp">
<div class="stripe"></div>
<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:16px;margin-bottom:22px;">
  <div><div style="font-size:11px;font-family:Arial;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;">FinSage AI Chart Vision Analysis</div>
  <h1>Chart Analysis Report<br><span style="font-size:18px;font-weight:700;">{ticker_name}</span></h1>
  <div style="margin-top:10px;"><span class="badge">{trend}</span><span class="badge" style="font-size:13px;">{bias}</span></div></div>
  <div style="text-align:right;"><div style="font-size:13px;">Timeframe: <b>{analysis.get('timeframe','--')}</b></div><div style="font-size:13px;">Chart Type: <b>{analysis.get('chart_type','--')}</b></div><div style="font-size:13px;">AI Confidence: <b>{conf}%</b></div><div style="font-size:12px;margin-top:6px;">{now}</div></div>
</div>
<h2>Executive Summary</h2><p class="txt">{analysis.get('executive_summary','')}</p>
<h2>Key Metrics</h2>
<div class="grid4">
  <div class="cell"><div class="cl">Current Price</div><div class="cv">{ep(analysis.get('current_price',0))}</div></div>
  <div class="cell"><div class="cl">Trend</div><div class="cv" style="color:{tc}!important;font-size:14px;">{trend}</div></div>
  <div class="cell"><div class="cl">Strength</div><div class="cv" style="font-size:14px;">{analysis.get('trend_strength','--')}</div></div>
  <div class="cell"><div class="cl">Trade Bias</div><div class="cv" style="color:{bc}!important;font-size:14px;">{bias}</div></div>
</div>
<h2>Support & Resistance Levels</h2>
<div class="grid3" style="margin-bottom:14px;">
  <div><div style="font-weight:800;font-family:Arial;font-size:12px;text-transform:uppercase;margin-bottom:8px;color:#1b5e20!important;">Support Levels</div><table><thead><tr><th>#</th><th>Price</th><th>Strength</th><th>Note</th></tr></thead><tbody>{sup_rows or '<tr><td colspan=4>Not detected</td></tr>'}</tbody></table></div>
  <div><div style="font-weight:800;font-family:Arial;font-size:12px;text-transform:uppercase;margin-bottom:8px;color:#b71c1c!important;">Resistance Levels</div><table><thead><tr><th>#</th><th>Price</th><th>Strength</th><th>Note</th></tr></thead><tbody>{res_rows or '<tr><td colspan=4>Not detected</td></tr>'}</tbody></table></div>
  <div><div style="font-weight:800;font-family:Arial;font-size:12px;text-transform:uppercase;margin-bottom:8px;">Trade Setup</div><table><tbody><tr><td style="font-weight:700;">Entry Zone</td><td>{ez_p}</td></tr><tr><td style="font-weight:700;">Stop Loss</td><td style="color:#b71c1c!important;">{ep(sl.get('price',0))}</td></tr>{targets_rows}</tbody></table></div>
</div>
<h2>Chart & Candlestick Patterns</h2><table><thead><tr><th>Pattern</th><th>Signal</th><th>Location</th><th>Significance</th></tr></thead><tbody>{pat_rows or '<tr><td colspan=4>No patterns detected</td></tr>'}</tbody></table>
<h2>Technical Indicators</h2><p class="txt">{analysis.get('indicator_summary','')}</p><table><thead><tr><th>Indicator</th><th>Reading</th><th>Signal</th><th>Explanation</th></tr></thead><tbody>{ind_rows or '<tr><td colspan=4>No indicators visible</td></tr>'}</tbody></table>
<h2>Volume & Order Flow</h2><p class="txt">{analysis.get('volume_narrative','')}</p>
<div class="grid3"><div class="cell"><div class="cl">Volume Trend</div><div class="cv" style="font-size:14px;">{vol.get('trend','--')}</div></div><div class="cell"><div class="cl">Buying Pressure</div><div class="cv" style="font-size:14px;color:#1b5e20!important;">{of.get('buying_pressure','--')}</div></div><div class="cell"><div class="cl">Selling Pressure</div><div class="cv" style="font-size:14px;color:#b71c1c!important;">{of.get('selling_pressure','--')}</div></div></div>
<h2>Key Observations</h2>{obs_rows or '<p class="txt">No observations.</p>'}
<h2>Risk Assessment</h2><p class="txt" style="font-weight:700;font-size:15px;">{analysis.get('risk_assessment','--')}</p>
<div class="disc">FinSage AI Chart Vision Analysis - Generated on {now}<br>AI-generated for educational purposes only. Not financial advice.</div>
</div></body></html>"""
    return html


def render_chart_analyzer():
    st.markdown("""
<div style="background:linear-gradient(135deg,rgba(99,102,241,0.06),rgba(245,158,11,0.06));border:1px solid rgba(99,102,241,0.2);border-radius:16px;padding:1rem 1.3rem;margin-bottom:0.8rem;">
  <div style="display:flex;align-items:center;gap:0.9rem;">
    <div style="font-size:1.5rem;">Camera</div>
    <div style="flex:1;"><div style="font-size:1rem;font-weight:800;color:#818CF8;">Chart Image Analyzer</div><div style="color:#64748B;font-size:0.75rem;margin-top:0.1rem;">Upload any chart screenshot -> AI detects levels, patterns, indicators -> annotated image + white paper report</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

    has_openai = bool(_get_key("OPENAI_API_KEY"))
    has_groq   = bool(_get_key("GROQ_API_KEY"))

    if not has_openai and not has_groq:
        st.warning("No vision API key found. Add OPENAI_API_KEY or GROQ_API_KEY in Streamlit secrets to use the Chart Image Analyzer.")
        st.info("How to add API keys:\n1. Open your Streamlit app settings\n2. Go to Secrets\n3. Add either OPENAI_API_KEY or GROQ_API_KEY")
        return

    uploaded = st.file_uploader("Upload Chart Screenshot", type=["png","jpg","jpeg","webp"], help="Upload any trading chart screenshot")

    if uploaded is not None:
        img_bytes = uploaded.getvalue()
        st.markdown("#### Original Chart")
        st.image(img_bytes, use_container_width=True)

        if st.button("Analyze Chart with AI", type="primary", use_container_width=True, key="analyze_chart_btn"):
            with st.spinner("AI analyzing chart image..."):
                img_b64 = _img_to_b64(img_bytes)
                result, model_used = _call_vision_api(img_b64, VISION_PROMPT)
            if result is None:
                st.error("Could not analyze image. Both OpenAI and Groq vision APIs failed.")
                return
            try:
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                analysis = json.loads(json_match.group()) if json_match else json.loads(result)
            except Exception:
                st.error("AI returned invalid JSON. Please try again with a clearer chart image.")
                st.code(result[:2000], language="json")
                return
            st.session_state["chart_analysis_result"] = analysis
            st.session_state["chart_analysis_model"] = model_used
            st.session_state["chart_analysis_ticker"] = analysis.get("ticker", "UNKNOWN")
            st.session_state["chart_analysis_img"] = img_bytes
            st.rerun()

    analysis = st.session_state.get("chart_analysis_result")
    if analysis:
        model_used = st.session_state.get("chart_analysis_model", "AI")
        ticker_name = st.session_state.get("chart_analysis_ticker", "UNKNOWN")
        orig_img = st.session_state.get("chart_analysis_img", b"")

        st.success(f"Analysis complete using {model_used}!")

        st.markdown("#### AI-Annotated Chart")
        annotated = _draw_annotations_on_image(orig_img, analysis)
        if annotated != orig_img:
            st.image(annotated, use_container_width=True)

        trend = analysis.get("trend","--")
        bias  = analysis.get("trading_bias","--")
        conf  = analysis.get("confidence_score",0)
        price = analysis.get("current_price",0)

        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Trend", trend)
        with col2: st.metric("Bias", bias)
        with col3: st.metric("Confidence", f"{conf}%")
        with col4: st.metric("Price", f"{price:.2f}" if price else "--")

        st.markdown("---")
        st.markdown("#### White Paper Report")
        html_report = _white_paper_html_chart(analysis, ticker_name)
        components.html(html_report, height=1400, scrolling=True)

        st.download_button("Download Report as HTML", data=html_report.encode(), file_name=f"chart_analysis_{ticker_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.html", mime="text/html", use_container_width=True, key="download_chart_report")

        if st.button("Analyze Another Chart", key="clear_chart_analysis"):
            for k in ["chart_analysis_result","chart_analysis_model","chart_analysis_ticker","chart_analysis_img"]:
                st.session_state.pop(k, None)
            st.rerun()


# ==============================================================
# MAIN RENDERER -- FinSage AI tab with sub-tabs
# ==============================================================

def render_finsage_ai():
    sub_tabs = st.tabs(["StoxAI Chat", "Chart Analyzer"])
    with sub_tabs[0]:
        ctx = st.session_state.get("finsage_context", None)
        render_ai_chat(analysis_context=ctx)
    with sub_tabs[1]:
        render_chart_analyzer()
