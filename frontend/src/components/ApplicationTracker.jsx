import { useEffect, useState } from "react";
import { getTracker } from "../api/client";
import EmptyState from "./shared/EmptyState";

const STATUS_CLASS = {
  DISCOVERED: "status-neutral",
  MATCHED: "status-info",
  SELECTED: "status-info",
  PREPARING: "status-pending",
  WAITING_FOR_REVIEW: "status-pending",
  SUBMITTED: "status-success",
  FAILED: "status-failed",
};

const STAT_TILES = [
  { statuses: ["SUBMITTED"], label: "Applied" },
  { statuses: ["PREPARING"], label: "Preparing" },
  { statuses: ["WAITING_FOR_REVIEW"], label: "Waiting for Review" },
  { statuses: ["FAILED"], label: "Failed" },
];

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

export default function ApplicationTracker({ candidateId }) {
  const [tracker, setTracker] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getTracker(candidateId)
      .then((data) => { if (!cancelled) setTracker(data); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [candidateId]);

  return (
    <div>
      <h1>Applications</h1>
      <p className="subtitle">Every job this search has touched, from discovery through submission.</p>

      {loading && <p className="hint">Loading tracker...</p>}
      {error && <p className="error-text">{error}</p>}

      {tracker && (
        <>
          <div className="stat-grid">
            {STAT_TILES.map((tile) => (
              <div className="stat-tile" key={tile.label} style={{ cursor: "default" }}>
                <div className="stat-tile-value">
                  {tile.statuses.reduce((sum, s) => sum + (tracker.status_counts[s] || 0), 0)}
                </div>
                <div className="stat-tile-label">{tile.label}</div>
              </div>
            ))}
          </div>

          {tracker.entries.length === 0 ? (
            <EmptyState icon="📋" title="No jobs tracked yet">
              <p>Once you discover and select jobs, they'll show up here.</p>
            </EmptyState>
          ) : (
            <div className="tracker-table-wrap">
              <table className="tracker-table">
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Job Title</th>
                    <th>Match</th>
                    <th>Date Found</th>
                    <th>Date Posted</th>
                    <th>Application Date</th>
                    <th>Status</th>
                    <th>Links</th>
                  </tr>
                </thead>
                <tbody>
                  {tracker.entries.map((e) => (
                    <tr key={e.job_id}>
                      <td>{e.company_name}</td>
                      <td>{e.title}</td>
                      <td>{e.match_score != null ? `${e.match_score}%` : "—"}</td>
                      <td>{formatDate(e.date_found)}</td>
                      <td>{e.date_posted || "Posting date unavailable"}</td>
                      <td>{e.application_date ? formatDate(e.application_date) : "—"}</td>
                      <td>
                        <span className={`status-badge ${STATUS_CLASS[e.status] || "status-neutral"}`}>
                          {e.status.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="tracker-links">
                        {e.job_url && <a href={e.job_url} target="_blank" rel="noreferrer">Job</a>}
                        {e.application_url && <a href={e.application_url} target="_blank" rel="noreferrer">Apply</a>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
