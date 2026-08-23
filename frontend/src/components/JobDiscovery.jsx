import { useState } from "react";
import { discoverJobs } from "../api/client";

const WINDOW_OPTIONS = [7, 14, 30, 60, 90];

export default function JobDiscovery({ candidateId, onDiscovered }) {
  const [windowDays, setWindowDays] = useState(30);
  const [status, setStatus] = useState("idle"); // idle | searching | error
  const [error, setError] = useState(null);

  const handleDiscover = async () => {
    setStatus("searching");
    setError(null);
    try {
      const result = await discoverJobs(candidateId, windowDays);
      setStatus("idle");
      onDiscovered(result);
    } catch (err) {
      setStatus("error");
      setError(err.message);
    }
  };

  return (
    <div className="app-main--narrow" style={{ margin: "0 auto" }}>
      <h1>Finding opportunities for you</h1>
      <p className="subtitle">
        Your AI assistant will open each company's official careers page and look for current
        openings.
      </p>

      <div className="form-section">
        <h3>Posting recency window</h3>
        <p className="hint">Only jobs posted within this window are shown as main results.</p>
        <div className="radio-group radio-group-row">
          {WINDOW_OPTIONS.map((d) => (
            <label key={d} className="radio-option">
              <input
                type="radio"
                name="windowDays"
                checked={windowDays === d}
                onChange={() => setWindowDays(d)}
              />
              {d} days
            </label>
          ))}
        </div>
      </div>

      {status === "searching" ? (
        <div className="progress-box">
          <div className="status-checklist-item">
            <span className="check-icon active" aria-hidden="true">⟳</span>
            Visiting official career pages and reading job listings...
          </div>
          <p className="hint" style={{ marginTop: 10 }}>
            This renders each page in a real browser and can take several minutes for local
            models — this is real progress, not a placeholder.
          </p>
        </div>
      ) : (
        <div className="empty-state" style={{ marginTop: 20 }}>
          <div className="empty-state-icon" aria-hidden="true">🔎</div>
          <h3>Ready to search for jobs</h3>
          <p>We'll check each discovered company's careers page for current openings.</p>
        </div>
      )}

      {error && <p className="error-text">{error}</p>}

      <div className="button-row">
        <button className="btn btn-primary" onClick={handleDiscover} disabled={status === "searching"}>
          {status === "searching" ? "Discovering Jobs..." : "Discover Jobs"}
        </button>
      </div>
    </div>
  );
}
