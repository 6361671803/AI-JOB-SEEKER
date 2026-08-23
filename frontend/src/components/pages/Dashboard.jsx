import { useEffect, useState } from "react";
import { getTracker } from "../../api/client";

const STRONG_MATCH_THRESHOLD = 70;
const EVER_SELECTED = new Set(["SELECTED", "PREPARING", "WAITING_FOR_REVIEW", "SUBMITTED"]);

function ChecklistItem({ state, label }) {
  const icon = state === "done" ? "✓" : state === "active" ? "⟳" : "";
  return (
    <div className="status-checklist-item">
      <span className={`check-icon ${state}`} aria-hidden="true">{icon}</span>
      {label}
    </div>
  );
}

export default function Dashboard({ candidate, preferences, companyResult, jobResult, onNavigate }) {
  const [tracker, setTracker] = useState(null);

  useEffect(() => {
    if (!candidate) return;
    let cancelled = false;
    getTracker(candidate.id).then((data) => { if (!cancelled) setTracker(data); }).catch(() => {});
    return () => { cancelled = true; };
  }, [candidate, jobResult]);

  const allJobs = jobResult ? [...jobResult.recent_jobs, ...jobResult.unknown_date_jobs] : [];
  const jobsFound = jobResult
    ? jobResult.recent_jobs.length + jobResult.unknown_date_jobs.length + jobResult.older_jobs_count
    : 0;
  const strongMatches = allJobs.filter((j) => j.match && j.match.overall_score >= STRONG_MATCH_THRESHOLD).length;

  const statusCounts = tracker?.status_counts || {};
  const selectedCount = Object.entries(statusCounts)
    .filter(([status]) => EVER_SELECTED.has(status))
    .reduce((sum, [, count]) => sum + count, 0);
  const submittedCount = statusCounts.SUBMITTED || 0;

  const hasMatches = allJobs.some((j) => j.match);
  const firstName = candidate?.profile?.name?.split(" ")[0];

  return (
    <div>
      <div className="dashboard-hero">
        <h1>{firstName ? `Good to see you, ${firstName}` : "Your AI Career Assistant"}</h1>
        <p>
          {jobResult
            ? "Your AI job search is underway. Here's where things stand."
            : "Upload your resume and let your AI assistant find opportunities that actually fit you."}
        </p>
        <div className="button-row">
          <button className="btn btn-primary" onClick={() => onNavigate(jobResult ? "DISCOVER" : "RESUME")}>
            {jobResult ? "View Job Matches" : candidate ? "Continue to Preferences" : "Upload Resume"}
          </button>
          {candidate && (
            <button className="btn btn-secondary" onClick={() => onNavigate("APPLICATIONS")}>
              View Applications
            </button>
          )}
        </div>
      </div>

      <div className="stat-grid">
        <button className="stat-tile" onClick={() => onNavigate("DISCOVER")}>
          <div className="stat-tile-value">{jobsFound}</div>
          <div className="stat-tile-label">Jobs Found</div>
        </button>
        <button className="stat-tile" onClick={() => onNavigate("DISCOVER")}>
          <div className="stat-tile-value">{strongMatches}</div>
          <div className="stat-tile-label">Strong Matches</div>
        </button>
        <button className="stat-tile" onClick={() => onNavigate("APPLICATIONS")}>
          <div className="stat-tile-value">{selectedCount}</div>
          <div className="stat-tile-label">Selected</div>
        </button>
        <button className="stat-tile" onClick={() => onNavigate("APPLICATIONS")}>
          <div className="stat-tile-value">{submittedCount}</div>
          <div className="stat-tile-label">Applications Submitted</div>
        </button>
      </div>

      <div className="surface-card" style={{ padding: 20 }}>
        <h3 style={{ marginBottom: 4 }}>AI Job Search Status</h3>
        <div className="status-checklist">
          <ChecklistItem state={candidate ? "done" : "pending"} label="Resume analyzed" />
          <ChecklistItem state={preferences ? "done" : candidate ? "active" : "pending"} label="Preferences loaded" />
          <ChecklistItem state={companyResult ? "done" : preferences ? "active" : "pending"} label="Companies discovered" />
          <ChecklistItem state={jobResult ? "done" : companyResult ? "active" : "pending"} label={jobResult ? `${jobsFound} jobs found` : "Jobs found"} />
          <ChecklistItem state={hasMatches ? "done" : jobResult ? "active" : "pending"} label={hasMatches ? `${strongMatches} strong matches` : "Matching jobs"} />
        </div>
      </div>
    </div>
  );
}
