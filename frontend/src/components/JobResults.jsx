import { useEffect, useMemo, useState } from "react";
import { getJobs, matchJobs, selectJobs } from "../api/client";
import { useToast } from "../context/ToastContext";
import MatchScoreBadge from "./shared/MatchScoreBadge";
import JobFilters from "./shared/JobFilters";
import MatchDetailsModal from "./shared/MatchDetailsModal";
import JobDescriptionModal from "./shared/JobDescriptionModal";
import EmptyState from "./shared/EmptyState";
import SkeletonCards from "./shared/Skeleton";

const WINDOW_OPTIONS = [7, 14, 30, 60, 90];
const STRONG_MATCH_THRESHOLD = 70;

const SORTERS = {
  best_match: (a, b) => (b.match?.overall_score || 0) - (a.match?.overall_score || 0),
  newest: (a, b) => (b.posted_date_parsed || "").localeCompare(a.posted_date_parsed || ""),
  company: (a, b) => a.company_name.localeCompare(b.company_name),
};

function skillList(label, skills, symbol, className) {
  if (!skills || skills.length === 0) return null;
  return (
    <p className={`job-skill-line ${className || ""}`}>
      <strong>{label}:</strong> {skills.map((s) => `${symbol} ${s}`).join("  ")}
    </p>
  );
}

