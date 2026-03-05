import React, { useEffect, useRef, useState } from "react";
import "./App.css";
import Login from "./Login";

// Reusable Circular Progress Widget
const CircularWidget = ({ label, value, unit, min, max, isDanger }: any) => {
  const percentage = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  const color = isDanger ? "#ef4444" : "#10b981";

  // Formatter specifically for precise numbers
  const displayValue = label === 'Current' || label === 'Temperature'
    ? Number(value).toFixed(2)
    : Number(value).toFixed(0);

  return (
    <div className="widget-card">
      <div className="progress-container">
        <svg className="progress-ring" width="140" height="140">
          <circle
            className="progress-ring__circle-bg"
            strokeWidth="8"
            fill="transparent"
            r={radius}
            cx="70"
            cy="70"
          />
          <circle
            className="progress-ring__circle"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            fill="transparent"
            r={radius}
            cx="70"
            cy="70"
            style={{
              strokeDasharray: circumference,
              strokeDashoffset: strokeDashoffset,
            }}
          />
        </svg>
        <div className="progress-content">
          <div className="circle-value" style={{ textShadow: `0 0 15px ${color}60` }}>{displayValue}</div>
          <div className="circle-unit">{unit}</div>
        </div>
      </div>
      <div className="circle-label">{label}</div>
    </div>
  );
};

// ─── Sliding Window Engine ────────────────────────────────────────────────────
// Tracks the last N anomaly events. Fires WARNING at ≥ ceil(threshold/2),
// CRITICAL at ≥ threshold. Entries older than decayMs are auto-expired.
interface WindowEntry {
  timestamp: number;
  fanName: string;
}

interface WindowState {
  level: "normal" | "warning" | "critical";
  anomalyCount: number;
  windowSize: number;
  criticalThreshold: number;
  entries: WindowEntry[];
  totalCriticalFires: number;
}

function useSlidingWindow(
  windowSize: number = 7,
  criticalThreshold: number = 5,
  decayMs: number = 60000
) {
  const [swState, setSwState] = useState<WindowState>({
    level: "normal",
    anomalyCount: 0,
    windowSize,
    criticalThreshold,
    entries: [],
    totalCriticalFires: 0,
  });

  const entriesRef = useRef<WindowEntry[]>([]);
  const totalCriticalRef = useRef(0);
  const prevLevelRef = useRef<"normal" | "warning" | "critical">("normal");

  const push = (isAnomaly: boolean, fanName: string) => {
    // Expire old entries beyond decay window
    const cutoff = Date.now() - decayMs;
    entriesRef.current = entriesRef.current.filter((e) => e.timestamp > cutoff);

    if (isAnomaly) {
      entriesRef.current.push({ timestamp: Date.now(), fanName });
      // Keep only last N
      if (entriesRef.current.length > windowSize) {
        entriesRef.current.shift();
      }
    }

    const count = entriesRef.current.length;
    const level: "normal" | "warning" | "critical" =
      count >= criticalThreshold
        ? "critical"
        : count >= Math.ceil(criticalThreshold / 2)
          ? "warning"
          : "normal";

    // Count new critical fires (transitions into critical)
    if (level === "critical" && prevLevelRef.current !== "critical") {
      totalCriticalRef.current += 1;
    }
    prevLevelRef.current = level;

    setSwState({
      level,
      anomalyCount: count,
      windowSize,
      criticalThreshold,
      entries: [...entriesRef.current],
      totalCriticalFires: totalCriticalRef.current,
    });
  };

  const reset = () => {
    entriesRef.current = [];
    totalCriticalRef.current = 0;
    prevLevelRef.current = "normal";
    setSwState({
      level: "normal",
      anomalyCount: 0,
      windowSize,
      criticalThreshold,
      entries: [],
      totalCriticalFires: 0,
    });
  };

  return { swState, push, reset };
}

// ─── Sliding Window Panel UI ──────────────────────────────────────────────────
const SW_COLORS = {
  normal: { border: "#1a4d1a", bg: "#0d1f0d", text: "#4ade80", badge: "#166534", dot: "#22c55e" },
  warning: { border: "#4d3800", bg: "#1c1500", text: "#fbbf24", badge: "#78350f", dot: "#f59e0b" },
  critical: { border: "#7f1d1d", bg: "#1a0000", text: "#f87171", badge: "#991b1b", dot: "#ef4444" },
};

