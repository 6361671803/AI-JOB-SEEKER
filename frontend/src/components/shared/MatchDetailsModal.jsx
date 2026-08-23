import { useEffect } from "react";
import { scoreTier } from "./MatchScoreBadge";

function BreakdownBar({ label, value }) {
  const { cls } = scoreTier(value);
  const color = cls === "score-strong" ? "var(--success)" : cls === "score-moderate" ? "var(--warning)" : "var(--danger)";
  return (
    <div className="breakdown-bar-row">
      <div className="breakdown-bar-label">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="breakdown-bar-track">
        <div className="breakdown-bar-fill" style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  );
}

export default function MatchDetailsModal({ job, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const { match } = job;
  if (!match) return null;

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-label={`Match details for ${job.title}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <h2>Why You Match</h2>
            <p className="subtitle">{job.title} at {job.company_name}</p>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <BreakdownBar label="Skills" value={match.breakdown.skills_score} />
        <BreakdownBar label="Experience" value={match.breakdown.experience_score} />
        <BreakdownBar label="Education" value={match.breakdown.education_score} />
        <BreakdownBar label="Role Relevance" value={match.breakdown.role_score} />
        <BreakdownBar label="Location" value={match.breakdown.location_score} />

        <div style={{ marginTop: 20 }}>
          <h3 style={{ fontSize: "0.9rem", marginBottom: 6 }}>Matched Skills</h3>
          {match.matched_required_skills.length + match.matched_preferred_skills.length === 0 ? (
            <p className="unknown">None found</p>
          ) : (
            <div className="tag-list">
              {[...match.matched_required_skills, ...match.matched_preferred_skills].map((s, i) => (
                <span className="tag" key={i}>✓ {s}</span>
              ))}
            </div>
          )}
        </div>

        <div style={{ marginTop: 14 }}>
          <h3 style={{ fontSize: "0.9rem", marginBottom: 6 }}>Missing Required Skills</h3>
          {match.missing_required_skills.length === 0 ? (
            <p className="unknown">None</p>
          ) : (
            <div className="tag-list">
              {match.missing_required_skills.map((s, i) => (
                <span className="tag" key={i} style={{ color: "var(--danger)" }}>⚠ {s}</span>
              ))}
            </div>
          )}
        </div>

        {match.missing_preferred_skills.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <h3 style={{ fontSize: "0.9rem", marginBottom: 6 }}>Missing Preferred Skills</h3>
            <div className="tag-list">
              {match.missing_preferred_skills.map((s, i) => (
                <span className="tag" key={i} style={{ color: "var(--warning)" }}>• {s}</span>
              ))}
            </div>
          </div>
        )}

        {match.eligibility_issues.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <h3 style={{ fontSize: "0.9rem", marginBottom: 6 }}>Potential Concerns</h3>
            <p style={{ color: "var(--danger)", fontSize: "0.88rem" }}>{match.eligibility_issues.join("; ")}</p>
          </div>
        )}

        <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
          <p style={{ fontSize: "0.88rem" }}>{match.why_this_matches}</p>
        </div>
      </div>
    </div>
  );
}
