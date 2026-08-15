import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
from modules.data_fetch import get_download
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from modules.chart_utils import TV_CHART_CONFIG, TV_LAYOUT_KWARGS, TV_SPIKE_XAXES, TV_SPIKE_YAXES, apply_tv_style
import io
import time

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="Quant Desk — Stock Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "QUANT DESK -- STOCK ANALYSIS DASHBOARD\nBuilt with Streamlit + Plotly + yfinance\nFor educational purposes only."},
)
# Hide GitHub deploy button only (3-dots menu stays visible)
st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════
   SCI-FI COMMAND CENTER UI — Blade Runner x NASA x Tron
   ═══════════════════════════════════════════════════════════ */

@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Rajdhani:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

:root {
  --bg: #05070D;
  --bg-grad: linear-gradient(135deg, #05070D 0%, #0A0E1A 40%, #0D1525 100%);
  --cyan: #00F0FF;
  --violet: #9D4EFF;
  --magenta: #FF2D95;
  --amber: #FFB800;
  --green: #00FF88;
  --red: #FF3B5C;
  --text: #C8D4E3;
  --muted: #5A6B80;
  --panel: rgba(10, 14, 26, 0.65);
  --panel-2: rgba(13, 18, 32, 0.7);
  --border: rgba(0, 240, 255, 0.15);
  --border-strong: rgba(0, 240, 255, 0.4);
  --glow-cyan: 0 0 12px rgba(0, 240, 255, 0.3);
  --glow-violet: 0 0 12px rgba(157, 78, 255, 0.3);
  --glow-magenta: 0 0 12px rgba(255, 45, 149, 0.3);
  --font-hud: 'Orbitron', 'Rajdhani', monospace;
  --font-data: 'Share Tech Mono', monospace;
  --font-body: 'Rajdhani', sans-serif;
}

/* ── Remove GitHub / Streamlit chrome ── */
.stDeployButton, #MainMenu, [data-testid="stMainMenu"] { display: none !important; }
footer { display: none !important; }
#stGithubLink, .stGithubLink { display: none !important; }
.stApp [data-testid="stToolbar"] { display: none !important; }

/* ── Global background: deep space ── */
.stApp {
  background: var(--bg-grad) !important;
  background-attachment: fixed !important;
}

/* Hexagonal grid overlay at low opacity */
.stApp::before {
  content: "";
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background-image:
    linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

/* Scan-line effect */
.stApp::after {
  content: "";
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: repeating-linear-gradient(
    0deg,
    transparent 0px,
    transparent 2px,
    rgba(0, 240, 255, 0.015) 2px,
    rgba(0, 240, 255, 0.015) 4px
  );
  pointer-events: none;
  z-index: 1;
}

.stMain, .stMain > section, [data-testid="stMain"] {
  background: transparent !important;
  position: relative;
  z-index: 2;
}

/* ── Headings: HUD style ── */
h1, h2, h3, h4 {
  font-family: var(--font-hud) !important;
  text-transform: uppercase !important;
  letter-spacing: 3px !important;
  font-weight: 700 !important;
  color: var(--cyan) !important;
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.3) !important;
}

h1 { font-size: 1.8rem !important; letter-spacing: 4px !important; }
h2 { font-size: 1.4rem !important; }
h3 { font-size: 1.1rem !important; }
h4 { font-size: 0.95rem !important; letter-spacing: 2px !important; }

/* ── Body text ── */
p, span, div, td, th {
  font-family: var(--font-body) !important;
}
.stMetric, [data-testid="stMetric"] {
  background: var(--panel) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border: 1px solid var(--border) !important;
  border-radius: 2px !important;
  padding: 14px 16px !important;
  transition: all 0.3s ease !important;
  position: relative;
}
.stMetric::before {
  content: "";
  position: absolute;
  top: 0; left: 0; width: 3px; height: 100%;
  background: var(--cyan);
  box-shadow: var(--glow-cyan);
}
.stMetric:hover {
  border-color: var(--border-strong) !important;
  box-shadow: var(--glow-cyan) !important;
  transform: translateY(-2px) !important;
}
.stMetric label, .stMetric [data-testid="stMetricLabel"] {
  font-family: var(--font-hud) !important;
  font-size: 10px !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  color: var(--muted) !important;
}
.stMetric [data-testid="stMetricValue"] {
  font-family: var(--font-data) !important;
  color: var(--cyan) !important;
  text-shadow: 0 0 6px rgba(0, 240, 255, 0.2) !important;
}
.stMetric [data-testid="stMetricDelta"] {
  font-family: var(--font-data) !important;
}

/* ── Sidebar: command center panel ── */
section[data-testid="stSidebar"] {
  background: rgba(5, 7, 13, 0.92) !important;
  backdrop-filter: blur(20px) !important;
  -webkit-backdrop-filter: blur(20px) !important;
  border-right: 1px solid var(--border-strong) !important;
  box-shadow: 4px 0 20px rgba(0, 240, 255, 0.05) !important;
}
section[data-testid="stSidebar"] > div {
  padding-top: 1rem !important;
}

/* ── Buttons: angular clipped corners + neon ── */
.stButton > button {
  background: rgba(0, 240, 255, 0.05) !important;
  backdrop-filter: blur(8px) !important;
  border: 1px solid var(--border) !important;
  border-radius: 0 !important;
  clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px) !important;
  color: var(--text) !important;
  font-family: var(--font-hud) !important;
  font-size: 12px !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  font-weight: 500 !important;
  transition: all 0.25s ease !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
}
.stButton > button:hover {
  background: rgba(0, 240, 255, 0.12) !important;
  border-color: var(--cyan) !important;
  box-shadow: var(--glow-cyan) !important;
  color: var(--cyan) !important;
  text-shadow: 0 0 8px rgba(0, 240, 255, 0.5) !important;
}
.stButton > button:active {
  transform: scale(0.98) !important;
}
/* Primary button — cyan neon */
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(157, 78, 255, 0.1)) !important;
  border: 1px solid var(--border-strong) !important;
  box-shadow: var(--glow-cyan), 0 2px 8px rgba(0,0,0,0.3) !important;
  color: var(--cyan) !important;
}
.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.25), rgba(157, 78, 255, 0.15)) !important;
  box-shadow: 0 0 20px rgba(0, 240, 255, 0.4), var(--glow-violet) !important;
}

/* ── Inputs: HUD terminal style ── */
.stTextInput > div > div > input,
.stSelectbox > div > div > div {
  background: rgba(5, 7, 13, 0.6) !important;
  backdrop-filter: blur(8px) !important;
  border: 1px solid var(--border) !important;
  border-radius: 0 !important;
  color: var(--cyan) !important;
  font-family: var(--font-data) !important;
  font-size: 13px !important;
}
.stTextInput > div > div > input:focus {
  border-color: var(--cyan) !important;
  box-shadow: var(--glow-cyan) !important;
}
.stTextInput > div > div > input::placeholder {
  color: var(--muted) !important;
  font-family: var(--font-data) !important;
}
.stSelectbox > div > div > div {
  font-family: var(--font-data) !important;
  color: var(--cyan) !important;
}

/* ── Dataframes: transparent terminal ── */
.stDataFrame {
  background: var(--panel) !important;
  border: 1px solid var(--border) !important;
  border-radius: 0 !important;
  overflow: hidden !important;
}
.stDataFrame [data-testid="stDataFrameResizable"] {
  background: transparent !important;
}

/* ── Info/Success/Error boxes ── */
.stAlert, .stInfo, .stSuccess, .stError, .stWarning {
  background: var(--panel) !important;
  backdrop-filter: blur(8px) !important;
  border: 1px solid var(--border) !important;
  border-left: 3px solid var(--cyan) !important;
  border-radius: 0 !important;
}
.stSuccess { border-left-color: var(--green) !important; }
.stError { border-left-color: var(--red) !important; }
.stWarning { border-left-color: var(--amber) !important; }

/* ── Expanders ── */
.streamlit-expanderHeader {
  background: var(--panel-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 0 !important;
  font-family: var(--font-hud) !important;
  font-size: 12px !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  color: var(--cyan) !important;
}

/* ── Captions ── */
.stCaption, p[data-testid="stCaption"] {
  color: var(--muted) !important;
  font-family: var(--font-data) !important;
  font-size: 11px !important;
  letter-spacing: 0.5px !important;
}

/* ── Plotly modebar: minimal HUD style ── */
.modebar {
  background: rgba(5, 7, 13, 0.7) !important;
  backdrop-filter: blur(8px) !important;
  border: 1px solid var(--border) !important;
  border-radius: 0 !important;
  padding: 2px !important;
}
.modebar-btn { color: var(--muted) !important; }
.modebar-btn:hover {
  background: rgba(0, 240, 255, 0.15) !important;
  color: var(--cyan) !important;
}
.modebar-btn.active {
  background-color: rgba(0, 240, 255, 0.2) !important;
  color: var(--cyan) !important;
}

/* Fix Plotly zoom */
.js-plotly-plot .plot-container,
.js-plotly-plot .svg-container {
  touch-action: none !important;
}

/* ── Scrollbar: sci-fi style ── */
::-webkit-scrollbar { width: 6px !important; height: 6px !important; }
::-webkit-scrollbar-track { background: rgba(5, 7, 13, 0.5) !important; }
::-webkit-scrollbar-thumb {
  background: rgba(0, 240, 255, 0.3) !important;
  border-radius: 0 !important;
}
::-webkit-scrollbar-thumb:hover { background: rgba(0, 240, 255, 0.5) !important; }

/* ── Tabs: angular HUD style ── */
.stTabs [data-baseweb="tab-list"] { gap: 2px !important; }
.stTabs [data-baseweb="tab"] {
  background: var(--panel) !important;
  backdrop-filter: blur(8px) !important;
  border-radius: 0 !important;
  border: 1px solid var(--border) !important;
  clip-path: polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px) !important;
  padding: 8px 18px !important;
  font-family: var(--font-hud) !important;
  font-size: 11px !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  color: var(--muted) !important;
  transition: all 0.25s ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
  color: var(--cyan) !important;
  border-color: var(--border-strong) !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  color: var(--cyan) !important;
  border-color: var(--cyan) !important;
  box-shadow: var(--glow-cyan) !important;
  background: rgba(0, 240, 255, 0.08) !important;
}

/* ── Divider: data-line ── */
hr, .stMarkdown hr {
  border: none !important;
  height: 1px !important;
  background: linear-gradient(90deg, transparent, var(--cyan), transparent) !important;
  opacity: 0.3 !important;
}

/* ── Animated title shimmer ── */
@keyframes shimmer {
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
}
.sci-fi-title {
  font-family: var(--font-hud) !important;
  background: linear-gradient(90deg, var(--cyan), var(--violet), var(--cyan));
  background-size: 200% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: shimmer 3s linear infinite;
  text-transform: uppercase;
  letter-spacing: 4px;
}

/* ── Pulsing status dot ── */
@keyframes pulse-glow {
  0%, 100% { opacity: 1; box-shadow: 0 0 6px currentColor; }
  50% { opacity: 0.5; box-shadow: 0 0 12px currentColor; }
}
.status-dot {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  animation: pulse-glow 2s ease-in-out infinite;
}
.status-dot.active { background: var(--green); color: var(--green); }
.status-dot.critical { background: var(--red); color: var(--red); }
.status-dot.warning { background: var(--amber); color: var(--amber); }

/* ── Asset cards: HUD terminal ── */
.asset-card {
  background: var(--panel) !important;
  backdrop-filter: blur(10px) !important;
  border: 1px solid var(--border) !important;
  border-radius: 0 !important;
  clip-path: polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px);
  padding: 12px !important;
  transition: all 0.3s ease !important;
  cursor: pointer !important;
}
.asset-card:hover {
  border-color: var(--cyan) !important;
  box-shadow: var(--glow-cyan) !important;
  transform: translateY(-2px) !important;
}

/* ── 3-dot navigation (replaces floating arrows) ── */
.hud-nav-menu {
  position: fixed;
  top: 12px;
  right: 12px;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 4px;
}
.hud-nav-dots {
  display: flex;
  gap: 5px;
  cursor: pointer;
  padding: 8px 12px;
  background: rgba(5, 7, 13, 0.85);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border);
  clip-path: polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px);
  transition: all 0.25s ease;
}
.hud-nav-dots:hover {
  border-color: var(--cyan);
  box-shadow: var(--glow-cyan);
}
.hud-nav-dots .dot {
  width: 4px; height: 4px;
  border-radius: 50%;
  background: var(--cyan);
  box-shadow: 0 0 4px var(--cyan);
}
.hud-nav-popup {
  display: none;
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: rgba(5, 7, 13, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border-strong);
  clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
  min-width: 180px;
  z-index: 10000;
}
.hud-nav-popup.open { display: block; }
.hud-nav-popup a {
  display: block;
  padding: 10px 16px;
  font-family: var(--font-hud);
  font-size: 11px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text);
  text-decoration: none;
  border-bottom: 1px solid var(--border);
  transition: all 0.2s ease;
  cursor: pointer;
}
.hud-nav-popup a:last-child { border-bottom: none; }
.hud-nav-popup a:hover {
  background: rgba(0, 240, 255, 0.1);
  color: var(--cyan);
  text-shadow: 0 0 8px rgba(0, 240, 255, 0.4);
  padding-left: 22px;
}

/* ── Signal glow badges ── */
.signal-buy { box-shadow: 0 0 12px rgba(0, 255, 136, 0.3) !important; }
.signal-sell { box-shadow: 0 0 12px rgba(255, 59, 92, 0.3) !important; }

/* ── Glitch text effect ── */
@keyframes glitch {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-1px); }
  40% { transform: translateX(1px); }
  60% { transform: translateX(-0.5px); }
  80% { transform: translateX(0.5px); }
}
.glitch-text:hover { animation: glitch 0.3s ease; }

/* ── Typing/decode text reveal ── */
@keyframes type-reveal {
  from { clip-path: inset(0 100% 0 0); }
  to { clip-path: inset(0 0 0 0); }
}
.type-reveal {
  animation: type-reveal 1s ease-out;
}