function JobCard({ j, rank, selectable, checked, onToggle, onViewDetails, onViewDescription }) {
  const { match } = j;

  return (
    <div className={`job-card ${checked ? "job-card-selected" : ""}`}>
      <div className="job-card-header">
        <h3>
          {selectable && (
            <input
              type="checkbox"
              className="job-select-checkbox"
              checked={checked}
              onChange={() => onToggle(j.id)}
              aria-label={`Select ${j.title} for application`}
            />
          )}
          {rank != null && <span className="rank-badge">#{rank}</span>} {j.title}
        </h3>
        {match && <MatchScoreBadge score={match.overall_score} />}
      </div>
      <p className="company-meta">
        {j.company_name}
        {j.location && <span> · {j.location}</span>}
        {j.work_mode && <span> · {j.work_mode}</span>}
      </p>
      <p className="job-meta">
        <span>Posted: {j.date_posted || "Posting date unavailable"}</span>
        {j.employment_type && <span> · {j.employment_type}</span>}
        {j.experience_requirement && <span> · {j.experience_requirement}</span>}
      </p>

      {!match && (
        <>
          {skillList("Required skills", j.required_skills, "✓")}
          {skillList("Preferred skills", j.preferred_skills, "•")}
        </>
      )}

      {match && (
        <>
          {skillList("Matched", [...match.matched_required_skills, ...match.matched_preferred_skills].slice(0, 6), "✓", "matched-line")}
          {match.missing_required_skills.length > 0 &&
            skillList("Missing (required)", match.missing_required_skills, "⚠", "missing-required-line")}
          <p className="why-matches-preview">{match.why_this_matches}</p>
        </>
      )}

      <div className="company-links">
        {j.job_url ? (
          <a href={j.job_url} target="_blank" rel="noreferrer">View Job</a>
        ) : (
          <span className="unknown">Job page link not found</span>
        )}
        <button className="btn-ghost" onClick={() => onViewDescription(j)}>Job Description</button>
        {match && (
          <button className="btn-ghost" onClick={() => onViewDetails(j)}>Match Details</button>
        )}
      </div>
    </div>
  );
}

export default function JobResults({
  candidateId, result, companiesDiscoveredCount, onRediscover, onResultChange, onSelectionApproved,
}) {
  const { recent_jobs, unknown_date_jobs, older_jobs_count, window_days, companies_skipped } = result;
  const [showUnknown, setShowUnknown] = useState(false);
  const [refiltering, setRefiltering] = useState(false);
  const [matching, setMatching] = useState(false);
  const [selecting, setSelecting] = useState(false);
  const [error, setError] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [detailsJob, setDetailsJob] = useState(null);
  const [descriptionJob, setDescriptionJob] = useState(null);
  const [sortKey, setSortKey] = useState("best_match");
  const [filters, setFilters] = useState({ locations: [], workModes: [], minScore: 0 });
  const notify = useToast();

  // Re-sync checkbox state from the server's truth whenever the result set changes
  // (e.g. after re-matching, which resets any prior selection server-side).
  useEffect(() => {
    setSelectedIds(new Set([...recent_jobs, ...unknown_date_jobs].filter((j) => j.status === "SELECTED").map((j) => j.id)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result]);

  const allJobs = [...recent_jobs, ...unknown_date_jobs];
  const alreadyMatched = allJobs.some((j) => j.match !== null);
  const strongMatchCount = allJobs.filter((j) => j.match && j.match.overall_score >= STRONG_MATCH_THRESHOLD).length;
  const totalJobsDiscovered = recent_jobs.length + unknown_date_jobs.length + older_jobs_count;

  const filteredRecent = useMemo(() => {
    let list = recent_jobs.filter((j) => {
      if (filters.locations.length && !filters.locations.includes(j.location)) return false;
      if (filters.workModes.length && !filters.workModes.includes(j.work_mode)) return false;
      if (filters.minScore > 0 && (!j.match || j.match.overall_score < filters.minScore)) return false;
      return true;
    });
    return [...list].sort(SORTERS[sortKey]);
  }, [recent_jobs, filters, sortKey]);

  const toggleSelected = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleWindowChange = async (newWindow) => {
    setRefiltering(true);
    try {
      const updated = await getJobs(candidateId, newWindow);
      onResultChange(updated);
    } finally {
      setRefiltering(false);
    }
  };

  const handleMatch = async () => {
    setMatching(true);
    setError(null);
    try {
      const updated = await matchJobs(candidateId, window_days);
      onResultChange(updated);
      notify(`Matched ${updated.recent_jobs.length + updated.unknown_date_jobs.length} jobs against your resume.`, "success");
    } catch (err) {
      setError(err.message);
    } finally {
      setMatching(false);
    }
  };

  const handleContinueToApplications = async () => {
    setSelecting(true);
    setError(null);
    try {
      const updated = await selectJobs(candidateId, [...selectedIds], window_days);
      onResultChange(updated);
      const selectedJobs = [...updated.recent_jobs, ...updated.unknown_date_jobs]
        .filter((j) => j.status === "SELECTED");
      onSelectionApproved(selectedJobs);
    } catch (err) {
      setError(err.message);
    } finally {
      setSelecting(false);
    }
  };

  return (
    <div>
      <h1>Job Results</h1>
      <p className="subtitle">Ranked by match score, best first.</p>

      <div className="funnel">
        <span>{companiesDiscoveredCount} companies discovered</span>
        <span>→</span>
        <span>{totalJobsDiscovered} jobs found</span>
        <span>→</span>
        <span>{recent_jobs.length + unknown_date_jobs.length} within {window_days}-day window</span>
        {alreadyMatched && (
          <>
            <span>→</span>
            <span>{strongMatchCount} strong match{strongMatchCount === 1 ? "" : "es"} (≥{STRONG_MATCH_THRESHOLD}%)</span>
          </>
        )}
      </div>

      <div className="form-section">
        <h3>Posting recency window</h3>
        <div className="radio-group radio-group-row">
          {WINDOW_OPTIONS.map((d) => (
            <label key={d} className="radio-option">
              <input
                type="radio"
                name="resultWindowDays"
                checked={window_days === d}
                disabled={refiltering}
                onChange={() => handleWindowChange(d)}
              />
              {d} days
            </label>
          ))}
        </div>
      </div>

      {companies_skipped.length > 0 && (
        <p className="hint">
          Skipped (no official careers page found, or the page couldn't be read):{" "}
          {companies_skipped.join(", ")}
        </p>
      )}

      {older_jobs_count > 0 && (
        <p className="hint">
          {older_jobs_count} job{older_jobs_count === 1 ? "" : "s"} posted outside this window were
          excluded from the main results below.
        </p>
      )}

      {!alreadyMatched && allJobs.length > 0 && (
        <div className="progress-box">
          <p><strong>Jobs haven't been scored against your resume yet.</strong></p>
          {matching && <SkeletonCards count={3} />}
          {error && <p className="error-text">{error}</p>}
          {!matching && (
            <button className="btn btn-primary" onClick={handleMatch}>
              Match &amp; Rank Against Resume
            </button>
          )}
        </div>
      )}

      {allJobs.length === 0 && (
        <EmptyState icon="🔍" title="We couldn't find strong matches yet">
          <p>Try:</p>
          <ul>
            <li>Expanding your preferred cities</li>
            <li>Including remote roles</li>
            <li>Increasing the experience range</li>
            <li>Allowing AI-suggested roles</li>
          </ul>
          <div className="button-row" style={{ justifyContent: "center" }}>
            <button className="btn btn-secondary" onClick={onRediscover}>Adjust Search</button>
          </div>
        </EmptyState>
      )}

      {allJobs.length > 0 && (
        <div className="results-layout">
          <JobFilters jobs={allJobs} filters={filters} onChange={setFilters} />

          <div>
            <div className="results-header">
              <strong>{filteredRecent.length} job{filteredRecent.length === 1 ? "" : "s"} match your profile</strong>
              <label>
                Sorted by{" "}
                <select className="sort-select" value={sortKey} onChange={(e) => setSortKey(e.target.value)}>
                  <option value="best_match">Best Match</option>
                  <option value="newest">Newest</option>
                  <option value="company">Company Name</option>
                </select>
              </label>
            </div>

            {alreadyMatched && (
              <p className="hint" style={{ marginBottom: 12 }}>
                Check the jobs you'd like to apply to — the agent will not prepare or submit
                applications for anything you don't select.
              </p>
            )}

            {matching ? (
              <SkeletonCards count={4} />
            ) : (
              <div className="job-list">
                {filteredRecent.map((j, i) => (
                  <JobCard
                    j={j}
                    rank={alreadyMatched ? i + 1 : null}
                    key={j.id}
                    selectable={alreadyMatched}
                    checked={selectedIds.has(j.id)}
                    onToggle={toggleSelected}
                    onViewDetails={setDetailsJob}
                    onViewDescription={setDescriptionJob}
                  />
                ))}
              </div>
            )}

            {unknown_date_jobs.length > 0 && (
              <div className="unknown-date-section" style={{ marginTop: 16 }}>
                <button className="btn btn-secondary" onClick={() => setShowUnknown(!showUnknown)}>
                  {showUnknown ? "Hide" : "Show"} {unknown_date_jobs.length} job
                  {unknown_date_jobs.length === 1 ? "" : "s"} with posting date unavailable
                </button>
                {showUnknown && (
                  <div className="job-list" style={{ marginTop: 12 }}>
                    {unknown_date_jobs.map((j) => (
                      <JobCard
                        j={j}
                        key={j.id}
                        selectable={alreadyMatched}
                        checked={selectedIds.has(j.id)}
                        onToggle={toggleSelected}
                        onViewDetails={setDetailsJob}
                        onViewDescription={setDescriptionJob}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {error && alreadyMatched && <p className="error-text">{error}</p>}

      <div className="button-row">
        {alreadyMatched && (
          <button className="btn btn-secondary" onClick={handleMatch} disabled={matching}>
            {matching ? "Re-matching..." : "Re-run Matching"}
          </button>
        )}
        <button className="btn btn-secondary" onClick={onRediscover}>
          Re-run Job Discovery
        </button>
      </div>

      {alreadyMatched && selectedIds.size > 0 && (
        <div className="selection-toolbar">
          <strong>{selectedIds.size} job{selectedIds.size === 1 ? "" : "s"} selected</strong>
          <div className="button-row" style={{ margin: 0 }}>
            <button className="btn btn-secondary" onClick={() => setSelectedIds(new Set())}>
              Clear Selection
            </button>
            <button className="btn btn-primary" onClick={handleContinueToApplications} disabled={selecting}>
              {selecting ? "Saving..." : "Prepare Applications →"}
            </button>
          </div>
        </div>
      )}

      {detailsJob && <MatchDetailsModal job={detailsJob} onClose={() => setDetailsJob(null)} />}
      {descriptionJob && <JobDescriptionModal job={descriptionJob} onClose={() => setDescriptionJob(null)} />}
    </div>
  );
}
