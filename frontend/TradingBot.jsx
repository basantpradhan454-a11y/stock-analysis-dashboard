/*
Trading Bot Dashboard — React frontend
Install: npm install react react-dom lightweight-charts
Backend: http://localhost:8000 (see backend/main.py)
*/

import React, { useEffect, useRef, useState, useCallback } from "react";
import { createChart, CandlestickSeries } from "lightweight-charts";

const API_BASE = "http://localhost:8000";

const SIGNAL_COLORS = { BUY: "#0ca30c", SELL: "#d03b3b", HOLD: "#898781" };

export default function App() {
  const [assets, setAssets] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/assets`).then((r) => r.json()).then(setAssets).catch(() => setAssets([]));
  }, []);

  if (selected) return <Dashboard asset={selected} onBack={() => setSelected(null)} />;

  return (
    <div style={s.page}>
      <h1 style={s.h1}>Trading bot — watchlist</h1>
      <p style={s.sub}>Ek asset chuniye signal, chart aur backtest dekhne ke liye</p>
      <div style={s.grid}>
        {assets.map((a) => (
          <button key={a.ticker} style={s.card} onClick={() => setSelected(a)}>
            <span style={s.ticker}>{a.ticker}</span>
            <span style={s.name}>{a.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Dashboard({ asset, onBack }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  const [signal, setSignal] = useState(null);
  const [backtest, setBacktest] = useState(null);
  const [loadingBt, setLoadingBt] = useState(false);
  const [orderMsg, setOrderMsg] = useState(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: "transparent" }, textColor: "#898781" },
      grid: { vertLines: { color: "rgba(140,140,140,0.08)" }, horzLines: { color: "rgba(140,140,140,0.08)" } },
      width: containerRef.current.clientWidth,
      height: 360,
    });
    seriesRef.current = chart.addSeries(CandlestickSeries, {
      upColor: "#0ca30c",
      downColor: "#d03b3b",
      borderVisible: false,
      wickUpColor: "#0ca30c",
      wickDownColor: "#d03b3b",
    });
    chartRef.current = chart;
    const onResize = () => chart.applyOptions({ width: containerRef.current.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, []);

  const loadAll = useCallback(() => {
    fetch(`${API_BASE}/api/ohlc/${asset.ticker}?period=6mo&interval=1d`)
      .then((r) => r.json())
      .then((d) => {
        seriesRef.current.setData(d.candles);
        chartRef.current.timeScale().fitContent();
      });
    fetch(`${API_BASE}/api/signal/${asset.ticker}`).then((r) => r.json()).then(setSignal);
  }, [asset.ticker]);

  useEffect(() => loadAll(), [loadAll]);

  const runBacktest = () => {
    setLoadingBt(true);
    fetch(`${API_BASE}/api/backtest/${asset.ticker}?period=1y&interval=1d`)
      .then((r) => r.json())
      .then(setBacktest)
      .finally(() => setLoadingBt(false));
  };

  const sendOrder = (side) => {
    fetch(`${API_BASE}/api/order/${asset.ticker}?side=${side}&qty=10`, { method: "POST" })
      .then((r) => r.json())
      .then((d) => setOrderMsg(d.message));
  };

  return (
    <div style={s.page}>
      <button style={s.backBtn} onClick={onBack}>← Watchlist</button>

      <div style={s.headerRow}>
        <div>
          <p style={s.ticker}>{asset.ticker}</p>
          <p style={s.name}>{asset.name}</p>
        </div>
        {signal && (
          <span style={{ ...s.badge, background: SIGNAL_COLORS[signal.signal] + "22", color: SIGNAL_COLORS[signal.signal] }}>
            {signal.signal}
          </span>
        )}
      </div>

      {signal && (
        <div style={s.metricsRow}>
          <Metric label="Close" value={signal.close} />
          <Metric label="SMA 20" value={signal.sma_fast} />
          <Metric label="SMA 50" value={signal.sma_slow} />
          <Metric label="RSI(14)" value={signal.rsi} />
        </div>
      )}

      <div ref={containerRef} style={{ width: "100%", marginBottom: 16 }} />

      <div style={s.controlsRow}>
        <button style={s.btn} onClick={runBacktest}>{loadingBt ? "Running…" : "Run backtest (1y)"}</button>
        <button style={{ ...s.btn, color: "#0ca30c", borderColor: "#0ca30c" }} onClick={() => sendOrder("BUY")}>Simulate BUY</button>
        <button style={{ ...s.btn, color: "#d03b3b", borderColor: "#d03b3b" }} onClick={() => sendOrder("SELL")}>Simulate SELL</button>
      </div>

      {orderMsg && <p style={s.sandboxNote}>{orderMsg}</p>}

      {backtest && (
        <div style={s.analysisBox}>
          <p style={s.label}>Backtest results (1 year, sandbox simulation)</p>
          <div style={s.metricsRow}>
            <Metric label="Final equity" value={backtest.final_equity} />
            <Metric label="Total return" value={backtest.total_return_pct + "%"} />
            <Metric label="Max drawdown" value={backtest.max_drawdown_pct + "%"} />
            <Metric label="Win rate" value={backtest.win_rate_pct + "%"} />
          </div>
          <p style={s.sub}>{backtest.total_trades} total trades simulated. This is historical simulation, not a guarantee of future results.</p>
        </div>
      )}

      <p style={s.footnote}>Sandbox mode — no real orders are placed. Data via yfinance.</p>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div style={s.metric}>
      <p style={s.metricLabel}>{label}</p>
      <p style={s.metricValue}>{value ?? "—"}</p>
    </div>
  );
}

const s = {
  page: { maxWidth: 900, margin: "0 auto", padding: 24, fontFamily: "sans-serif" },
  h1: { fontSize: 22, fontWeight: 500, margin: "0 0 4px" },
  sub: { fontSize: 13, color: "#898781", margin: "4px 0" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 12, marginTop: 16 },
  card: { display: "flex", flexDirection: "column", gap: 4, padding: 16, borderRadius: 12, border: "0.5px solid rgba(140,140,140,0.3)", background: "transparent", cursor: "pointer", textAlign: "left" },
  ticker: { fontSize: 18, fontWeight: 500, margin: 0 },
  name: { fontSize: 13, color: "#898781", margin: 0 },
  backBtn: { marginBottom: 16, padding: "6px 12px", borderRadius: 8, border: "0.5px solid rgba(140,140,140,0.3)", background: "transparent", cursor: "pointer" },
  headerRow: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  badge: { padding: "6px 14px", borderRadius: 20, fontSize: 13, fontWeight: 500 },
  metricsRow: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(110px,1fr))", gap: 10, marginBottom: 16 },
  metric: { background: "rgba(140,140,140,0.08)", borderRadius: 8, padding: "10px 12px" },
  metricLabel: { fontSize: 11, color: "#898781", margin: 0 },
  metricValue: { fontSize: 16, fontWeight: 500, margin: "2px 0 0" },
  controlsRow: { display: "flex", gap: 10, marginBottom: 12, flexWrap: "wrap" },
  btn: { padding: "8px 16px", borderRadius: 8, border: "0.5px solid rgba(140,140,140,0.4)", background: "transparent", cursor: "pointer", fontWeight: 500 },
  sandboxNote: { fontSize: 13, color: "#898781", background: "rgba(140,140,140,0.08)", padding: "8px 12px", borderRadius: 8, marginBottom: 12 },
  analysisBox: { background: "rgba(140,140,140,0.06)", borderRadius: 12, padding: "16px 20px", marginBottom: 16 },
  label: { fontSize: 13, fontWeight: 500, color: "#2a78d6", margin: "0 0 10px" },
  footnote: { fontSize: 11, color: "#898787", marginTop: 8 },
};