/* ── Panel border with corner accents ── */
.hud-panel {
  position: relative;
  background: var(--panel);
  border: 1px solid var(--border);
  clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
}
.hud-panel::before, .hud-panel::after {
  content: "";
  position: absolute;
  width: 16px; height: 16px;
  border: 2px solid var(--cyan);
}
.hud-panel::before { top: 0; left: 0; border-right: none; border-bottom: none; }
.hud-panel::after { bottom: 0; right: 0; border-left: none; border-top: none; }
</style>
""", unsafe_allow_html=True)

# ── 3-Dot HUD Navigation (replaces floating arrows) ──
st.components.v1.html("""
<div id="hudNavMenu" style="position:fixed;top:14px;right:18px;z-index:999999;display:flex;flex-direction:column;align-items:flex-end;">
  <div id="hudDots" style="display:flex;gap:6px;cursor:pointer;padding:10px 14px;
       background:rgba(5,7,13,0.9);backdrop-filter:blur(10px);
       border:1px solid rgba(0,240,255,0.3);
       clip-path:polygon(6px 0,100% 0,100% calc(100% - 6px),calc(100% - 6px) 100%,0 100%,0 6px);
       transition:all 0.25s ease;"
       onmouseover="this.style.borderColor='#00F0FF';this.style.boxShadow='0 0 12px rgba(0,240,255,0.4)';"
       onmouseout="this.style.borderColor='rgba(0,240,255,0.3)';this.style.boxShadow='none';"
       onclick="var p=document.getElementById('hudPopup');p.style.display = (p.style.display==='block')?'none':'block';">
    <div style="width:5px;height:5px;border-radius:50%;background:#00F0FF;box-shadow:0 0 5px #00F0FF;"></div>
    <div style="width:5px;height:5px;border-radius:50%;background:#00F0FF;box-shadow:0 0 5px #00F0FF;"></div>
    <div style="width:5px;height:5px;border-radius:50%;background:#00F0FF;box-shadow:0 0 5px #00F0FF;"></div>
  </div>
  <div id="hudPopup" style="display:none;position:absolute;top:100%;right:0;margin-top:6px;
       background:rgba(5,7,13,0.95);backdrop-filter:blur(14px);
       border:1px solid rgba(0,240,255,0.4);min-width:160px;
       clip-path:polygon(8px 0,100% 0,100% calc(100% - 8px),calc(100% - 8px) 100%,0 100%,0 8px);">
    <div onclick="window.parent.window.scrollTo({top:0,behavior:'smooth'});document.getElementById('hudPopup').style.display='none';"
         style="padding:11px 16px;font-family:Orbitron,monospace;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#C8D4E3;cursor:pointer;border-bottom:1px solid rgba(0,240,255,0.1);transition:all 0.2s;"
         onmouseover="this.style.background='rgba(0,240,255,0.1)';this.style.color='#00F0FF';this.style.paddingLeft='22px';"
         onmouseout="this.style.background='none';this.style.color='#C8D4E3';this.style.paddingLeft='16px';">
      &#9650; Top
    </div>
    <div onclick="window.parent.window.scrollTo({top:999999,behavior:'smooth'});document.getElementById('hudPopup').style.display='none';"
         style="padding:11px 16px;font-family:Orbitron,monospace;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#C8D4E3;cursor:pointer;border-bottom:1px solid rgba(0,240,255,0.1);transition:all 0.2s;"
         onmouseover="this.style.background='rgba(0,240,255,0.1)';this.style.color='#00F0FF';this.style.paddingLeft='22px';"
         onmouseout="this.style.background='none';this.style.color='#C8D4E3';this.style.paddingLeft='16px';">
      &#9660; Bottom
    </div>
    <div onclick="document.getElementById('hudPopup').style.display='none';"
         style="padding:11px 16px;font-family:Orbitron,monospace;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#FF3B5C;cursor:pointer;transition:all 0.2s;"
         onmouseover="this.style.background='rgba(255,59,92,0.1)';this.style.paddingLeft='22px';"
         onmouseout="this.style.background='none';this.style.paddingLeft='16px';">
      &#10005; Close
    </div>
  </div>
</div>
<script>
  document.addEventListener('click', function(e) {
    if (!e.target.closest('#hudNavMenu')) {
      var p = document.getElementById('hudPopup');
      if (p) p.style.display = 'none';
    }
  });