const SlidingWindowPanel = ({
  swState,
  onReset,
}: {
  swState: WindowState;
  onReset: () => void;
}) => {
  const c = SW_COLORS[swState.level];
  const slots = Array.from({ length: swState.windowSize }, (_, i) => {
    const entry = swState.entries[swState.entries.length - swState.windowSize + i];
    return entry ?? null;
  });

  return (
    <div
      className="glass-panel"
      style={{
        border: `2px solid ${c.border}`,
        background: `linear-gradient(135deg, ${c.bg} 0%, #0f172a 100%)`,
        transition: "border-color 0.4s, background 0.4s",
      }}
    >
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div>
          <div className="title-main" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {/* Pulsing dot */}
            <span style={{ position: "relative", display: "inline-flex", width: 12, height: 12 }}>
              <span
                style={{
                  position: "absolute", inset: 0, borderRadius: "50%",
                  background: c.dot, opacity: 0.5,
                  animation: swState.level !== "normal" ? "sw-ping 1.2s cubic-bezier(0,0,0.2,1) infinite" : "none",
                }}
              />
              <span style={{ borderRadius: "50%", width: 12, height: 12, background: c.dot }} />
            </span>
            Sliding Window Alert Engine
          </div>
          <div className="title-sub">
            Fires CRITICAL when {swState.criticalThreshold} anomalies occur within last {swState.windowSize} detections
          </div>
        </div>

        {/* Level badge */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              background: c.badge, color: c.text,
              padding: "4px 14px", borderRadius: "20px",
              fontSize: "0.78rem", fontWeight: 800, letterSpacing: "1.5px",
            }}
          >
            {swState.level.toUpperCase()}
          </span>
          <button
            onClick={onReset}
            style={{
              background: "transparent", border: "1px solid #334155",
              color: "#64748b", borderRadius: "6px",
              padding: "4px 10px", fontSize: "0.75rem", cursor: "pointer",
            }}
          >
            ↺ Reset
          </button>
        </div>
      </div>

      {/* Window slots visualiser */}
      <div style={{ marginBottom: "16px" }}>
        <div style={{ fontSize: "0.72rem", color: "#64748b", marginBottom: "8px", letterSpacing: "1px" }}>
          WINDOW BUFFER — last {swState.windowSize} anomaly slots
        </div>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", alignItems: "center" }}>
          {slots.map((entry, i) => {
            const filled = !!entry;
            const isCritZone = i >= swState.windowSize - swState.criticalThreshold;
            return (
              <div
                key={i}
                title={entry ? `Anomaly at ${new Date(entry.timestamp).toLocaleTimeString()} — ${entry.fanName}` : "Empty slot"}
                style={{
                  width: 34, height: 34, borderRadius: "7px",
                  background: filled
                    ? isCritZone ? "#ef4444" : "#f59e0b"
                    : "#1e293b",
                  border: `2px solid ${filled ? (isCritZone ? "#7f1d1d" : "#78350f") : "#334155"}`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "1rem",
                  transition: "all 0.3s ease",
                  transform: filled ? "scale(1.08)" : "scale(1)",
                  boxShadow: filled ? `0 0 10px ${isCritZone ? "#ef444466" : "#f59e0b55"}` : "none",
                  cursor: "help",
                }}
              >
                {filled ? "⚠" : ""}
              </div>
            );
          })}
          <span style={{ fontSize: "0.78rem", color: "#64748b", marginLeft: "6px" }}>
            {swState.anomalyCount} / {swState.windowSize} filled
          </span>
        </div>
      </div>

      {/* Stats row */}
      <div
        style={{
          display: "grid", gridTemplateColumns: "repeat(3, 1fr)",
          gap: "10px", marginBottom: "14px",
        }}
      >
        {[
          { label: "Window Anomalies", value: `${swState.anomalyCount} / ${swState.windowSize}`, color: c.text },
          { label: "Threshold", value: `${swState.criticalThreshold} to CRITICAL`, color: "#7dd3fc" },
          { label: "Critical Fires", value: swState.totalCriticalFires, color: "#f87171" },
        ].map(({ label, value, color }) => (
          <div
            key={label}
            style={{
              background: "#0f172a", border: "1px solid #1e293b",
              borderRadius: "8px", padding: "10px 14px",
            }}
          >
            <div style={{ fontSize: "0.7rem", color: "#64748b", marginBottom: "4px" }}>{label}</div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700, color }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Status message */}
      <div
        style={{
          background: c.bg, border: `1px solid ${c.border}`,
          borderRadius: "8px", padding: "10px 16px",
          fontSize: "0.82rem", color: c.text, fontWeight: 600,
        }}
      >
        {swState.level === "critical" &&
          `🚨 CRITICAL — ${swState.anomalyCount} anomalies in the active window. Immediate inspection required!`}
        {swState.level === "warning" &&
          `⚠️ WARNING — ${swState.anomalyCount} anomalies accumulating. Approaching critical threshold (${swState.criticalThreshold}).`}
        {swState.level === "normal" &&
          `✅ NORMAL — Only ${swState.anomalyCount} anomaly in current window. System stable.`}
      </div>

      <style>{`
        @keyframes sw-ping {
          75%, 100% { transform: scale(2.2); opacity: 0; }
        }
      `}</style>
    </div>
  );
};

