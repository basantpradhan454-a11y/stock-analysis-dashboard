/*
Trading Dashboard — React frontend
------------------------------------
Install:  npm install react react-dom lightweight-charts
This component calls the FastAPI backend (main.py) running on http://localhost:8000

Flow:
  1. Asset list screen -> click an asset
  2. Dashboard opens -> candlestick chart (real OHLC from yfinance via backend)
  3. "AI Analysis" button -> fetches /api/analysis/<ticker> -> shows quant + technical summary
*/

import React, { useEffect, useRef, useState, useCallback } from "react";
import { createChart, CandlestickSeries } from "lightweight-charts";

const API_BASE = "http://localhost:8000";

export default function App() {
  const [assets, setAssets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loadingAssets, setLoadingAssets] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/assets`)
      .then((r) => r.json())
      .then(setAssets)
      .catch(() => setAssets([]))
      .finally(() => setLoadingAssets(false));
  }, []);

  if (selected) {
    return <Dashboard asset={selected} onBack={() => setSelected(null)} />;
  }

  return (
    <div style={styles.page}>
      <h1 style={styles.h1}>Watchlist</h1>
      <p style={styles.sub}>Chart kholne ke liye ek asset chuniye</p>
      {loadingAssets && <p style={styles.sub}>Loading assets\u2026</p>}
      <div style={styles.grid}>
        {assets.map((a) => (
          <button key={a.ticker} style={styles.card} onClick={() => setSelected(a)}>
            <span style={styles.ticker}>{a.ticker}</span>
            <span style={styles.name}>{a.name}</span>
            <span style={styles.type}>{a.type}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Dashboard({ asset, onBack }) {
  const chartRef = useRef(null);
  const containerRef = useRef(null);
  const seriesRef = useRef(null);

  const [period, setPeriod] = useState("6mo");
  const [interval, setIntervalVal] = useState("1d");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastCandle, setLastCandle] = useState(null);

  const [analysis, setAnalysis] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: "transparent" }, textColor: "#898781" },
      grid: {
        vertLines: { color: "rgba(140,140,140,0.08)" },
        horzLines: { color: "rgba(140,140,140,0.08)" },
      },
      width: containerRef.current.clientWidth,
      height: 380,
      timeScale: { borderColor: "rgba(140,140,140,0.2)" },
      rightPriceScale: { borderColor: "rgba(140,140,140,0.2)" },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#0ca30c",
      downColor: "#d03b3b",
      borderVisible: false,
      wickUpColor: "#0ca30c",
      wickDownColor: "#d03b3b",
    });
    chartRef.current = chart;
    seriesRef.current = series;

    const onResize = () => chart.applyOptions({ width: containerRef.current.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, []);

  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/api/ohlc/${encodeURIComponent(asset.ticker)}?period=${period}&interval=${interval}`)
      .then((r) => {
        if (!r.ok) throw new Error("Failed to fetch data");
        return r.json();
      })
      .then((data) => {
        const candles = data.candles.map((c) => ({
          time: interval.includes("m") || interval.includes("h") ? c.time : c.time.slice(0, 10),
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }));
        seriesRef.current.setData(candles);
        chartRef.current.timeScale().fitContent();
        setLastCandle(data.candles[data.candles.length - 1]);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [asset.ticker, period, interval]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const runAnalysis = () => {
    setShowAnalysis(true);
    setAnalysisLoading(true);
    fetch(`${API_BASE}/api/analysis/${encodeURIComponent(asset.ticker)}?period=${period}&interval=${interval}`)
      .then((r) => r.json())
      .then(setAnalysis)
      .catch(() => setAnalysis(null))
      .finally(() => setAnalysisLoading(false));
  };

  const change =
    lastCandle && lastCandle.open ? (((lastCandle.close - lastCandle.open) / lastCandle.open) * 100).toFixed(2) : null;

  return (
    <div style={styles.page}>
      <button style={styles.backBtn} onClick={onBack}>
        \u2190 Assets
      </button>

      <div style={styles.headerRow}>
        <div>
          <p style={styles.ticker}>{asset.ticker}</p>
          <p style={styles.name}>{asset.name}</p>
        </div>
        {lastCandle && (
          <div style={{ textAlign: "right" }}>
            <p style={styles.price}>{lastCandle.close}</p>
            <p style={{ ...styles.change, color: change >= 0 ? "#0ca30c" : "#d03b3b" }}>
              {change >= 0 ? "+" : ""}
              {change}%
            </p>
          </div>
        )}
      </div>

      <div style={styles.controlsRow}>
        <select value={period} onChange={(e) => setPeriod(e.target.value)}>
          {["1mo", "3mo", "6mo", "1y", "2y", "5y"].map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <select value={interval} onChange={(e) => setIntervalVal(e.target.value)}>
          {["1d", "1wk", "1mo"].map((i) => (
            <option key={i} value={i}>
              {i}
            </option>
          ))}
        </select>
        <button style={styles.aiBtn} onClick={runAnalysis}>
          \u2728 AI Analysis
        </button>
      </div>

      {showAnalysis && (
        <div style={styles.analysisBox}>
          {analysisLoading && <p style={styles.sub}>Analyzing\u2026</p>}
          {!analysisLoading && analysis && (
            <>
              <p style={styles.analysisLabel}>Quant analysis</p>
              <p style={styles.analysisText}>{analysis.analysis.quant}</p>
              <p style={styles.analysisLabel}>Technical analysis</p>
              <p style={styles.analysisText}>{analysis.analysis.technical}</p>
              <p style={styles.analysisLabel}>Summary</p>
              <p style={styles.analysisText}>{analysis.analysis.summary}</p>
            </>
          )}
          {!analysisLoading && !analysis && <p style={styles.sub}>Analysis failed to load.</p>}
        </div>
      )}

      {loading && <p style={styles.sub}>Loading chart\u2026</p>}
      {error && <p style={{ ...styles.sub, color: "#d03b3b" }}>{error}</p>}
      <div ref={containerRef} style={{ width: "100%" }} />
      <p style={styles.footnote}>Data source: yfinance (via backend API)</p>
    </div>
  );
}

const styles = {
  page: { maxWidth: 900, margin: "0 auto", padding: "24px", fontFamily: "sans-serif" },
  h1: { fontSize: 22, fontWeight: 500, margin: "0 0 4px" },
  sub: { fontSize: 14, color: "#898781", margin: "0 0 16px" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 12 },
  card: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    gap: 4,
    padding: 16,
    borderRadius: 12,
    border: "0.5px solid rgba(140,140,140,0.3)",
    background: "transparent",
    cursor: "pointer",
    textAlign: "left",
  },
  ticker: { fontSize: 16, fontWeight: 500 },
  name: { fontSize: 13, color: "#898781" },
  type: { fontSize: 11, color: "#898781", marginTop: 4 },
  backBtn: {
    marginBottom: 16,
    padding: "6px 12px",
    borderRadius: 8,
    border: "0.5px solid rgba(140,140,140,0.3)",
    background: "transparent",
    cursor: "pointer",
  },
  headerRow: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 },
  price: { fontSize: 24, fontWeight: 500, margin: 0 },
  change: { fontSize: 13, margin: "2px 0 0" },
  controlsRow: { display: "flex", gap: 10, alignItems: "center", marginBottom: 16, flexWrap: "wrap" },
  aiBtn: {
    marginLeft: "auto",
    padding: "8px 16px",
    borderRadius: 8,
    border: "1px solid #2a78d6",
    background: "rgba(42,120,214,0.1)",
    color: "#2a78d6",
    cursor: "pointer",
    fontWeight: 500,
  },
  analysisBox: {
    background: "rgba(140,140,140,0.06)",
    borderRadius: 12,
    padding: "16px 20px",
    marginBottom: 16,
  },
  analysisLabel: { fontSize: 13, fontWeight: 500, color: "#2a78d6", margin: "0 0 6px" },
  analysisText: { fontSize: 14, color: "#52514e", lineHeight: 1.6, margin: "0 0 14px" },
  footnote: { fontSize: 11, color: "#898787", marginTop: 8 },
};