</script>
""", height=0)

# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
# PASSWORD PROTECTION
# ──────────────────────────────────────────────
def check_password():
    """Returns True if the correct password is entered."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if st.session_state["authenticated"]:
        return True
    st.markdown("""
    <div style="display:flex;justify-content:center;align-items:center;min-height:60vh;">
      <div style="background:#151b23;border:1px solid #2a3441;border-radius:16px;padding:36px 40px;text-align:center;max-width:380px;">
        <h2 style="color:#e6edf3;margin:0 0 8px;">\U0001f512 Quant Desk</h2>
        <p style="color:#8b949e;font-size:13px;margin:0 0 20px;">Enter password to access the dashboard</p>
      </div>
    </div>
    """, unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password", placeholder="Enter password...", label_visibility="collapsed")
    if st.button("INITIATE", type="primary", use_container_width=True):
        if pwd == "dinesh@123":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("\u274c Incorrect password. Try again.")
    st.stop()
    return False

if not check_password():
    st.stop()
# ASSETS WATCHLIST
# ──────────────────────────────────────────────

ASSETS = [
    # India - NSE
    {"ticker": "RELIANCE.NS",   "tv": "NSE:RELIANCE",    "name": "Reliance Industries",      "type": "NSE",  "logo": "RELIANCE"},
    {"ticker": "TCS.NS",        "tv": "NSE:TCS",          "name": "Tata Consultancy Services","type": "NSE",  "logo": "TCS"},
    {"ticker": "INFY.NS",       "tv": "NSE:INFY",         "name": "Infosys",                  "type": "NSE",  "logo": "INFY"},
    {"ticker": "HDFCBANK.NS",   "tv": "NSE:HDFCBANK",     "name": "HDFC Bank",               "type": "NSE",  "logo": "HDFCBANK"},
    {"ticker": "ICICIBANK.NS",  "tv": "NSE:ICICIBANK",    "name": "ICICI Bank",               "type": "NSE",  "logo": "ICICIBANK"},
    {"ticker": "SBIN.NS",       "tv": "NSE:SBIN",         "name": "State Bank of India",     "type": "NSE",  "logo": "SBIN"},
    {"ticker": "TATAMOTORS.NS", "tv": "NSE:TATAMOTORS",  "name": "Tata Motors",             "type": "NSE",  "logo": "TATAMOTORS"},
    {"ticker": "ADANIENT.NS",   "tv": "NSE:ADANIENT",    "name": "Adani Enterprises",       "type": "NSE",  "logo": "ADANIENT"},
    {"ticker": "BAJFINANCE.NS", "tv": "NSE:BAJFINANCE",   "name": "Bajaj Finance",           "type": "NSE",  "logo": "BAJFINANCE"},
    {"ticker": "WIPRO.NS",      "tv": "NSE:WIPRO",        "name": "Wipro",                   "type": "NSE",  "logo": "WIPRO"},
    {"ticker": "LT.NS",         "tv": "NSE:LT",           "name": "Larsen & Toubro",         "type": "NSE",  "logo": "LT"},
    {"ticker": "HINDUNILVR.NS", "tv": "NSE:HINDUNILVR",  "name": "Hindustan Unilever",      "type": "NSE",  "logo": "HINDUNILVR"},
    {"ticker": "BHARTIARTL.NS", "tv": "NSE:BHARTIARTL",  "name": "Bharti Airtel",           "type": "NSE",  "logo": "BHARTIARTL"},
    {"ticker": "MARUTI.NS",     "tv": "NSE:MARUTI",       "name": "Maruti Suzuki",           "type": "NSE",  "logo": "MARUTI"},
    {"ticker": "AXISBANK.NS",   "tv": "NSE:AXISBANK",    "name": "Axis Bank",               "type": "NSE",  "logo": "AXISBANK"},
    {"ticker": "KOTAKBANK.NS",  "tv": "NSE:KOTAKBANK",    "name": "Kotak Mahindra Bank",    "type": "NSE",  "logo": "KOTAKBANK"},
    {"ticker": "SUNPHARMA.NS",  "tv": "NSE:SUNPHARMA",   "name": "Sun Pharma",              "type": "NSE",  "logo": "SUNPHARMA"},
    {"ticker": "ITC.NS",        "tv": "NSE:ITC",          "name": "ITC Limited",             "type": "NSE",  "logo": "ITC"},
    {"ticker": "^NSEI",         "tv": "NSE:NIFTY",        "name": "Nifty 50 Index",          "type": "Index", "logo": "NIFTY50"},
    {"ticker": "^NSEBANK",      "tv": "NSE:NIFTYBANK",   "name": "Bank Nifty Index",       "type": "Index", "logo": "NIFTYBANK"},
    # US - NASDAQ / NYSE
    {"ticker": "AAPL",          "tv": "NASDAQ:AAPL",      "name": "Apple Inc",               "type": "NASDAQ", "logo": "AAPL"},
    {"ticker": "MSFT",          "tv": "NASDAQ:MSFT",      "name": "Microsoft",               "type": "NASDAQ", "logo": "MSFT"},
    {"ticker": "AMZN",          "tv": "NASDAQ:AMZN",      "name": "Amazon",                  "type": "NASDAQ", "logo": "AMZN"},
    {"ticker": "GOOGL",         "tv": "NASDAQ:GOOGL",     "name": "Alphabet (Google)",       "type": "NASDAQ", "logo": "GOOGL"},
    {"ticker": "TSLA",          "tv": "NASDAQ:TSLA",      "name": "Tesla",                   "type": "NASDAQ", "logo": "TSLA"},
    {"ticker": "META",          "tv": "NASDAQ:META",      "name": "Meta Platforms",          "type": "NASDAQ", "logo": "META"},
    {"ticker": "NVDA",          "tv": "NASDAQ:NVDA",     "name": "Nvidia",                  "type": "NASDAQ", "logo": "NVDA"},
    {"ticker": "NFLX",          "tv": "NASDAQ:NFLX",      "name": "Netflix",                 "type": "NASDAQ", "logo": "NFLX"},
    {"ticker": "INTC",          "tv": "NASDAQ:INTC",     "name": "Intel",                   "type": "NASDAQ", "logo": "INTC"},
    {"ticker": "KO",            "tv": "NYSE:KO",          "name": "Coca-Cola",               "type": "NYSE",   "logo": "KO"},
    {"ticker": "WMT",           "tv": "NYSE:WMT",         "name": "Walmart",                 "type": "NYSE",   "logo": "WMT"},
    {"ticker": "JPM",           "tv": "NYSE:JPM",         "name": "JPMorgan Chase",          "type": "NYSE",   "logo": "JPM"},
    # Crypto
    {"ticker": "BTC-USD",       "tv": "BINANCE:BTCUSDT",  "name": "Bitcoin",                 "type": "Crypto", "logo": "BTC"},
    {"ticker": "ETH-USD",       "tv": "BINANCE:ETHUSDT",  "name": "Ethereum",                "type": "Crypto", "logo": "ETH"},
    {"ticker": "SOL-USD",       "tv": "BINANCE:SOLUSDT",  "name": "Solana",                  "type": "Crypto", "logo": "SOL"},
    {"ticker": "DOGE-USD",      "tv": "BINANCE:DOGEUSDT", "name": "Dogecoin",                "type": "Crypto", "logo": "DOGE"},
    # Commodities
    {"ticker": "GC=F",          "tv": "TVC:GOLD",         "name": "Gold Futures",            "type": "Commodity", "logo": "GOLD"},
]

# ── Navigation Tabs ──
NAV_TABS = ["Dashboard", "Prime Terminal", "AI Analysis", "Fundamental Engine", "Strategy Bot", "Backtester", "Quant Tools", "Quant Trade", "Quant Trading", "Portfolio", "Trading Bot"]
active_tab = st.sidebar.selectbox("Navigate", NAV_TABS, key="nav_tab")

if active_tab != "Dashboard":
    if active_tab == "Strategy Bot":
        from modules.strategy_bot import render_strategy_bot
        render_strategy_bot()
    elif active_tab == "Backtester":
        from modules.backtester import render_backtester
    elif active_tab == "Quant Tools":
        from modules.quant_tools import render_quant_tools
        render_quant_tools()
        render_backtester()
    elif active_tab == "Quant Trade":
        from modules.quant_trade import render_quant_trade
        render_quant_trade()
    elif active_tab == "Quant Trading":
        from modules.quant_trading import render_quant_trading
        render_quant_trading()
    elif active_tab == "Portfolio":
        from modules.portfolio_tracker import render_portfolio_tracker
        render_portfolio_tracker()
    elif active_tab == "AI Analysis":
        from modules.ai_analysis import render_ai_analysis
        render_ai_analysis()
    elif active_tab == "Prime Terminal":
        from modules.prime_terminal import render_prime_terminal
        render_prime_terminal()
    elif active_tab == "Fundamental Engine":
        from modules.fundamental_engine_ui import render_fundamental_engine_ui
        render_fundamental_engine_ui()
    elif active_tab == "Trading Bot":
        from modules.trading_bot import render_trading_bot
        render_trading_bot()
    st.stop()

BROKERS = [
    {"id": "zerodha",  "name": "Zerodha Kite", "note": "Kite Connect API",       "fields": ["API Key", "API Secret"], "color": "#387ed1", "logo": "⚡"},
    {"id": "groww",    "name": "Groww",        "note": "Groww Official API",  "fields": ["API Key", "API Secret", "Client Code", "TOTP Secret"], "color": "#00d09c", "logo": "🌱"},
    {"id": "upstox",   "name": "Upstox",      "note": "Upstox API v2",          "fields": ["API Key", "API Secret", "Redirect URI"], "color": "#562ac8", "logo": "💥"},
    {"id": "angelone", "name": "Angel One",   "note": "SmartAPI",               "fields": ["API Key", "Client ID", "PIN"], "color": "#f47216", "logo": "💡"},
    {"id": "fyers",    "name": "Fyers",        "note": "Fyers API v3",          "fields": ["App ID", "Secret Key"], "color": "#00baf2", "logo": "🔥"},
    {"id": "generic",  "name": "Any broker",   "note": "Custom REST / WebSocket", "fields": ["Base URL", "API Key"], "color": "#888", "logo": "🔗"},
]

# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────

if "selected_asset" not in st.session_state:
    st.session_state.selected_asset = None
if "show_analysis" not in st.session_state:
    st.session_state.show_analysis = False
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "voice_generated" not in st.session_state:
    st.session_state.voice_generated = None
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "connection" not in st.session_state:
    st.session_state.connection = None
if "credentials" not in st.session_state:
    st.session_state.credentials = {}
if "period" not in st.session_state:
    st.session_state.period = "5y"
if "interval" not in st.session_state:
    st.session_state.interval = "1d"
if "backtest_result" not in st.session_state:
    st.session_state.backtest_result = None
if "order_message" not in st.session_state:
    st.session_state.order_message = None

# ──────────────────────────────────────────────
# DATA FETCH (yfinance)
# ──────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_ohlc(ticker, period="6mo", interval="1d"):
    """Fetch OHLC data (real via yfinance, safe synthetic fallback if rate-limited).
    Returns DataFrame with lowercase columns, or None if truly no data at all."""
    try:
        df, is_synthetic = get_download(ticker, period=period, interval=interval)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        date_col = "Date" if "Date" in df.columns else "Datetime"
        df = df.rename(columns={date_col: "date"})
        # Rename to lowercase
        rename_map = {}
        for col in df.columns:
            cl = col.lower()
            if cl == "open": rename_map[col] = "open"
            elif cl == "high": rename_map[col] = "high"
            elif cl == "low": rename_map[col] = "low"
            elif cl == "close": rename_map[col] = "close"
            elif cl == "volume": rename_map[col] = "volume"
        df = df.rename(columns=rename_map)
        # Ensure numeric
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close"])
        df.attrs["synthetic"] = is_synthetic
        return df
    except Exception:
        return None

# ──────────────────────────────────────────────
# TECHNICAL INDICATORS
# ──────────────────────────────────────────────

def sma(series, period):
    return series.rolling(period).mean().round(2)

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean().round(2)

def rsi(series, period=14):
    diff = series.diff()
    gain = diff.clip(lower=0)
    loss = -diff.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = (100 - 100 / (1 + rs))
    out.iloc[:period] = np.nan
    return out.round(2)

def macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = (ema12 - ema26).round(2)
    signal = macd_line.ewm(span=9, adjust=False).mean().round(2)
    hist = (macd_line - signal).round(2)
    return macd_line, signal, hist

def bollinger(series, period=20, mult=2):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std(ddof=0)
    upper = (mid + mult * std).round(2)
    lower = (mid - mult * std).round(2)
    return upper, mid, lower

def detect_patterns(df):
    """Detect candlestick patterns on last 3 candles — TradingView style."""
    n = len(df)
    if n < 3:
        return ["Not enough data for pattern detection"]
    last = df.iloc[-1]; prev = df.iloc[-2]; prev2 = df.iloc[-3]
    body = abs(last["close"] - last["open"])
    rng = (last["high"] - last["low"]) or 1
    upper_wick = last["high"] - max(last["open"], last["close"])
    lower_wick = min(last["open"], last["close"]) - last["low"]
    prev_body = abs(prev["close"] - prev["open"])
    prev_rng = (prev["high"] - prev["low"]) or 1
    prev2_body = abs(prev2["close"] - prev2["open"])
    patterns = []

    # ── Single candle patterns ──
    if body / rng < 0.12:
        patterns.append("\U0001f7e1 Doji \u2014 indecision, possible reversal")
    if body / rng < 0.05:
        patterns.append("\U0001f7e1 Dragonfly Doji \u2014 strong bullish reversal signal (if at support)")
    if lower_wick > body * 2 and upper_wick < body * 0.5 and last["close"] > last["open"]:
        patterns.append("\U0001f7e2 Hammer \u2014 bullish reversal signal")
    if upper_wick > body * 2 and lower_wick < body * 0.5 and last["close"] < last["open"]:
        patterns.append("\U0001f534 Shooting Star \u2014 bearish reversal signal")
    if lower_wick > body * 2 and upper_wick < body * 0.3 and last["close"] < last["open"]:
        patterns.append("\U0001f534 Hanging Man \u2014 bearish reversal (at top of uptrend)")
    if body / rng > 0.9 and last["close"] > last["open"]:
        patterns.append("\U0001f7e2 Bullish Marubozu \u2014 strong buying pressure, continuation")
    if body / rng > 0.9 and last["close"] < last["open"]:
        patterns.append("\U0001f534 Bearish Marubozu \u2014 strong selling pressure, continuation")
    if lower_wick > body * 1.5 and upper_wick > body * 1.5 and body / rng < 0.3:
        patterns.append("\u26aa Spinning Top \u2014 indecision, neither buyers nor sellers in control")

    # ── Two candle patterns ──
    if prev["close"] < prev["open"] and last["close"] > last["open"] and last["close"] > prev["open"] and last["open"] < prev["close"]:
        patterns.append("\U0001f7e2 Bullish Engulfing \u2014 buyers overwhelming sellers")
    if prev["close"] > prev["open"] and last["close"] < last["open"] and last["close"] < prev["open"] and last["open"] > prev["close"]:
        patterns.append("\U0001f534 Bearish Engulfing \u2014 sellers overwhelming buyers")
    if prev["close"] < prev["open"] and last["close"] > last["open"] and last["close"] > prev["close"] and last["open"] < prev["close"] and (last["close"] - last["open"]) < prev_body:
        patterns.append("\U0001f7e2 Piercing Line \u2014 partial bullish reversal")
    if prev["close"] > prev["open"] and last["close"] < last["open"] and last["close"] < prev["close"] and last["open"] > prev["open"] and (prev["close"] - last["close"]) < prev_body:
        patterns.append("\U0001f534 Dark Cloud Cover \u2014 partial bearish reversal")
    if prev["close"] > prev["open"] and last["close"] > prev["close"] and last["open"] > prev["open"] and last["close"] > last["open"]:
        patterns.append("\U0001f7e2 Upside Tasuki Gap \u2014 bullish continuation (gap up)")
    if prev["close"] < prev["open"] and last["close"] < prev["close"] and last["open"] < prev["open"] and last["close"] < last["open"]:
        patterns.append("\U0001f534 Downside Tasuki Gap \u2014 bearish continuation (gap down)")

    # ── Three candle patterns ──
    if (prev2["close"] < prev2["open"]
        and abs(prev["close"] - prev["open"]) / ((prev["high"] - prev["low"]) or 1) < 0.3
        and last["close"] > last["open"] and last["close"] > (prev2["open"] + prev2["close"]) / 2):
        patterns.append("\U0001f7e2 Morning Star \u2014 3-candle bullish reversal")
    if (prev2["close"] > prev2["open"]
        and abs(prev["close"] - prev["open"]) / ((prev["high"] - prev["low"]) or 1) < 0.3
        and last["close"] < last["open"] and last["close"] < (prev2["open"] + prev2["close"]) / 2):
        patterns.append("\U0001f534 Evening Star \u2014 3-candle bearish reversal")
    if (prev2["close"] > prev2["open"] and prev["close"] > prev["open"] and last["close"] > last["open"]
        and last["close"] > prev["close"] and prev["close"] > prev2["close"]):
        patterns.append("\U0001f7e2 Three White Soldiers \u2014 strong bullish reversal")
    if (prev2["close"] < prev2["open"] and prev["close"] < prev["open"] and last["close"] < last["open"]
        and last["close"] < prev["close"] and prev["close"] < prev2["close"]):
        patterns.append("\U0001f534 Three Black Crows \u2014 strong bearish reversal")
    if (prev2["close"] > prev2["open"] and prev["close"] > prev["open"] and last["close"] < last["open"]
        and last["open"] > prev["close"] and last["close"] > prev["open"]):
        patterns.append("\U0001f534 Two Black Gapping \u2014 bearish continuation after gap")
    if (prev2["close"] < prev2["open"] and prev["close"] < prev["open"] and last["close"] > last["open"]
        and last["open"] < prev["close"] and last["close"] > prev["open"]):
        patterns.append("\U0001f7e2 Abandoned Baby (bullish) \u2014 rare strong reversal")

    if not patterns:
        patterns.append("\u27a1\ufe0f No strong candlestick pattern detected \u2014 trend continuation likely")
    return patterns


# ──────────────────────────────────────────────
# PIVOT DETECTION & TREND LINES
# ──────────────────────────────────────────────

def find_pivots(df, lookback=3):
    highs, lows = [], []
    n = len(df)
    for i in range(lookback, n - lookback):
        is_high = True
        is_low = True
        for j in range(i - lookback, i + lookback + 1):
            if j == i:
                continue
            if df["high"].iloc[j] >= df["high"].iloc[i]:
                is_high = False
            if df["low"].iloc[j] <= df["low"].iloc[i]:
                is_low = False
        if is_high:
            highs.append({"idx": i, "price": df["high"].iloc[i]})
        if is_low:
            lows.append({"idx": i, "price": df["low"].iloc[i]})
    return {"highs": highs, "lows": lows}

def linear_regression(points):
    n_pts = len(points)
    if n_pts < 2:
        return None
    sum_x = sum(p["idx"] for p in points)
    sum_y = sum(p["price"] for p in points)
    sum_xy = sum(p["idx"] * p["price"] for p in points)
    sum_xx = sum(p["idx"] ** 2 for p in points)
    denom = n_pts * sum_xx - sum_x * sum_x
    if denom == 0:
        return None
    slope = (n_pts * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n_pts
    return {"slope": slope, "intercept": intercept}

# ──────────────────────────────────────────────
# ANALYSIS (chart data)
# ──────────────────────────────────────────────

def build_analysis(df):
    closes = df["close"]
    last = df.iloc[-1]
    first = df.iloc[0]
    prev = df.iloc[-2]

    change_pct = round(((last["close"] - first["close"]) / first["close"]) * 100, 2)
    day_change_pct = round(((last["close"] - prev["close"]) / prev["close"]) * 100, 2)

    sma20_vals = sma(closes, 20)
    sma50_vals = sma(closes, 50)
    sma200_vals = sma(closes, 200)
    rsi_vals = rsi(closes)
    macd_line, signal_line, hist = macd(closes)
    bb_upper, bb_mid, bb_lower = bollinger(closes)

    def last_val(s):
        try:
            v = s.iloc[-1]
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return None
            return float(v)
        except (IndexError, TypeError, ValueError):
            return None

    last_rsi = last_val(rsi_vals)
    last_macd = last_val(macd_line)
    last_signal = last_val(signal_line)
    last_hist = last_val(hist)
    last_sma20 = last_val(sma20_vals)
    last_sma50 = last_val(sma50_vals)
    last_sma200 = last_val(sma200_vals)
    last_bb_upper = last_val(bb_upper)
    last_bb_lower = last_val(bb_lower)

    avg_vol = df["volume"].iloc[-20:].mean() if "volume" in df.columns else 0
    vol_ratio = round(last["volume"] / avg_vol, 2) if avg_vol else 0

    returns = closes.pct_change().dropna()
    daily_vol = returns.std()
    annualized_vol = round(daily_vol * np.sqrt(252) * 100, 2) if daily_vol else 0
    mean_return = returns.mean()
    sharpe = round((mean_return * 252) / (daily_vol * np.sqrt(252)) if daily_vol else 0, 2)

    # Skewness & Kurtosis
    n_ret = len(returns)
    skewness = round(float(n_ret / ((n_ret-1)*(n_ret-2)) * np.sum(((returns - mean_return) / daily_vol) ** 3)), 3) if daily_vol and n_ret > 2 else 0
    kurtosis = round(float(n_ret*(n_ret+1) / ((n_ret-1)*(n_ret-2)*(n_ret-3)) * np.sum(((returns - mean_return) / daily_vol) ** 4) - 3*(n_ret-1)**2/((n_ret-2)*(n_ret-3))), 3) if daily_vol and n_ret > 3 else 0

    # Sortino ratio
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
    sortino = round(float(mean_return * 252 / downside_std), 2) if downside_std and downside_std != 0 else 0

    # Golden/Death Cross
    golden_cross = False
    death_cross = False
    if last_sma50 is not None and last_sma200 is not None:
        prev_sma50 = sma50_vals.iloc[-2] if len(sma50_vals) > 1 else None
        prev_sma200 = sma200_vals.iloc[-2] if len(sma200_vals) > 1 else None
        if prev_sma50 is not None and prev_sma200 is not None and not np.isnan(prev_sma50) and not np.isnan(prev_sma200):
            if last_sma50 > last_sma200 and prev_sma50 <= prev_sma200:
                golden_cross = True
            elif last_sma50 < last_sma200 and prev_sma50 >= prev_sma200:
                death_cross = True

    bull, bear = 0, 0
    if last_rsi is not None:
        if last_rsi < 30: bull += 1
        elif last_rsi > 70: bear += 1
    if last_macd is not None and last_signal is not None:
        if last_macd > last_signal: bull += 1
        else: bear += 1
    if last_sma20 is not None and last_sma50 is not None:
        if last_sma20 > last_sma50: bull += 1
        else: bear += 1
    if last_bb_lower is not None:
        if last["close"] < last_bb_lower: bull += 1
        elif last_bb_upper is not None and last["close"] > last_bb_upper: bear += 1
    if last["close"] > first["close"]: bull += 1
    else: bear += 1

    if bull - bear >= 2:
        verdict = "Bullish bias 🟢"
    elif bear - bull >= 2:
        verdict = "Bearish bias 🔴"
    else:
        verdict = "Neutral / range-bound ⚪"

    patterns = detect_patterns(df)
    support = round(df["low"].iloc[-20:].min(), 2)
    resistance = round(df["high"].iloc[-20:].max(), 2)

    pivots = find_pivots(df)
    res_trend = linear_regression(pivots["highs"][-6:]) if len(pivots["highs"]) >= 2 else None
    sup_trend = linear_regression(pivots["lows"][-6:]) if len(pivots["lows"]) >= 2 else None

    n_candles = len(df)
    res_trend_vals = None
    sup_trend_vals = None
    if res_trend:
        res_trend_vals = [round(res_trend["slope"] * i + res_trend["intercept"], 2) for i in range(n_candles)]
    if sup_trend:
        sup_trend_vals = [round(sup_trend["slope"] * i + sup_trend["intercept"], 2) for i in range(n_candles)]

    return {
        "change_pct": change_pct, "day_change_pct": day_change_pct,
        "last_rsi": last_rsi, "last_macd": last_macd, "last_signal": last_signal,
        "last_hist": last_hist, "last_sma20": last_sma20, "last_sma50": last_sma50,
        "bb_upper": last_bb_upper, "bb_lower": last_bb_lower,
        "avg_vol": avg_vol, "vol_ratio": vol_ratio,
        "annualized_vol": annualized_vol, "sharpe": sharpe,
        "sortino": sortino, "skewness": skewness, "kurtosis": kurtosis,
        "golden_cross": golden_cross, "death_cross": death_cross, "last_sma200": last_sma200,
        "verdict": verdict, "bull_signals": bull, "bear_signals": bear,
        "patterns": patterns, "support": support, "resistance": resistance,
        "sma20": sma20_vals, "sma50": sma50_vals, "sma200": sma200_vals,
        "rsi_vals": rsi_vals, "macd_line": macd_line, "signal_line": signal_line,
        "hist": hist, "bb_upper_series": bb_upper, "bb_lower_series": bb_lower, "bb_mid_series": bb_mid,
        "res_trend": res_trend, "sup_trend": sup_trend,
        "res_trend_vals": res_trend_vals, "sup_trend_vals": sup_trend_vals,
        "pivots": pivots}

# ──────────────────────────────────────────────
# AI ANALYSIS (quant + technical + summary)
# ──────────────────────────────────────────────

def compute_ai_summary(df):
    """Compute indicators and build a quant + technical + overall summary."""
    close = df["close"]

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_val = ema12 - ema26
    signal_val = macd_val.ewm(span=9, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))

    daily_returns = close.pct_change().dropna()
    volatility = float(daily_returns.std() * np.sqrt(252) * 100) if len(daily_returns) > 0 else 0
    sharpe = float((daily_returns.mean() / daily_returns.std()) * np.sqrt(252)) if len(daily_returns) > 0 and daily_returns.std() != 0 else 0

    last_close = float(close.iloc[-1])
    last_sma20 = float(sma20.iloc[-1]) if not pd.isna(sma20.iloc[-1]) else None
    last_sma50 = float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else None
    last_rsi = float(rsi_val.iloc[-1]) if not pd.isna(rsi_val.iloc[-1]) else None
    last_macd = float(macd_val.iloc[-1]) if not pd.isna(macd_val.iloc[-1]) else 0
    last_signal = float(signal_val.iloc[-1]) if not pd.isna(signal_val.iloc[-1]) else 0

    period_high = round(float(close.max()), 2)
    period_low = round(float(close.min()), 2)

    # Build summary
    trend = "uptrend" if last_sma20 and last_close > last_sma20 else "downtrend"
    if last_sma20 and last_sma50:
        trend_strength = "strong" if (last_sma20 > last_sma50) == (trend == "uptrend") else "weak/mixed"
    else:
        trend_strength = "insufficient data"

    if last_rsi is None:
        rsi_state = "not enough data"
    elif last_rsi > 70:
        rsi_state = "overbought"
    elif last_rsi < 30:
        rsi_state = "oversold"
    else:
        rsi_state = "neutral"

    macd_state = "bullish crossover" if last_macd > last_signal else "bearish crossover"

    quant_text = (
        f"Annualized volatility is {round(volatility, 2)}%, with a Sharpe ratio of "
        f"{round(sharpe, 2)}. Price is trading between a period low of {period_low} and "
        f"high of {period_high}, currently at {round(last_close, 2)}."
    )

    technical_text = (
        f"Price is in a {trend} ({trend_strength}) relative to the 20/50-day SMA "
        f"({round(last_sma20, 2) if last_sma20 else 'N/A'}/{round(last_sma50, 2) if last_sma50 else 'N/A'}). "
        f"RSI(14) is at {round(last_rsi, 2) if last_rsi else 'N/A'} ({rsi_state}). "
        f"MACD ({round(last_macd, 4)}) vs signal ({round(last_signal, 4)}) indicates a {macd_state}."
    )

    overall_bias = "bullish" if trend == "uptrend" and last_macd > last_signal else "cautious/bearish" if trend == "downtrend" and last_macd < last_signal else "mixed"
    rsi_advice = "watch for a pullback before entry" if rsi_state == "overbought" else "watch for reversal confirmation" if rsi_state == "oversold" else "no extreme momentum signal currently"

    overall_summary = (
        f"Overall bias leans {overall_bias}. "
        f"RSI suggests {rsi_state} conditions, so {rsi_advice}. "
        f"Use the period range ({period_low}\u2013{period_high}) as reference support/resistance."
    )

    return {
        "quant": quant_text,
        "technical": technical_text,
        "summary": overall_summary,
        "indicators": {
            "last_close": round(last_close, 2),
            "sma20": round(last_sma20, 2) if last_sma20 else None,
            "sma50": round(last_sma50, 2) if last_sma50 else None,
            "rsi14": round(last_rsi, 2) if last_rsi else None,
            "macd": round(last_macd, 4),
            "macd_signal": round(last_signal, 4),
            "volatility_pct": round(volatility, 2),
            "sharpe": round(sharpe, 2),
            "period_high": period_high,
            "period_low": period_low}}


# ──────────────────────────────────────────────
# ENHANCED SUPPORT/RESISTANCE (swing-based with touch counts)
# ──────────────────────────────────────────────

def find_support_resistance_enhanced(df, window=10, tolerance=0.015):
    """Find swing highs/lows, cluster nearby levels, return top support & resistance
    with touch counts (strength). Mirrors the standalone dashboard's logic."""
    highs = df["high"]
    lows = df["low"]

    swing_highs, swing_lows = [], []
    for i in range(window, len(df) - window):
        if highs.iloc[i] == highs.iloc[i - window:i + window + 1].max():
            swing_highs.append(highs.iloc[i])
        if lows.iloc[i] == lows.iloc[i - window:i + window + 1].min():
            swing_lows.append(lows.iloc[i])

    def cluster(levels):
        levels = sorted(levels)
        clusters = []
        for lvl in levels:
            placed = False
            for c in clusters:
                if abs(lvl - c[-1]) / c[-1] < tolerance:
                    c.append(lvl)
                    placed = True
                    break
            if not placed:
                clusters.append([lvl])
        return sorted([(sum(c) / len(c), len(c)) for c in clusters], key=lambda x: -x[1])

    resistance_levels = cluster(swing_highs)
    support_levels = cluster(swing_lows)

    current_price = df["close"].iloc[-1]
    resistance = [r for r in resistance_levels if r[0] > current_price]
    support = [s for s in support_levels if s[0] < current_price]

    nearest_resistance = min(resistance, key=lambda x: x[0]) if resistance else None
    nearest_support = max(support, key=lambda x: x[0]) if support else None

    return nearest_support, nearest_resistance, support_levels[:5], resistance_levels[:5]


# ──────────────────────────────────────────────
# INDIVIDUAL INDICATOR STATUS (Signals Summary)
# ──────────────────────────────────────────────

def generate_indicator_signals(df):
    """Generate individual indicator verdicts — RSI, MACD, Trend, Bollinger.
    Returns a list of (indicator_name, signal_text, value_str) tuples."""
    latest = df.iloc[-1]
    close = df["close"]
    signals = []

    # ── RSI ──
    rsi_val = rsi(close, 14).iloc[-1]
    if pd.notna(rsi_val):
        if rsi_val > 70:
            signals.append(("RSI (14)", "Overbought", f"{rsi_val:.1f}"))
        elif rsi_val < 30:
            signals.append(("RSI (14)", "Oversold", f"{rsi_val:.1f}"))
        else:
            signals.append(("RSI (14)", "Neutral", f"{rsi_val:.1f}"))
    else:
        signals.append(("RSI (14)", "—", "—"))

    # ── MACD ──
    macd_line, signal_line, hist = macd(close)
    if pd.notna(macd_line.iloc[-1]) and pd.notna(signal_line.iloc[-1]):
        if macd_line.iloc[-1] > signal_line.iloc[-1]:
            signals.append(("MACD (12,26,9)", "Bullish Crossover", f"{hist.iloc[-1]:.4f}"))
        else:
            signals.append(("MACD (12,26,9)", "Bearish Crossover", f"{hist.iloc[-1]:.4f}"))
    else:
        signals.append(("MACD (12,26,9)", "—", "—"))

    # ── Trend (SMA50 vs SMA200) ──
    sma50_val = close.rolling(50).mean().iloc[-1]
    sma200_val = close.rolling(200).mean().iloc[-1]
    if pd.notna(sma50_val) and pd.notna(sma200_val):
        if latest["close"] > sma50_val > sma200_val:
            signals.append(("Trend", "Strong Uptrend", "Close > SMA50 > SMA200"))
        elif latest["close"] < sma50_val < sma200_val:
            signals.append(("Trend", "Strong Downtrend", "Close < SMA50 < SMA200"))
        else:
            signals.append(("Trend", "Sideways / Mixed", "—"))
    else:
        signals.append(("Trend", "—", "Not enough data"))

    # ── Bollinger Bands ──
    bb_upper, bb_mid, bb_lower = bollinger(close, 20, 2)
    if pd.notna(bb_upper.iloc[-1]) and pd.notna(bb_lower.iloc[-1]):
        if latest["close"] > bb_upper.iloc[-1]:
            signals.append(("Bollinger Bands", "Above Upper Band (Overextended)", "—"))
        elif latest["close"] < bb_lower.iloc[-1]:
            signals.append(("Bollinger Bands", "Below Lower Band (Oversold zone)", "—"))
        else:
            signals.append(("Bollinger Bands", "Within Bands (Normal)", "—"))
    else:
        signals.append(("Bollinger Bands", "—", "—"))

    # ── EMA20 vs SMA20 ──
    ema20_val = close.ewm(span=20, adjust=False).mean().iloc[-1]
    sma20_val = close.rolling(20).mean().iloc[-1]
    if pd.notna(ema20_val) and pd.notna(sma20_val):
        if ema20_val > sma20_val:
            signals.append(("EMA 20 vs SMA 20", "Bullish (EMA above)", f"{ema20_val:.2f} > {sma20_val:.2f}"))
        else:
            signals.append(("EMA 20 vs SMA 20", "Bearish (EMA below)", f"{ema20_val:.2f} < {sma20_val:.2f}"))
    else:
        signals.append(("EMA 20 vs SMA 20", "—", "—"))

    return signals


# ──────────────────────────────────────────────
# ENHANCED CANDLESTICK PATTERN DETECTION (scan last 6 candles)
# ──────────────────────────────────────────────

def detect_patterns_enhanced(df):
    """Detect candlestick patterns scanning the last ~6 candles (enhanced version).
    Merges with the existing 3-candle detection for comprehensive coverage."""
    n = len(df)
    if n < 7:
        return detect_patterns(df)

    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    body = (c - o).abs()
    range_ = (h - l).replace(0, np.nan)
    upper_wick = h - df[["open", "close"]].max(axis=1)
    lower_wick = df[["open", "close"]].min(axis=1) - l

    found = {}  # date -> list of (pattern_name, type)

    for i in range(max(1, n - 6), n):
        date = str(df["date"].iloc[i].date()) if "date" in df.columns else str(i)
        bo, bh, bl, bc = o.iloc[i], h.iloc[i], l.iloc[i], c.iloc[i]
        b = body.iloc[i]
        r = range_.iloc[i]
        uw = upper_wick.iloc[i]
        lw = lower_wick.iloc[i]

        if pd.isna(r) or r == 0:
            continue

        patterns_at_date = []

        # Doji
        if b / r < 0.1:
            patterns_at_date.append(("Doji", "Indecision", "🟡"))
        # Hammer
        elif lw > 2 * b and uw < b and bc >= bo:
            patterns_at_date.append(("Hammer", "Bullish reversal", "🟢"))
        # Shooting Star
        elif uw > 2 * b and lw < b and bc <= bo:
            patterns_at_date.append(("Shooting Star", "Bearish reversal", "🔴"))
        # Hanging Man
        elif lw > 2 * b and uw < b * 0.3 and bc < bo:
            patterns_at_date.append(("Hanging Man", "Bearish reversal", "🔴"))
        # Bullish Marubozu
        elif b / r > 0.9 and bc > bo:
            patterns_at_date.append(("Bullish Marubozu", "Strong buying", "🟢"))
        # Bearish Marubozu
        elif b / r > 0.9 and bc < bo:
            patterns_at_date.append(("Bearish Marubozu", "Strong selling", "🔴"))
        # Spinning Top
        elif lw > b * 1.5 and uw > b * 1.5 and b / r < 0.3:
            patterns_at_date.append(("Spinning Top", "Indecision", "⚪"))

        # Two-candle patterns
        if i > 0:
            po, pc = o.iloc[i - 1], c.iloc[i - 1]
            prev_bearish = pc < po
            prev_bullish = pc > po
            curr_bullish = bc > bo
            curr_bearish = bc < bo

            if prev_bearish and curr_bullish and bc > po and bo < pc:
                patterns_at_date.append(("Bullish Engulfing", "Bullish reversal", "🟢"))
            elif prev_bullish and curr_bearish and bo > pc and bc < po:
                patterns_at_date.append(("Bearish Engulfing", "Bearish reversal", "🔴"))
            # Piercing Line
            if prev_bearish and curr_bullish and bc > po and bo < pc and (bc - bo) < body.iloc[i-1]:
                patterns_at_date.append(("Piercing Line", "Partial bullish reversal", "🟢"))
            # Dark Cloud Cover
            if prev_bullish and curr_bearish and bc < po and bo > pc and (po - bc) < body.iloc[i-1]:
                patterns_at_date.append(("Dark Cloud Cover", "Partial bearish reversal", "🔴"))

        # Three-candle patterns
        if i > 1:
            prev2_c = c.iloc[i - 2]
            prev2_o = o.iloc[i - 2]
            prev_c = c.iloc[i - 1]
            prev_o = o.iloc[i - 1]
            # Morning Star
            if prev2_c < prev2_o and abs(prev_c - prev_o) / ((h.iloc[i-1] - l.iloc[i-1]) or 1) < 0.3 and bc > bo and bc > (prev2_o + prev2_c) / 2:
                patterns_at_date.append(("Morning Star", "3-candle bullish reversal", "🟢"))
            # Evening Star
            if prev2_c > prev2_o and abs(prev_c - prev_o) / ((h.iloc[i-1] - l.iloc[i-1]) or 1) < 0.3 and bc < bo and bc < (prev2_o + prev2_c) / 2:
                patterns_at_date.append(("Evening Star", "3-candle bearish reversal", "🔴"))
            # Three White Soldiers
            if prev2_c > prev2_o and prev_c > prev_o and bc > bo and bc > prev_c and prev_c > prev2_c:
                patterns_at_date.append(("Three White Soldiers", "Strong bullish reversal", "🟢"))
            # Three Black Crows
            if prev2_c < prev2_o and prev_c < prev_o and bc < bo and bc < prev_c and prev_c < prev2_c:
                patterns_at_date.append(("Three Black Crows", "Strong bearish reversal", "🔴"))

        if patterns_at_date:
            found[date] = patterns_at_date

    # Format output
    result = []
    for date, pats in sorted(found.items(), reverse=True):
        for pname, ptype, emoji in pats:
            result.append(f"{emoji} {date}: {pname} — {ptype}")
    if not result:
        result.append("➡️ No strong candlestick pattern detected — trend continuation likely")
    return result


# ──────────────────────────────────────────────
# HTML DASHBOARD EXPORT
# ──────────────────────────────────────────────

def export_html_dashboard(df, ticker, asset_name, analysis, signals, sr_enhanced, patterns, theme="dark"):
    """Build a standalone HTML dashboard with Plotly chart + signal summary tables.
    Returns HTML string for download."""
    bg_color = "#0e1117" if theme == "dark" else "#ffffff"
    text_color = "#e6edf3" if theme == "dark" else "#1f2328"
    card_bg = "#161b22" if theme == "dark" else "#f6f8fa"

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.2, 0.15],
        subplot_titles=(
            f"{asset_name} ({ticker}) — Price & Indicators",
            "Volume",
            "RSI (14)",
            "MACD"
        )
    )

    # Row 1: Candlestick + MAs + Bollinger
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="Price",
        increasing_line_color="#26a69a", decreasing_line_color="#ef5350"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df["date"], y=df["close"].rolling(20).mean(), name="SMA 20",
                              line=dict(color="orange", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["close"].rolling(50).mean(), name="SMA 50",
                              line=dict(color="blue", width=1)), row=1, col=1)
    if len(df) >= 200:
        fig.add_trace(go.Scatter(x=df["date"], y=df["close"].rolling(200).mean(), name="SMA 200",
                                  line=dict(color="purple", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["close"].ewm(span=20, adjust=False).mean(), name="EMA 20",
                              line=dict(color="cyan", width=1, dash="dash")), row=1, col=1)

    bb_upper, bb_mid, bb_lower = bollinger(df["close"], 20, 2)
    fig.add_trace(go.Scatter(x=df["date"], y=bb_upper, name="BB Upper",
                              line=dict(color="gray", width=1, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=bb_lower, name="BB Lower",
                              line=dict(color="gray", width=1, dash="dot"),
                              fill="tonexty", fillcolor="rgba(128,128,128,0.1)"), row=1, col=1)

    # S/R lines
    ns, nr, sl, rl = sr_enhanced
    if nr:
        fig.add_hline(y=nr[0], line_dash="dash", line_color="red", line_width=1.5,
                      annotation_text=f"Resistance ₹{nr[0]:.1f} ({nr[1]} touches)", annotation_position="top right",
                      row=1, col=1)
    if ns:
        fig.add_hline(y=ns[0], line_dash="dash", line_color="green", line_width=1.5,
                      annotation_text=f"Support ₹{ns[0]:.1f} ({ns[1]} touches)", annotation_position="bottom right",
                      row=1, col=1)

    # Row 2: Volume
    colors = ["#26a69a" if row["close"] >= row["open"] else "#ef5350" for _, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df["date"], y=df["volume"], name="Volume", marker_color=colors), row=2, col=1)
    if "volume" in df.columns:
        fig.add_trace(go.Scatter(x=df["date"], y=df["volume"].rolling(20).mean(), name="Vol MA20",
                                  line=dict(color="black", width=1)), row=2, col=1)

    # Row 3: RSI
    rsi_vals = rsi(df["close"], 14)
    fig.add_trace(go.Scatter(x=df["date"], y=rsi_vals, name="RSI",
                              line=dict(color="#7b1fa2", width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

    # Row 4: MACD
    macd_line, signal_line, hist = macd(df["close"])
    fig.add_trace(go.Bar(x=df["date"], y=hist, name="MACD Hist",
                          marker_color=np.where(hist >= 0, "#26a69a", "#ef5350")), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=macd_line, name="MACD",
                              line=dict(color="blue", width=1)), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=signal_line, name="Signal",
                              line=dict(color="orange", width=1)), row=4, col=1)

    template = "plotly_dark" if theme == "dark" else "plotly_white"
    fig.update_layout(
        height=1000,
        title=f"Technical Analysis Dashboard — {asset_name} ({ticker})",
        xaxis_rangeslider_visible=False,
        template=template,
        dragmode="zoom",
        hovermode="x unified",
        margin=dict(l=10, r=60, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(
        rangebreaks=[dict(bounds=["sat", "mon"])],
        rangeslider_visible=False,
        showspikes=True, spikemode="across", spikesnap="cursor",
        spikecolor="grey", spikethickness=1,
    )
    fig.update_yaxes(
        fixedrange=False,
        showspikes=True, spikemode="across", spikesnap="cursor",
        spikecolor="grey", spikethickness=1,
    )

    # Signal summary HTML table
    latest = df.iloc[-1]
    sig_html = f"""
    <div style="font-family: sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: {bg_color}; color: {text_color};">
    <h1 style="text-align:center;">📊 Technical Analysis Dashboard — {asset_name} ({ticker})</h1>
    <p style="text-align:center; color: gray;">Latest Close: <b>₹{latest['close']:.2f}</b> | Date: {df['date'].iloc[-1]}</p>

    <h2>🔔 Signals Summary</h2>
    <table border="1" cellpadding="10" style="border-collapse:collapse;width:100%;background:{card_bg};color:{text_color};">
    <tr style="background:#2a3441;color:#fff;"><th>Indicator</th><th>Signal</th><th>Value</th></tr>
    """
    for name, sig, val in signals:
        sig_html += f"<tr><td>{name}</td><td>{sig}</td><td>{val}</td></tr>"
    sig_html += "</table>"

    # S/R table
    sig_html += f"""
    <h2>📐 Support &amp; Resistance</h2>
    <table border="1" cellpadding="10" style="border-collapse:collapse;width:100%;background:{card_bg};color:{text_color};">
    <tr style="background:#2a3441;color:#fff;"><th>Level</th><th>Price</th><th>Touches (Strength)</th></tr>
    """
    if nr:
        sig_html += f"<tr><td>🔴 Nearest Resistance</td><td>₹{nr[0]:.2f}</td><td>{nr[1]}</td></tr>"
    if ns:
        sig_html += f"<tr><td>🟢 Nearest Support</td><td>₹{ns[0]:.2f}</td><td>{ns[1]}</td></tr>"
    sig_html += "<tr><td colspan='3' style='font-weight:bold;'>Other Resistance Levels</td></tr>"
    for lvl, touches in (rl[1:] if len(rl) > 1 else []):
        sig_html += f"<tr><td>Resistance</td><td>₹{lvl:.2f}</td><td>{touches}</td></tr>"
    sig_html += "<tr><td colspan='3' style='font-weight:bold;'>Other Support Levels</td></tr>"
    for lvl, touches in (sl[1:] if len(sl) > 1 else []):
        sig_html += f"<tr><td>Support</td><td>₹{lvl:.2f}</td><td>{touches}</td></tr>"
    sig_html += "</table>"

    # Candlestick patterns
    sig_html += """
    <h2>🔍 Detected Candlestick Patterns (recent 6 candles)</h2>
    <table border="1" cellpadding="10" style="border-collapse:collapse;width:100%;background:%s;color:%s;">
    <tr style="background:#2a3441;color:#fff;"><th>Pattern</th></tr>
    """ % (card_bg, text_color)
    if patterns:
        for p in patterns:
            sig_html += f"<tr><td>{p}</td></tr>"
    else:
        sig_html += "<tr><td>No significant pattern detected in the last 6 candles.</td></tr>"
    sig_html += "</table>"

    sig_html += """
    <p style="color:gray;font-size:12px;margin-top:20px;">Note: This is technical analysis for informational purposes only, not investment advice.</p>
    </div>
    """

    chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")
    full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{asset_name} ({ticker}) — Dashboard</title></head>
<body style="background:{bg_color};margin:0;">
{sig_html}
{chart_html}
</body></html>"""
    return full_html



# ──────────────────────────────────────────────
# FORMATTERS
# ──────────────────────────────────────────────

# ──────────────────────────────────────────────
# SIGNAL ENGINE (SMA crossover + RSI + MACD)
# ──────────────────────────────────────────────

def generate_signals(df, rsi_buy=40, rsi_sell=65):
    """Rule-based BUY/SELL/HOLD signals using SMA crossover + RSI + MACD."""
    df = df.copy()
    df["sma_fast"] = df["close"].rolling(20).mean()
    df["sma_slow"] = df["close"].rolling(50).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi_sig"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd_sig"] = ema12 - ema26
    df["macd_sig_signal"] = df["macd_sig"].ewm(span=9, adjust=False).mean()

    df["signal"] = "HOLD"
    buy_cond = (df["sma_fast"] > df["sma_slow"]) & (df["rsi_sig"] < rsi_buy) & (df["macd_sig"] > df["macd_sig_signal"])
    sell_cond = (df["sma_fast"] < df["sma_slow"]) | (df["rsi_sig"] > rsi_sell) | (df["macd_sig"] < df["macd_sig_signal"])
    df.loc[buy_cond, "signal"] = "BUY"
    df.loc[sell_cond & ~buy_cond, "signal"] = "SELL"
    return df

def latest_signal(df):
    """Return the latest signal dict."""
    sig_df = generate_signals(df)
    last = sig_df.iloc[-1]
    return {
        "signal": last["signal"],
        "close": round(float(last["close"]), 2),
        "sma_fast": round(float(last["sma_fast"]), 2) if not pd.isna(last["sma_fast"]) else None,
        "sma_slow": round(float(last["sma_slow"]), 2) if not pd.isna(last["sma_slow"]) else None,
        "rsi": round(float(last["rsi_sig"]), 2) if not pd.isna(last["rsi_sig"]) else None,
        "macd": round(float(last["macd_sig"]), 4) if not pd.isna(last["macd_sig"]) else None,
        "macd_signal": round(float(last["macd_sig_signal"]), 4) if not pd.isna(last["macd_sig_signal"]) else None}

# ──────────────────────────────────────────────
# BACKTESTER
# ──────────────────────────────────────────────

def run_backtest(df, initial_cash=100000.0, qty_per_trade=10):
    """Simulate the signal strategy on historical data."""
    sig_df = generate_signals(df).dropna(subset=["sma_slow"]).reset_index(drop=True)

    cash = initial_cash
    position = 0
    trades = []
    equity_curve = []

    for _, row in sig_df.iterrows():
        price = float(row["close"])
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

    final_price = float(sig_df.iloc[-1]["close"])
    final_equity = cash + position * final_price
    total_return_pct = ((final_equity - initial_cash) / initial_cash) * 100

    equity_series = pd.Series([e["equity"] for e in equity_curve])
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max.replace(0, np.nan) * 100
    max_drawdown_pct = round(float(drawdown.min()), 2) if len(drawdown) else 0

    completed = [t for t in trades if t["action"] == "SELL"]
    wins = 0
    buy_stack = []
    for t in trades:
        if t["action"] == "BUY":
            buy_stack.append(t["price"])
        elif t["action"] == "SELL" and buy_stack:
            avg_buy = sum(buy_stack) / max(len(buy_stack), 1)
            if t["price"] > avg_buy:
                wins += 1
            buy_stack = []

    win_rate = round((wins / len(completed)) * 100, 2) if completed else 0

    return {
        "initial_cash": initial_cash,
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "max_drawdown_pct": max_drawdown_pct,
        "total_trades": len(trades),
        "win_rate_pct": win_rate,
        "trades": trades[-20:],
        "equity_curve": equity_curve}

def equity_curve_chart(equity_curve, theme="dark"):
    """Plotly chart for backtest equity curve."""
    template = "plotly_dark" if theme == "dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)" if theme == "dark" else "rgba(255,255,255,0)"
    dates = [e["date"] for e in equity_curve]
    values = [e["equity"] for e in equity_curve]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=values, name="Equity",
        fill="tozeroy", fillcolor="rgba(42,120,214,0.12)",
        line=dict(color="#2a78d6", width=2),
    ))
    fig.update_layout(template=template, height=280,
                      margin=dict(l=50, r=20, t=20, b=30),
                      yaxis_title="Equity", showlegend=False,
        dragmode="zoom", hovermode="x unified",
                      font=dict(size=11), paper_bgcolor=bg_color, plot_bgcolor=bg_color)
    fig.update_xaxes(showgrid=False, showspikes=True, spikemode="across", spikesnap="cursor", spikecolor="grey", spikethickness=1)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(50,50,50,0.3)" if theme == "dark" else "rgba(200,200,200,0.5)", fixedrange=False, showspikes=True, spikemode="across", spikesnap="cursor", spikecolor="grey", spikethickness=1)
    return fig

# ──────────────────────────────────────────────
# BROKER CONNECTOR (Sandbox mode)
# ──────────────────────────────────────────────

SANDBOX_MODE = True

def place_order_simulated(ticker, side, qty=10):
    """Sandbox order placement - no real orders."""
    if SANDBOX_MODE:
        return {
            "status": "SIMULATED",
            "message": f"[SANDBOX] Would {side} {qty} of {ticker} (MARKET). No real order placed."}
    return {"status": "ERROR", "message": "Live trading not implemented."}

def fmt_vol(n):
    if n is None: return "\u2014"
    if n >= 1e7: return f"{n/1e7:.2f}Cr"
    if n >= 1e5: return f"{n/1e5:.2f}L"
    if n >= 1e3: return f"{n/1e3:.1f}K"
    return str(int(n))

def fmt_num(n):
    if n is None:
        return "—"
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    if np.isnan(n) or np.isinf(n):
        return "—"
    return f"{n:,.2f}"

# ──────────────────────────────────────────────
# TRADINGVIEW EMBED
# ──────────────────────────────────────────────

def render_tradingview(symbol, theme="dark", height=600):
    """Render TradingView advanced chart with native zoom/pan/drawing tools."""
    tv_symbol = symbol if ":" in symbol else f"NSE:{symbol}"
    html = f"""
    <div class="tradingview-widget-container" style="height:{height}px;width:100%;">
      <div class="tradingview-widget-container__widget" style="height:calc({height}px - 0px);width:100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
      {{
        "autosize": true,
        "symbol": "{tv_symbol}",
        "interval": "D",
        "timezone": "Asia/Kolkata",
        "theme": "{theme}",
        "style": "1",
        "locale": "in",
        "toolbar_bg": "#131722",
        "enable_publishing": false,
        "withdateranges": true,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "studies": ["STD;SMA", "STD;RSI", "Volume@tv-basicstudies", "STD;MACD", "STD;Bollinger_Bands"],
        "support_host": "https://www.tradingview.com"
      }}
      </script>
    </div>
    """
    components.html(html, height=height)
def render_tradingview_fullscreen(symbol, theme="dark"):
    """Render TradingView chart in fullscreen overlay."""
    tv_symbol = symbol if ":" in symbol else f"NSE:{symbol}"
    html = f"""
    <div id="tv-fs" style="position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:99999;background:#131722;">
      <div class="tradingview-widget-container" style="height:100vh;width:100vw;">
        <div class="tradingview-widget-container__widget" style="height:100vh;width:100vw;"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
        {{
          "autosize": true,
          "symbol": "{tv_symbol}",
          "interval": "D",
          "timezone": "Asia/Kolkata",
          "theme": "{theme}",
          "style": "1",
          "locale": "in",
          "toolbar_bg": "#131722",
          "enable_publishing": false,
          "withdateranges": true,
          "hide_side_toolbar": false,
          "allow_symbol_change": true,
          "studies": ["STD;SMA", "STD;RSI", "Volume@tv-basicstudies", "STD;MACD", "STD;Bollinger_Bands"],
          "support_host": "https://www.tradingview.com"
        }}
        </script>
      </div>
      <button onclick="var e=document.getElementById('tv-fs');e.parentNode.removeChild(e);document.body.style.overflow='';" style="position:fixed;top:12px;right:12px;z-index:100000;background:#ef4444;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:14px;cursor:pointer;font-weight:600;">✖ Close Fullscreen</button>
    </div>
    <script>document.body.style.overflow='hidden';</script>
    """
    components.html(html, height=1000)

    if st.button("Exit Fullscreen", key="tv_fs_exit", type="secondary"):
        st.session_state["tv_fullscreen"] = False
        st.rerun()

def render_tradingview_ticker(symbol, theme="dark"):
    tv_sym = symbol.replace(".NS", "") if ".NS" in symbol else symbol
    if symbol.startswith("^"):
        tv_sym = "NIFTY" if symbol == "^NSEI" else "NIFTYBANK" if symbol == "^NSEBANK" else symbol
    html = f"""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
      {{
        "symbols": [
          {{"proName": "NSE:{tv_sym}", "title": "{tv_sym}"}},
          {{"proName": "NSE:RELIANCE", "title": "RELIANCE"}},
          {{"proName": "NSE:TCS", "title": "TCS"}},
          {{"proName": "NSE:HDFCBANK", "title": "HDFCBANK"}},
          {{"proName": "NSE:NIFTY", "title": "NIFTY 50"}}
        ],
        "showSymbolLogo": true,
        "isTransparent": true,
        "displayMode": "adaptive",
        "colorTheme": "{theme}",
        "locale": "in"
      }}
      </script>
    </div>
    """
    components.html(html, height=70)
# ──────────────────────────────────────────────
# VOICE NARRATION
# ──────────────────────────────────────────────

def build_narration(asset_name, summary=None):
    parts = [f"Here's the read on {asset_name}."]
    if summary:
        parts.append(summary["quant"])
        parts.append(summary["technical"])
        parts.append(summary["summary"])
    else:
        parts.append("The chart is showing real market data with SMA, RSI, MACD, and Bollinger Bands overlaid.")
        parts.append("Use RSI to judge overbought or oversold conditions. Above 70 signals overbought, below 30 oversold.")
        parts.append("MACD crossing above its signal line is bullish momentum, and crossing below as bearish.")
    parts.append("Remember, none of this is financial advice.")
    return " ".join(parts)

def generate_audio(text):
    try:
        from gtts import gTTS
        audio_fp = io.BytesIO()
        tts = gTTS(text=text, lang="en", slow=False)
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        return audio_fp
    except Exception:
        return None

# ──────────────────────────────────────────────
# PLOTLY CHARTS
# ──────────────────────────────────────────────

def candlestick_chart(df, analysis, show_ma, show_bb, show_trend, theme="dark"):
    template = "plotly_dark" if theme == "dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)" if theme == "dark" else "rgba(255,255,255,0)"
    grid_color = "rgba(50,50,50,0.25)" if theme == "dark" else "rgba(200,200,200,0.4)"

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.46, 0.16, 0.18, 0.20],
        subplot_titles=("Price & Indicators", "Volume", "RSI (14)", "MACD (12, 26, 9)"),
    )

    # ── TradingView-style candlestick ──
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="OHLC",
        increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
        increasing_fillcolor="#26a69a", decreasing_fillcolor="#ef5350",
        line_width=2, whiskerwidth=0.3,
        hoverlabel=dict(bgcolor=bg_color, font=dict(size=12, family="Trebuchet MS, sans-serif"))),
        row=1, col=1)
    fig.update_traces(increasing_line_width=2, decreasing_line_width=2, selector=dict(type="candlestick"))

    # ── Moving Averages ──
    if show_ma:
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["sma20"], name="SMA 20",
                                 line=dict(color="#2962ff", width=1.8)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["sma50"], name="SMA 50",
                                 line=dict(color="#ff9800", width=1.8)), row=1, col=1)
        if analysis.get("last_sma200") is not None:
            fig.add_trace(go.Scatter(x=df["date"], y=analysis["sma200"], name="SMA 200",
                                     line=dict(color="#9c27b0", width=1.8)), row=1, col=1)
        # EMA 20 (exponential — reacts faster than SMA)
        ema20_series = df["close"].ewm(span=20, adjust=False).mean().round(2)
        fig.add_trace(go.Scatter(x=df["date"], y=ema20_series, name="EMA 20",
                                 line=dict(color="#00bcd4", width=1.5, dash="dash")), row=1, col=1)

    # ── Bollinger Bands ──
    if show_bb:
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["bb_upper_series"], name="BB Upper",
                                 line=dict(color="#9575cd", width=1.2, dash="dot"), opacity=0.7), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["bb_lower_series"], name="BB Lower",
                                 line=dict(color="#9575cd", width=1.2, dash="dot"), opacity=0.7, showlegend=False), row=1, col=1)

    # ── Trend Lines ──
    if show_trend and analysis.get("res_trend_vals") is not None:
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["res_trend_vals"], name="Resistance Trend",
                                 line=dict(color="#ef5350", width=2, dash="dash"), opacity=0.9), row=1, col=1)
    if show_trend and analysis.get("sup_trend_vals") is not None:
        fig.add_trace(go.Scatter(x=df["date"], y=analysis["sup_trend_vals"], name="Support Trend",
                                 line=dict(color="#26a69a", width=2, dash="dash"), opacity=0.9), row=1, col=1)

    # ── Support/Resistance zones (TradingView-style shaded bands) ──
    res_val = analysis["resistance"]
    sup_val = analysis["support"]
    band_range = (res_val - sup_val) * 0.02 or res_val * 0.01
    # Shaded resistance zone
    fig.add_hrect(y0=res_val - band_range, y1=res_val + band_range,
                  fillcolor="rgba(239,83,80,0.12)", line_width=0, row=1, col=1)
    # Shaded support zone
    fig.add_hrect(y0=sup_val - band_range, y1=sup_val + band_range,
                  fillcolor="rgba(38,166,154,0.12)", line_width=0, row=1, col=1)
    # BOLD support/resistance lines
    fig.add_hline(y=res_val, line_dash="solid", line_color="#ef5350", line_width=3, opacity=0.85, row=1, col=1,
                  annotation_text=f"\u25cf R: {res_val:.2f}", annotation_position="top right",
                  annotation_font_size=11, annotation_font_color="#ef5350")
    fig.add_hline(y=sup_val, line_dash="solid", line_color="#26a69a", line_width=3, opacity=0.85, row=1, col=1,
                  annotation_text=f"\u25cf S: {sup_val:.2f}", annotation_position="bottom right",
                  annotation_font_size=11, annotation_font_color="#26a69a")

    # ── Fibonacci Retracement Levels (TradingView-style) ──
    period_high = analysis.get("period_high", res_val)
    period_low = analysis.get("period_low", sup_val)
    fib_range = period_high - period_low
    if fib_range > 0:
        fib_levels = {"0%": period_high, "23.6%": period_high - fib_range * 0.236,
                      "38.2%": period_high - fib_range * 0.382, "50%": period_high - fib_range * 0.5,
                      "61.8%": period_high - fib_range * 0.618, "78.6%": period_high - fib_range * 0.786,
                      "100%": period_low}
        fib_colors = ["#ef5350", "#ff9800", "#26a69a", "#9c27b0", "#2962ff", "#ab47bc", "#26a69a"]
        for i, (label, val) in enumerate(fib_levels.items()):
            fig.add_hline(y=val, line_dash="dot", line_color=fib_colors[i % len(fib_colors)],
                          line_width=1, opacity=0.35, row=1, col=1,
                          annotation_text=f"Fib {label}: {val:.2f}", annotation_position="top left",
                          annotation_font_size=8, annotation_font_color=fib_colors[i % len(fib_colors)])

    # ── Volume Profile (horizontal histogram on right side) ──
    if "volume" in df.columns and len(df) > 20:
        close_vals = df["close"].values
        vol_vals = df["volume"].values
        n_bins = min(30, max(10, len(df) // 5))
        price_min, price_max = float(np.min(close_vals)), float(np.max(close_vals))
        bin_edges = np.linspace(price_min, price_max, n_bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        vol_profile = np.zeros(n_bins)
        for j in range(len(close_vals)):
            idx = min(int((close_vals[j] - price_min) / (price_max - price_min) * n_bins), n_bins - 1)
            if idx >= 0:
                vol_profile[idx] += vol_vals[j]
        max_vp = vol_profile.max() if vol_profile.max() > 0 else 1
        # Scale volume profile bars to fit within ~15% of price chart width
        x_max = df["date"].iloc[-1]
        x_range_ms = (df["date"].iloc[-1] - df["date"].iloc[0]).total_seconds() * 1000
        bar_width_ms = x_range_ms * 0.12  # 12% of chart width
        for j in range(n_bins):
            if vol_profile[j] > 0:
                fig.add_shape(type="rect",
                    xref="x", yref="y",
                    x0=df["date"].iloc[-1], x1=df["date"].iloc[-1] + pd.Timedelta(milliseconds=int(bar_width_ms * vol_profile[j] / max_vp)),
                    y0=bin_edges[j], y1=bin_edges[j+1],
                    fillcolor="rgba(100,181,246,0.25)", line_width=0, row=1, col=1)

    # ── Volume bars ──
    if "volume" in df.columns:
        colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(df["close"], df["open"])]
        fig.add_trace(go.Bar(x=df["date"], y=df["volume"], name="Volume",
                             marker_color=colors, opacity=0.6), row=2, col=1)
        if analysis.get("avg_vol"):
            fig.add_hline(y=analysis["avg_vol"], line_dash="dash", line_color="#7c7b76",
                          opacity=0.5, row=2, col=1)

    # ── RSI ──
    fig.add_trace(go.Scatter(x=df["date"], y=analysis["rsi_vals"], name="RSI",
                             line=dict(color="#ab47bc", width=1.8)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#ef5350", line_width=1, opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#26a69a", line_width=1, opacity=0.5, row=3, col=1)
    fig.add_hline(y=50, line_dash="dash", line_color="#78909c", line_width=1, opacity=0.3, row=3, col=1)

    # ── MACD ──
    hist_colors = ["#26a69a" if h >= 0 else "#ef5350" for h in analysis["hist"]]
    fig.add_trace(go.Bar(x=df["date"], y=analysis["hist"], name="MACD Hist",
                         marker_color=hist_colors, opacity=0.6), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=analysis["macd_line"], name="MACD",
                             line=dict(color="#2962ff", width=1.6)), row=4, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=analysis["signal_line"], name="Signal",
                             line=dict(color="#ff9800", width=1.6)), row=4, col=1)

    fig.update_layout(
        template=template,
        height=820,
        margin=dict(l=50, r=60, t=40, b=30),
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(size=11, family="Trebuchet MS, sans-serif"),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        hovermode="x unified",
        dragmode="zoom",
        # TradingView-style crosshair
        xaxis=dict(showspikes=True, spikethickness=1, spikedash="solid", spikemode="across",
                   spikecolor="rgba(150,150,150,0.5)", spikesnap="cursor", showline=True, linecolor=grid_color),
        yaxis=dict(showspikes=True, spikethickness=1, spikedash="solid", spikemode="across",
                   spikecolor="rgba(150,150,150,0.5)", spikesnap="cursor", showline=True, linecolor=grid_color, side="right"),
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor=grid_color, mirror=True,
                     rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=grid_color, side="right",
                     showline=True, linecolor=grid_color, mirror=True, fixedrange=False)
    fig.update_yaxes(tickformat=".2f", row=1, col=1)
    # Weekend gaps (TradingView style)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig


def trend_chart(df, theme="dark"):
    template = "plotly_dark" if theme == "dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)" if theme == "dark" else "rgba(255,255,255,0)"

    first = df["close"].iloc[0]
    pct = ((df["close"] - first) / first * 100).round(2)
    last_val = pct.iloc[-1]
    color = "#1d9e75" if last_val >= 0 else "#e0524f"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=pct, name="Cumulative %",
        fill="tozeroy", fillcolor=f"rgba({29 if last_val>=0 else 224},{158 if last_val>=0 else 82},{117 if last_val>=0 else 79},0.14)",
        line=dict(color=color, width=2.2),
    ))
    fig.add_trace(go.Scatter(
        x=[df["date"].iloc[-1]], y=[last_val], mode="markers",
        marker=dict(size=8, color=color, line=dict(color="#111", width=2)),
        showlegend=False,
    ))
    fig.update_layout(template=template, height=240,
                      margin=dict(l=50, r=20, t=20, b=30),
                      yaxis_title="Cumulative %", showlegend=False,
        dragmode="pan",
                      font=dict(size=11), paper_bgcolor=bg_color, plot_bgcolor=bg_color)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(50,50,50,0.3)" if theme == "dark" else "rgba(200,200,200,0.5)")
    return fig

# ──────────────────────────────────────────────
# SIDEBAR (shared)
# ──────────────────────────────────────────────

theme = st.session_state.theme

st.sidebar.markdown("## \u2699\ufe0f Settings")

theme_col1, theme_col2 = st.sidebar.columns([1, 1])
if theme_col1.button("\U0001f319 Dark", use_container_width=True,
                     type="primary" if st.session_state.theme == "dark" else "secondary"):
    st.session_state.theme = "dark"
    st.rerun()
if theme_col2.button("\u2600\ufe0f Light", use_container_width=True,
                     type="primary" if st.session_state.theme == "light" else "secondary"):
    st.session_state.theme = "light"
    st.rerun()

st.sidebar.markdown("---")

# ── Broker Connection Panel ──
st.sidebar.markdown("### 🔗 Broker Connection")

# Quick connect to Groww (prominent banner when not connected)
if not st.session_state.connection:
    st.sidebar.markdown("""
    <div style='padding:10px 14px;border-radius:10px;background:linear-gradient(135deg,#00d09c22,#00b37f22);
    border:1.5px solid #00d09c66;margin-bottom:10px;'>
        <div style='display:flex;align-items:center;gap:8px;'>
            <span style='font-size:20px;'>🌱</span>
            <span style='font-size:14px;font-weight:700;color:#00d09c;'>Groww Quick Connect</span>
        </div>
        <div style='font-size:11px;opacity:0.6;margin-top:4px;'>Select Groww below to connect instantly</div>
    </div>
    """, unsafe_allow_html=True)

if st.session_state.connection:
    conn = st.session_state.connection
    broker_info = next((b for b in BROKERS if b["id"] == conn.get("broker_id")), {})
    broker_color = broker_info.get("color", "#00d09c")
    broker_logo = broker_info.get("logo", "🔗")
    mode_label = "🟢 Live" if conn.get("mode") == "live" else "🟡 Demo"
    st.sidebar.markdown(f"""
    <div style='padding:10px 14px; border-radius:8px; background:{broker_color}22;
    border:1px solid {broker_color}66;'>
        <div style='font-weight:700;font-size:13px;'>{broker_logo} {conn["name"]} {mode_label}</div>
        <div style='font-size:11px;opacity:0.7;margin-top:2px;'>Connected {conn["connected_at"]}</div>
    </div>
    """, unsafe_allow_html=True)
    if st.sidebar.button("🔌 Disconnect", use_container_width=True):
        st.session_state.connection = None
        st.session_state.credentials = {}
        st.rerun()
else:
    selected_broker_id = st.sidebar.selectbox(
        "Select Broker",
        options=[b["id"] for b in BROKERS],
        format_func=lambda x: next(b["name"] for b in BROKERS if b["id"] == x),
        key="broker_select"
    )
    broker_meta = next(b for b in BROKERS if b["id"] == selected_broker_id)
    broker_color = broker_meta.get("color", "#888")
    broker_logo = broker_meta.get("logo", "🔗")

    # Branded broker info card
    st.sidebar.markdown(f"""
    <div style='padding:6px 10px;border-radius:6px;background:{broker_color}11;border:1px solid {broker_color}44;margin:4px 0;'>
        <span style='font-size:14px;'>{broker_logo}</span>
        <span style='font-size:11px;color:{broker_color};margin-left:6px;font-weight:600;'>{broker_meta['note']}</span>
    </div>
    """, unsafe_allow_html=True)

    # Groww-specific hint
    if selected_broker_id == "groww":
        st.sidebar.markdown("""
        <div style='padding:8px;border-radius:8px;background:#00d09c11;border:1px dashed #00d09c44;margin:6px 0 10px 0;text-align:center;'>
            <div style='font-size:11px;color:#00d09c;'>🌱 Enter your Groww API credentials below</div>
            <div style='font-size:10px;opacity:0.5;margin-top:2px;'>Get API keys from Groww Dashboard → Settings → API</div>
        </div>
        """, unsafe_allow_html=True)

    credentials = {}
    for field in broker_meta["fields"]:
        is_secret = "secret" in field.lower() or "pin" in field.lower() or "key" in field.lower() or "totp" in field.lower()
        credentials[field] = st.sidebar.text_input(
            field, type="password" if is_secret else "default",
            key=f"cred_{selected_broker_id}_{field}"
        )

    btn_label = f"Connect to {broker_meta['name']}"
    if st.sidebar.button(btn_label, use_container_width=True, type="primary"):
        empty_fields = [f for f in broker_meta["fields"] if not credentials.get(f)]
        if empty_fields:
            st.sidebar.error(f"⚠️ Please fill: {', '.join(empty_fields)}")
        else:
            st.session_state.connection = {
                "broker_id": selected_broker_id,
                "name": broker_meta["name"],
                "connected_at": time.strftime("%H:%M:%S"),
                "mode": "demo"}
            st.session_state.credentials = credentials
            st.sidebar.success(f"✅ Connected to {broker_meta['name']} (Demo)")
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("QUANT DESK // REAL DATA VIA YFINANCE // NOT FINANCIAL ADVICE")

# ──────────────────────────────────────────────

if st.session_state.selected_asset is None:
    st.markdown('<h1 class="sci-fi-title">📊 Quant Desk</h1>', unsafe_allow_html=True)
    st.markdown("### WATCHLIST // SELECT ASSET TO INITIALIZE")
    st.markdown("")

    search_query = st.text_input("SEARCH", placeholder="ENTER TICKER OR NAME...", key="watchlist_search")
    filtered = [a for a in ASSETS if
        search_query.lower() in a["ticker"].lower() or
        search_query.lower() in a["name"].lower() or
        search_query.lower() in a.get("tv", "").lower()]

    if not filtered:
        st.warning("No matches found")
    else:
        cols = st.columns(4)
        for i, asset in enumerate(filtered):
            with cols[i % 4]:
                logo_url = f"https://s3-symbol-logo.tradingview.com/{asset.get('logo', asset['ticker']).lower()}.svg"
                st.markdown(
                    f'<img src="{logo_url}" width="28" height="28" '
                    f'style="border-radius:0;object-fit:contain;background:rgba(0,240,255,0.05);padding:2px;" '
                    f'onerror="this.style.display=\'none\'">',
                    unsafe_allow_html=True
                )
                card_key = f"asset_card_{i}"
                if st.button(
                    f"**{asset['ticker']}**\n{asset['name']}\n{asset['type']}",
                    key=card_key,
                    use_container_width=True,
                ):
                    st.session_state.selected_asset = asset
                    st.session_state.show_analysis = False
                    st.session_state.analysis_result = None
                    st.session_state.voice_generated = None
                    st.session_state.backtest_result = None
                    st.session_state.order_message = None
                    st.rerun()

    st.markdown("---")
    st.caption("DATA SOURCE: YFINANCE (REAL MARKET DATA) // EDUCATIONAL USE ONLY // NOT FINANCIAL ADVICE")

# ──────────────────────────────────────────────
# DASHBOARD SCREEN
# ──────────────────────────────────────────────

else:
    asset = st.session_state.selected_asset
    ticker = asset["ticker"]

    # Back button in sidebar
    if st.sidebar.button("\u2190 Back to Watchlist", use_container_width=True):
        st.session_state.selected_asset = None
        st.session_state.show_analysis = False
        st.session_state.analysis_result = None
        st.session_state.voice_generated = None
        st.session_state.backtest_result = None
        st.session_state.order_message = None
        st.rerun()

    # ── Period / Interval selectors (standalone dashboard style) ──
    per_col1, per_col2 = st.sidebar.columns(2)
    with per_col1:
        period_opts = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]
        st.session_state.period = st.selectbox("Period", period_opts,
                                                index=period_opts.index(st.session_state.get("period", "5y")),
                                                key="period_selector",
                                                help="1mo=1 month, 5y=5 years, max=all available data")
    with per_col2:
        interval_opts = ["1d", "1wk", "1mo"]
        interval_labels = {"1d": "Daily", "1wk": "Weekly", "1mo": "Monthly"}
        st.session_state.interval = st.selectbox("Interval", interval_opts,
                                                   format_func=lambda x: interval_labels.get(x, x),
                                                   index=interval_opts.index(st.session_state.get("interval", "1d")),
                                                   key="interval_selector",
                                                   help="Candle interval: daily, weekly, or monthly")

    # ── Fetch data ──
    with st.spinner(f"Fetching real data for {ticker}..."):
        df = fetch_ohlc(ticker, st.session_state.period, st.session_state.interval)

    if df is None or len(df) < 5:
        with st.expander("\u26a0\ufe0f Error Details (click to expand)"):
            st.error(f"Could not fetch data for {ticker}. Please try a different period or asset.")
        if st.button("\u2190 Back to Watchlist"):
            st.session_state.selected_asset = None
            st.rerun()
        st.stop()
    if df.attrs.get("synthetic"):
        st.info(f"\u26a0\ufe0f Yahoo Finance is rate-limiting right now \u2014 showing deterministic "
                f"simulated candles for {ticker} so the app keeps working. Real data resumes "
                "automatically once the limit clears.")

    analysis = build_analysis(df)
    last_price = float(df["close"].iloc[-1])

    # ── Enhanced S/R with touch counts ──
    sr_enhanced = find_support_resistance_enhanced(df)
    # ── Individual indicator status signals ──
    indicator_signals = generate_indicator_signals(df)
    # ── Enhanced candlestick pattern detection (6 candles) ──
    enhanced_patterns = detect_patterns_enhanced(df)

    # -- Compute signal --
    sig = latest_signal(df)
    sig_colors = {"BUY": "#0ca30c", "SELL": "#d03b3b", "HOLD": "#898781"}
    sig_color = sig_colors.get(sig["signal"], "#898781")

    # -- Header --
    col_title, col_signal, col_badge, col_price = st.columns([3, 1, 1, 1])
    with col_title:
        st.markdown(f'<h2 class="sci-fi-title">📊 {ticker} — {asset["name"]}</h2>', unsafe_allow_html=True)
        st.caption(f"{asset['type']} \u00b7 Data via yfinance \u00b7 {st.session_state.period} / {st.session_state.interval}")
    with col_signal:
        st.markdown(f"""
        <div style='text-align:center;padding:8px 16px;border-radius:0;clip-path:polygon(8px 0,100% 0,100% calc(100% - 8px),calc(100% - 8px) 100%,0 100%,0 8px);background:{sig_color}22;color:{sig_color};font-size:1.1rem;font-weight:700;font-family:Orbitron,monospace;letter-spacing:2px;text-transform:uppercase;text-shadow:0 0 10px {sig_color}80;'>
            {sig['signal']}
        </div>
        """, unsafe_allow_html=True)
    with col_badge:
        if st.session_state.connection:
            st.markdown(f"\U0001f7e1 {st.session_state.connection['name']} \u00b7 Demo")
        else:
            st.markdown("\u26aa No broker connected")
    with col_price:
        st.metric("Last Price", f"\u20b9{last_price:,.2f}" if ticker.endswith(".NS") or ticker.startswith("^") else f"${last_price:,.2f}",
                  f"{analysis['day_change_pct']:+.2f}% today")

    # ── Ticker tape ──
    render_tradingview_ticker(ticker, theme)

    st.markdown("")

    # ── AI Analysis + Voice buttons (side by side, above chart) ──
    # -- Signal metrics row --
    sig_col1, sig_col2, sig_col3, sig_col4 = st.columns(4)
    with sig_col1:
        st.metric("Signal: " + sig["signal"], f"\u20b9{sig['close']:,.2f}")
    with sig_col2:
        st.metric("SMA 20", f"{sig['sma_fast']:.2f}" if sig['sma_fast'] else "\u2014")
    with sig_col3:
        st.metric("SMA 50", f"{sig['sma_slow']:.2f}" if sig['sma_slow'] else "\u2014")
    with sig_col4:
        st.metric("RSI (14)", f"{sig['rsi']:.1f}" if sig['rsi'] else "\u2014")

    st.markdown("")

    # -- AI Analysis + Voice + Backtest + Order buttons --
    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns([1, 1, 1, 1, 1])

    with btn_col1:
        if st.button("\u2728 AI Analysis", type="primary", use_container_width=True):
            st.session_state.show_analysis = True
            st.session_state.analysis_result = compute_ai_summary(df)
            st.session_state.voice_generated = None

    with btn_col2:
        if st.button("\U0001f50a Voice Brief", use_container_width=True):
            narration = build_narration(asset["name"],
                st.session_state.analysis_result if st.session_state.show_analysis else None)
            with st.spinner("Generating audio..."):
                audio_bytes = generate_audio(narration)
                if audio_bytes:
                    st.session_state.voice_generated = audio_bytes
                else:
                    st.error("\u274c Failed to generate audio. gTTS might not be available.")

    with btn_col3:
        if st.button("\U0001f504 Run Backtest", use_container_width=True):
            with st.spinner("Running backtest simulation..."):
                bt_df = fetch_ohlc(ticker, "1y", "1d")
                if bt_df is not None and bt_df.attrs.get("synthetic"):
                    st.caption("\u26a0\ufe0f Using simulated data for the backtest (live feed rate-limited).")
                if bt_df is not None and len(bt_df) > 50:
                    st.session_state.backtest_result = run_backtest(bt_df)
                else:
                    st.error("\u274c Not enough data for backtest.")

    with btn_col4:
        if st.button("\U0001f7e2 Sim BUY", use_container_width=True):
            result = place_order_simulated(ticker, "BUY", 10)
            st.session_state.order_message = result["message"]

    with btn_col5:
        if st.button("\U0001f7e3 Sim SELL", use_container_width=True):
            result = place_order_simulated(ticker, "SELL", 10)
            st.session_state.order_message = result["message"]

    # ── Analysis summary box (shown when AI Analysis clicked) ──
    if st.session_state.show_analysis and st.session_state.analysis_result:
        result = st.session_state.analysis_result
        st.markdown("#### \U0001f9ee Quant Analysis")
        st.info(result["quant"])
        st.markdown("#### \U0001f4ca Technical Analysis")
        st.info(result["technical"])
        st.markdown("#### \U0001f4cb Overall Summary")
        st.success(result["summary"])

    # ── Voice audio player ──
    if st.session_state.voice_generated:
        st.audio(st.session_state.voice_generated, format="audio/mp3")

    # -- Order message (sandbox) --
    if st.session_state.order_message:
        st.info(f"\U0001f7e0 {st.session_state.order_message}")

    # -- Backtest results --
    if st.session_state.backtest_result:
        bt = st.session_state.backtest_result
        st.markdown("#### \U0001f4c8 Backtest Results (1 year, sandbox simulation)")

        bt_col1, bt_col2, bt_col3, bt_col4 = st.columns(4)
        with bt_col1:
            st.metric("Final Equity", f"\u20b9{bt['final_equity']:,.2f}")
        with bt_col2:
            st.metric("Total Return", f"{bt['total_return_pct']:+.2f}%")
        with bt_col3:
            st.metric("Max Drawdown", f"{bt['max_drawdown_pct']:.2f}%")
        with bt_col4:
            st.metric("Win Rate", f"{bt['win_rate_pct']:.1f}%")

        st.caption(f"{bt['total_trades']} total trades simulated. Initial cash: \u20b9{bt['initial_cash']:,.0f}. Historical simulation, not a guarantee of future results.")

        st.plotly_chart(equity_curve_chart(bt["equity_curve"], theme), use_container_width=True, config=TV_CHART_CONFIG)

        if bt["trades"]:
            st.markdown("##### Last 20 Trades")
            trades_df = pd.DataFrame(bt["trades"])
            st.dataframe(trades_df, use_container_width=True, hide_index=True)


    # ── Verdict banner ──
    verdict_bg = "#1a4d2e" if "Bullish" in analysis["verdict"] else "#4d1a1a" if "Bearish" in analysis["verdict"] else "#333"
    st.markdown(f"""
    <div style='padding:12px 18px;border-radius:10px;background:{verdict_bg};color:#fff;text-align:center;font-size:1.1rem;font-weight:600;margin:8px 0;'>
        {analysis['verdict']} &nbsp;|&nbsp; Bullish: {analysis['bull_signals']} &nbsp;\u00b7&nbsp; Bearish: {analysis['bear_signals']}
    </div>
    """, unsafe_allow_html=True)
    # ── Main chart - Plotly candlestick (scroll to zoom like photo) ──
    st.plotly_chart(
        candlestick_chart(df, analysis, True, True, True, theme),
        use_container_width=True,
        config=TV_CHART_CONFIG,
    )

    # ── Clear trading signal box (TradingView-style) ──
    sig = latest_signal(df)
    sig_colors = {"BUY": "#0ca30c", "SELL": "#d03b3b", "HOLD": "#898781"}
    sig_color = sig_colors.get(sig["signal"], "#898781")
    rsi_val = analysis.get("last_rsi", 50)
    rsi_text = "Oversold (<30)" if rsi_val < 30 else "Overbought (>70)" if rsi_val > 70 else "Neutral"
    st.markdown(f"""
    <div style="padding:16px 20px;border-radius:0;clip-path:polygon(10px 0,100% 0,100% calc(100% - 10px),calc(100% - 10px) 100%,0 100%,0 10px);background:rgba(5,7,13,0.6);border:1px solid {sig_color};color:{sig_color};font-size:0.95rem;font-weight:600;margin:8px 0;font-family:'Share Tech Mono',monospace;letter-spacing:1px;text-shadow:0 0 8px {sig_color}40;">
        > SIGNAL: {sig["signal"]} &nbsp;|&nbsp; PRICE: {sig["close"]:,.2f} &nbsp;|&nbsp; RSI: {rsi_val:.1f} ({rsi_text}) &nbsp;|&nbsp; SMA20: {sig["sma_fast"] or "--"} &nbsp;|&nbsp; SMA50: {sig["sma_slow"] or "--"} &nbsp;|&nbsp; MACD: {fmt_num(sig.get("macd"))} &nbsp;|&nbsp; EMA20: {fmt_num(round(float(df["close"].ewm(span=20, adjust=False).mean().iloc[-1]), 2))}
    </div>
    """, unsafe_allow_html=True)
    # ── Top metrics row ──
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    with col_m1:
        st.metric("Period Change", f"{analysis['change_pct']:+.2f}%", f"over {len(df)} candles")
    with col_m2:
        rsi_val = analysis["last_rsi"]
        st.metric("RSI (14)", f"{rsi_val:.1f}" if rsi_val is not None else "\u2014")
    with col_m3:
        st.metric("Volume", fmt_vol(df["volume"].iloc[-1]) if "volume" in df.columns else "\u2014",
                  f"{analysis['vol_ratio']:.2f}\u00d7 avg" if "volume" in df.columns else "")
    with col_m4:
        st.metric("Volatility (ann.)", f"{analysis['annualized_vol']}%")
    with col_m5:
        st.metric("Sharpe Ratio", f"{analysis['sharpe']}")

    # Golden/Death Cross alert
    if analysis.get("golden_cross"):
        st.success("❤️ GOLDEN CROSS detected! SMA50 crossed above SMA200 — strong bullish signal.")
    elif analysis.get("death_cross"):
        st.error("⚰️ DEATH CROSS detected! SMA50 crossed below SMA200 — strong bearish signal.")
    # Skewness/Kurtosis info
    sk = analysis.get("skewness", 0)
    ku = analysis.get("kurtosis", 0)
    so = analysis.get("sortino", 0)
    sk_msg = "right-skewed (more big gains)" if sk > 0.5 else "left-skewed (more big losses)" if sk < -0.5 else "symmetric"
    ku_msg = "fat tails (extreme moves likely)" if ku > 3 else "thin tails" if ku < 0 else "normal distribution"
    st.info(f"Sortino: {so} | Skewness: {sk} ({sk_msg}) | Kurtosis: {ku} ({ku_msg})")

    # ── Two-column: Indicators + Patterns ──
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### \U0001f4cb Technical Indicators")
        ind_data = {
            "Indicator": ["SMA 20", "EMA 20", "SMA 50", "RSI (14)", "MACD Line", "MACD Signal",
                          "MACD Histogram", "BB Upper", "BB Lower",
                          "Support (20d low)", "Resistance (20d high)",
                          "Resistance Trend Slope", "Support Trend Slope",
                          "Golden Cross", "Death Cross",
                          "SMA 200", "Avg Volume (20d)", "Volume Ratio",
                          "Annualized Volatility", "Sharpe Ratio",
                          "Sortino Ratio", "Skewness", "Kurtosis"],
            "Value": [
                fmt_num(analysis["last_sma20"]),
                fmt_num(round(float(df["close"].ewm(span=20, adjust=False).mean().iloc[-1]), 2)),
                fmt_num(analysis["last_sma50"]),
                f"{analysis['last_rsi']:.2f}" if analysis["last_rsi"] is not None else "—",
                fmt_num(analysis["last_macd"]),
                fmt_num(analysis["last_signal"]),
                fmt_num(analysis["last_hist"]),
                fmt_num(analysis["bb_upper"]),
                fmt_num(analysis["bb_lower"]),
                f"₹{analysis['support']}",
                f"₹{analysis['resistance']}",
                f"{analysis['res_trend']['slope']:+.4f}" if analysis.get('res_trend') else "—",
                f"{analysis['sup_trend']['slope']:+.4f}" if analysis.get('sup_trend') else "—",
                "Yes ❤️" if analysis.get("golden_cross") else "No",
                "Yes ⚰️" if analysis.get("death_cross") else "No",
                fmt_num(analysis.get("last_sma200")) if analysis.get("last_sma200") else "—",
                fmt_vol(analysis["avg_vol"]),
                f"{analysis['vol_ratio']}×",
                f"{analysis['annualized_vol']}%",
                f"{analysis['sharpe']}",
                f"{analysis.get('sortino', 0)}",
                f"{analysis.get('skewness', 0)}",
                f"{analysis.get('kurtosis', 0)}",
            ]}
        st.dataframe(pd.DataFrame(ind_data), use_container_width=True, hide_index=True)

        # Raw data table
        st.markdown("---")
        st.markdown("#### \U0001f4cb Recent Candle Data")
        display_df = df[["date", "open", "high", "low", "close"]].copy()
        if "volume" in df.columns:
            display_df["volume"] = df["volume"].apply(fmt_vol)
        display_df.columns = ["Date", "Open", "High", "Low", "Close"] + (["Volume"] if "volume" in df.columns else [])
        display_df["Date"] = pd.to_datetime(display_df["Date"]).dt.strftime("%Y-%m-%d")
        st.dataframe(display_df.tail(30), use_container_width=True, hide_index=True)

    with col_right:
        st.markdown("#### \U0001f50d Candlestick Patterns (6-candle scan)")
        for p in enhanced_patterns:
            st.markdown(f"- {p}")

        st.markdown("#### \U0001f527 Indicator Status (Individual Verdicts)")
        ind_sig_df = pd.DataFrame(indicator_signals, columns=["Indicator", "Signal", "Value"])
        st.dataframe(ind_sig_df, use_container_width=True, hide_index=True)

        st.markdown("#### \U0001f4d0 Support/Resistance (Swing-based with Touch Counts)")
        ns, nr, sl_list, rl_list = sr_enhanced
        sr_rows = []
        if nr:
            sr_rows.append({"Level": "\U0001f534 Nearest Resistance", "Price": f"\u20b9{nr[0]:.2f}", "Touches": nr[1]})
        if ns:
            sr_rows.append({"Level": "\U0001f7e2 Nearest Support", "Price": f"\u20b9{ns[0]:.2f}", "Touches": ns[1]})
        for lvl, touches in (rl_list[1:] if len(rl_list) > 1 else []):
            sr_rows.append({"Level": "\U0001f534 Resistance", "Price": f"\u20b9{lvl:.2f}", "Touches": touches})
        for lvl, touches in (sl_list[1:] if len(sl_list) > 1 else []):
            sr_rows.append({"Level": "\U0001f7e2 Support", "Price": f"\u20b9{lvl:.2f}", "Touches": touches})
        if sr_rows:
            st.dataframe(pd.DataFrame(sr_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Not enough swing points for clustered S/R levels.")

        st.markdown("#### \U0001f4d0 Pivot Points & Trend Lines")
        pv = analysis.get("pivots", {"highs": [], "lows": []})
        st.markdown(f"**Pivot Highs:** {len(pv['highs'])} \u00b7 **Pivot Lows:** {len(pv['lows'])}")
        if analysis.get("res_trend"):
            st.markdown(f"- \U0001f534 Resistance trend slope: `{analysis['res_trend']['slope']:+.4f}`")
        if analysis.get("sup_trend"):
            st.markdown(f"- \U0001f7e2 Support trend slope: `{analysis['sup_trend']['slope']:+.4f}`")
        if not analysis.get("res_trend") and not analysis.get("sup_trend"):
            st.markdown("- Not enough pivot points for trend lines")

        st.markdown("#### \U0001f4ca Signal Summary (Bull/Bear Count)")
        sig_df = pd.DataFrame({
            "Type": ["\U0001f7e2 Bullish", "\U0001f534 Bearish", "\u2696\ufe0f Net"],
            "Count": [analysis["bull_signals"], analysis["bear_signals"],
                      analysis["bull_signals"] - analysis["bear_signals"]]})
        st.dataframe(sig_df, use_container_width=True, hide_index=True)


    # ── HTML Dashboard Export ──
    st.markdown("---")
    exp_col1, exp_col2 = st.columns([3, 1])
    with exp_col2:
        if st.button("💾 Download HTML Dashboard", key="html_export", use_container_width=True, type="primary"):
            html_content = export_html_dashboard(df, ticker, asset["name"], analysis,
                                                  indicator_signals, sr_enhanced,
                                                  enhanced_patterns, theme)
            st.download_button(
                label="⬇️ Save HTML File",
                data=html_content,
                file_name=f"{ticker.replace('.', '_')}_dashboard.html",
                mime="text/html",
                use_container_width=True,
            )
    with exp_col1:
        st.caption("Export a standalone interactive HTML dashboard with chart, signals, S/R levels & patterns.")

    # ── TradingView chart with fullscreen (collapsible) ──
    st.markdown("")
    with st.expander("TradingView Live Chart (native zoom + fullscreen)"):
        fs_col1, fs_col2 = st.columns([4, 1])
        with fs_col2:
            if st.button("\U0001f5fa\ufe0f Open Fullscreen", key="tv_fs", use_container_width=True):
                st.session_state["tv_fullscreen"] = not st.session_state.get("tv_fullscreen", False)
        if st.session_state.get("tv_fullscreen", False):
            render_tradingview_fullscreen(asset.get("tv", ticker), theme)
        else:
            render_tradingview(asset.get("tv", ticker), theme, height=600)
# ── Footer ──
st.markdown("---")
footer_col1, footer_col2 = st.columns([3, 1])
with footer_col1:
    st.caption("QUANT DESK // SIGNAL ENGINE + BACKTESTER + BROKER SANDBOX // NOT FINANCIAL ADVICE")
with footer_col2:
    st.caption("Powered by [TradingView](https://www.tradingview.com)")