// ─── App ──────────────────────────────────────────────────────────────────────
function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const API_BASE = "http://localhost:5000";

  const [fanData, setFanData] = useState<any>(null);
  const [liveHistory, setLiveHistory] = useState<string[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [date, setDate] = useState("");
  const [predChartUrl, setPredChartUrl] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(false);

  // ── Sliding Window (window=7, critical at 5 anomalies, decay 60s) ──────────
  const { swState, push: swPush, reset: swReset } = useSlidingWindow(7, 5, 60000);

  // Pick live fan safely
  const firstFanKey = fanData ? Object.keys(fanData)[0] : null;
  const liveFan = firstFanKey ? fanData[firstFanKey] : null;
  const liveFanName = firstFanKey || "Fan-1";

  const defaultFan = {
    timestamp: "--",
    rpm: 0,
    temperature: 0,
    humidity: 0,
    current: 0,
    vibration: 0,
    status: "unknown",
  };

  const displayFan = liveFan || defaultFan;

  const liveTotal = liveHistory.length;
  const liveAnomalyCount = liveHistory.filter((s) => s === "anomaly").length;
  const livePct = liveTotal === 0 ? 0 : Math.round((liveAnomalyCount / liveTotal) * 100);

  const currentStatus = displayFan.status || "normal";

  // Real-time stream
  useEffect(() => {
    const eventSource = new EventSource(`${API_BASE}/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setFanData(data);

        const k = data ? Object.keys(data)[0] : null;
        const status = k ? data?.[k]?.status : null;

        if (status) {
          setLiveHistory((prev) => [...prev, status].slice(-50));

          // ── Feed every prediction into the sliding window engine ──────────
          swPush(status === "anomaly", k || "Fan-1");
        }
      } catch (e) {
        console.error("Error parsing event data", e);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [API_BASE]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load historical data
  const loadHistory = async () => {
    try {
      if (!date) {
        alert("Please enter a date first (DD-MM-YYYY)");
        return;
      }

      setLoadingHistory(true);
      const response = await fetch(`${API_BASE}/history?date=${date}`);

      if (!response.ok) {
        const txt = await response.text();
        console.error("History error:", response.status, txt);
        alert("History API error. Check backend.");
        return;
      }

      const data = await response.json();
      setHistory(data);
    } catch (e) {
      console.error("Failed to fetch history:", e);
      alert("Failed to fetch. Check CORS / backend running.");
    } finally {
      setLoadingHistory(false);
    }
  };

  const downloadCSV = () => {
    if (!date) return;
    window.open(`${API_BASE}/download/csv?date=${date}`, "_blank");
  };

  const downloadExcel = () => {
    if (!date) return;
    window.open(`${API_BASE}/download/excel?date=${date}`, "_blank");
  };

  const showPredictionChart = () => {
    if (!date) {
      alert("Enter date first (DD-MM-YYYY)");
      return;
    }
    setPredChartUrl(`${API_BASE}/chart/prediction?date=${date}&fan=${liveFanName}&t=${Date.now()}`);
  };

  if (!isAuthenticated) {
    return <Login onLogin={setIsAuthenticated} />;
  }

  return (
    <div className="container">
      {/* 🚨 Sliding Alert for Anomaly — UNCHANGED */}
      <div className={`alert-slider ${currentStatus === "anomaly" ? "show" : ""}`}>
        <div className="alert-icon">🚨</div>
        <div>
          <div style={{ fontSize: '1.1rem', marginBottom: '4px', fontWeight: 800 }}>CRITICAL ANOMALY</div>
          <div style={{ fontSize: '0.85rem', opacity: 0.95 }}>ML Model detected abnormal telemetry live.</div>
        </div>
      </div>

      <h1>Tunnel Fan Monitoring</h1>

      {/* LIVE STATUS PANEL — UNCHANGED */}
      <div className="glass-panel live-panel">
        <div className="live-indicator">
          <div
            className={`dot ${currentStatus === "anomaly"
              ? "dot-anomaly"
              : currentStatus === "normal"
                ? "dot-normal"
                : "dot-unknown"
              }`}
          />
          <span className="live-text">
            {currentStatus === "anomaly"
              ? "ANOMALY DETECTED (ML)"
              : currentStatus === "normal"
                ? "SYSTEM NORMAL (ML)"
                : "WAITING FOR ML PREDICTION..."}
          </span>
        </div>

        <div className="live-stats">
          <div>
            Anomaly Rate: <strong>{livePct}%</strong> <span style={{ opacity: 0.6 }}>({liveAnomalyCount}/{liveTotal} samples)</span>
          </div>
          <div>Last Update: <strong>{displayFan.timestamp}</strong></div>
        </div>
      </div>

      {/* MAIN DATA WIDGETS — UNCHANGED */}
      <div className="glass-panel">
        <div className="panel-header">
          <div>
            <div className="title-main">Live Parameters</div>
            <div className="title-sub">{liveFanName} Active Telemetry</div>
          </div>
          <div className="meta-value" style={{ color: '#38bdf8' }}>{displayFan.timestamp}</div>
        </div>

        <div className="widgets-row">
          <CircularWidget
            label="RPM"
            value={displayFan.rpm}
            unit="rpm"
            min={0}
            max={5000}
            isDanger={displayFan.status === "anomaly"}
          />

          <CircularWidget
            label="Temperature"
            value={displayFan.temperature}
            unit="°C"
            min={0}
            max={80}
            isDanger={displayFan.status === "anomaly"}
          />

          <CircularWidget
            label="Humidity"
            value={displayFan.humidity}
            unit="%"
            min={0}
            max={100}
            isDanger={displayFan.status === "anomaly"}
          />

          <CircularWidget
            label="Current"
            value={displayFan.current}
            unit="A"
            min={0}
            max={5}
            isDanger={displayFan.status === "anomaly"}
          />
        </div>

        <div
          className={`status-banner ${displayFan.status === "anomaly"
            ? "status-anom"
            : displayFan.status === "normal"
              ? "status-norm"
              : "status-wait"
            }`}
        >
          {displayFan.status === "anomaly" && "⚠️ Critical Anomaly Detected by ML Output Model"}
          {displayFan.status === "normal" && "✅ All Systems Operational – Telemetry Normal"}
          {displayFan.status === "unknown" && "⏳ Gathering Telemetry Data..."}
        </div>
      </div>

      {/* ── NEW: SLIDING WINDOW CRITICAL ALERT PANEL ── */}
      <SlidingWindowPanel swState={swState} onReset={swReset} />

      {/* CHART SECTION — UNCHANGED */}
      {predChartUrl && (
        <div className="chart-box">
          <h3>Prediction Analysis Chart</h3>
          <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: 4 }}>Historical data patterns for {date}</p>
          <img className="chart-img" src={predChartUrl} alt="Prediction Analysis" />
        </div>
      )}

      {/* HISTORY SECTION — UNCHANGED */}
      <div className="glass-panel">
        <div className="panel-header">
          <div>
            <div className="title-main">Historical Data Archive</div>
            <div className="title-sub">Query past telemetry and export reports</div>
          </div>
        </div>

        <div className="controls-row">
          <input
            type="text"
            placeholder="DD-MM-YYYY"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <button onClick={loadHistory} disabled={loadingHistory}>
            {loadingHistory ? "Loading..." : "Load Data"}
          </button>
          <button onClick={downloadCSV} style={{ background: 'linear-gradient(to right, #10b981, #059669)' }}>
            Export CSV
          </button>
          <button onClick={downloadExcel} style={{ background: 'linear-gradient(to right, #10b981, #059669)' }}>
            Export Excel
          </button>
          <button onClick={showPredictionChart} style={{ background: 'linear-gradient(to right, #8b5cf6, #6d28d9)' }}>
            Generate Chart
          </button>
        </div>

        {loadingHistory && (
          <div className="loading-row">
            <div className="spinner" />
            <div>Fetching telemetry records from database...</div>
          </div>
        )}

        {history.length > 0 && (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Temp (°C)</th>
                  <th>Humidity (%)</th>
                  <th>Current (A)</th>
                  <th>RPM</th>
                  <th>Vibration</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item, index) => (
                  <tr key={index}>
                    <td>{item.timestamp}</td>
                    <td>{Number(item.temperature).toFixed(1)}</td>
                    <td>{Number(item.humidity).toFixed(0)}</td>
                    <td>{Number(item.current).toFixed(2)}</td>
                    <td>{Number(item.rpm).toFixed(0)}</td>
                    <td>{Number(item.vibration).toFixed(2)}</td>
                    <td>
                      <span className={`status-badge ${item.status === "anomaly" ? "badge-anomaly" : "badge-normal"}`}>
                        {(item.status || "normal").toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
