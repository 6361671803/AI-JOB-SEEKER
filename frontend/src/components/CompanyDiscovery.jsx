import { useState } from "react";
import { discoverCompanies } from "../api/client";

export default function CompanyDiscovery({ candidateId, onDiscovered }) {
  const [status, setStatus] = useState("idle"); // idle | searching | error
  const [error, setError] = useState(null);

  const handleDiscover = async () => {
    setStatus("searching");
    setError(null);
    try {
      const result = await discoverCompanies(candidateId);
      setStatus("idle");
      onDiscovered(result);
    } catch (err) {
      setStatus("error");
      setError(err.message);
    }
  };

  return (
    <div className="app-main--narrow" style={{ margin: "0 auto" }}>
      <h1>Finding companies for you</h1>
      <p className="subtitle">
        Your AI assistant is searching for real companies hiring for your target role(s) and
        location, and trying to find each one's official careers page.
      </p>

      {status === "searching" ? (
        <div className="progress-box">
          <div className="status-checklist-item">
            <span className="check-icon active" aria-hidden="true">⟳</span>
            Searching for companies hiring for your target roles...
          </div>
          <p className="hint" style={{ marginTop: 10 }}>
            This runs several real web searches and can take a minute or two — we show progress
            honestly rather than a fake bar, since results only appear once the search actually
            completes.
          </p>
        </div>
      ) : (
        <div className="empty-state" style={{ marginTop: 20 }}>
          <div className="empty-state-icon" aria-hidden="true">🏢</div>
          <h3>Ready to discover companies</h3>
          <p>We'll look for companies matching your role and location preferences.</p>
        </div>
      )}

      {error && <p className="error-text">{error}</p>}

      <div className="button-row">
        <button className="btn btn-primary" onClick={handleDiscover} disabled={status === "searching"}>
          {status === "searching" ? "Discovering Companies..." : "Discover Companies"}
        </button>
      </div>
    </div>
  );
}
