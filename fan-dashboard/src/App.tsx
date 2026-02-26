import React, { useEffect, useState } from "react";
import "./App.css";

function App() {
  const API_BASE = "http://localhost:5000"; // works from browser

  const [fanData, setFanData] = useState<any>(null);
  const [liveHistory, setLiveHistory] = useState<string[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [date, setDate] = useState("");
  const [predChartUrl, setPredChartUrl] = useState("");

  // ✅ Pick live fan safely (if backend sends Fan-2 or different key)
  const firstFanKey = fanData ? Object.keys(fanData)[0] : null;
  const liveFan = firstFanKey ? fanData[firstFanKey] : null;
  const liveFanName = firstFanKey || "Fan-1";

  // ✅ fallback values if no live data yet (UI must still show)
  const defaultFan = {
    timestamp: "--",
    rpm: 0,
    temperature: 0,
    humidity: 0,
    current: 0,
    pressure: 0,
    status: "unknown",
  };

  // ✅ use real live data if available else use default zero values
  const displayFan = liveFan || defaultFan;

  // 🔴 LIVE STATE CALCULATIONS
  const liveTotal = liveHistory.length;
  const liveAnomalyCount = liveHistory.filter((s) => s === "anomaly").length;
  const livePct =
    liveTotal === 0 ? 0 : Math.round((liveAnomalyCount / liveTotal) * 100);

  const currentStatus = displayFan.status || "normal";

  // 🔴 Real-time stream
  useEffect(() => {
    const eventSource = new EventSource(`${API_BASE}/stream`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setFanData(data);

      // ✅ use safe fan key
      const k = data ? Object.keys(data)[0] : null;
      const status = k ? data?.[k]?.status : null;

      if (status) {
        setLiveHistory((prev) => [...prev, status].slice(-50)); // last 50 samples
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [API_BASE]);

  // 📅 Load historical data
  const loadHistory = async () => {
    try {
      if (!date) return;

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
    }
  };

  // 📥 Download CSV
  const downloadCSV = () => {
    if (!date) return;
    window.open(`${API_BASE}/download/csv?date=${date}`, "_blank");
  };

  // 📤 Download Excel
  const downloadExcel = () => {
    if (!date) return;
    window.open(`${API_BASE}/download/excel?date=${date}`, "_blank");
  };

  // 📊 Prediction Chart
  const showPredictionChart = () => {
    if (!date) {
      alert("Enter date first (DD-MM-YYYY)");
      return;
    }
    setPredChartUrl(
      `${API_BASE}/chart/prediction?date=${date}&fan=${liveFanName}&t=${Date.now()}`
    );
  };

  return (
    <div className="container">
      <h1> Tunnel Fan Monitoring Dashboard</h1>

      {/* 🔴 LIVE STATUS PANEL */}
      <div className="live-panel">
  <div className="live-indicator">
    <span
      className={
        currentStatus === "anomaly"
          ? "dot-anomaly"
          : currentStatus === "normal"
          ? "dot-normal"
          : "dot-unknown"
      }
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
      Live Anomaly %: <strong>{livePct}%</strong>
    </div>
    <div>Samples: {liveTotal}</div>
    <div>Last Update: {displayFan.timestamp}</div>
  </div>
</div>

      {/* ✅ LIVE CIRCLE UI ALWAYS VISIBLE (even when no data) */}
      <div className="panel">
        <div className="panel-header">
          <div className="title">
            <div className="title-main">Tunnel Fan Monitoring</div>
            <div className="title-sub">Live Parameters ({liveFanName})</div>
          </div>

          <div className="right-meta">
            <div className="meta-line">Last Update</div>
            <div className="meta-value">{displayFan.timestamp}</div>
          </div>
        </div>

        <div className="widgets-row">
          <div
            className={`circle ${
              displayFan.rpm < 3800 || displayFan.rpm > 4300 ? "danger" : "ok"
            }`}
          >
            <div className="circle-label">RPM</div>
            <div className="circle-value">{Number(displayFan.rpm).toFixed(0)}</div>
            <div className="circle-unit">rpm</div>
          </div>

          <div
            className={`circle ${
              displayFan.temperature < 20 || displayFan.temperature > 40
                ? "danger"
                : "ok"
            }`}
          >
            <div className="circle-label">Temperature</div>
            <div className="circle-value">
              {Number(displayFan.temperature).toFixed(1)}
            </div>
            <div className="circle-unit">°C</div>
          </div>

          <div
            className={`circle ${
              displayFan.humidity < 30 || displayFan.humidity > 65 ? "danger" : "ok"
            }`}
          >
            <div className="circle-label">Humidity</div>
            <div className="circle-value">
              {Number(displayFan.humidity).toFixed(0)}
            </div>
            <div className="circle-unit">%</div>
          </div>

          <div
            className={`circle ${
              displayFan.current < 0.776 || displayFan.current > 2.43
                ? "danger"
                : "ok"
            }`}
          >
            <div className="circle-label">Current</div>
            <div className="circle-value">
              {Number(displayFan.current).toFixed(2)}
            </div>
            <div className="circle-unit">A</div>
          </div>
        </div>

        <div
  className={`status-banner ${
    displayFan.status === "anomaly"
      ? "status-anom"
      : displayFan.status === "normal"
      ? "status-norm"
      : "status-wait"
  }`}
></div>
  {displayFan.status === "anomaly"
    ? "⚠️ Anomaly Detected – Model Prediction"
    : displayFan.status === "normal"
    ? "✅ System Normal – Model Prediction"
    : "⏳ Waiting for model prediction…"}
</div>

      {/* Prediction Chart Image */}
      {predChartUrl && (
        <div className="chart-box">
          <h3>Stored ML Prediction (Normal vs Anomaly)</h3>
          <img className="chart-img" src={predChartUrl} alt="Prediction Chart" />
        </div>
      )}

      {/* Historical Data */}
      <div className="history-section">
        <h2>Historical Data</h2>

        <input
          type="text"
          placeholder="DD-MM-YYYY"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />

        <button onClick={loadHistory}>Load Data</button>
        <button onClick={downloadCSV}>Download CSV</button>
        <button onClick={downloadExcel}>Download Excel</button>
        <button onClick={showPredictionChart}>Prediction Chart</button>

        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Temp</th>
              <th>Humidity</th>
              <th>Current</th>
              <th>RPM</th>
              <th>Pressure</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {history.map((item, index) => (
              <tr key={index}>
                <td>{item.timestamp}</td>
                <td>{item.temperature}</td>
                <td>{item.humidity}</td>
                <td>{item.current}</td>
                <td>{item.rpm}</td>
                <td>{item.pressure}</td>
                <td
                  className={
                    item.status === "anomaly" ? "status-anomaly" : "status-normal"
                  }
                >
                  {(item.status || "normal").toUpperCase()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;