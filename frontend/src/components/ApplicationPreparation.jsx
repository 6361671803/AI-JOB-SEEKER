import { useState } from "react";
import { markSubmitted, prepareApplication, screenshotUrl } from "../api/client";
import { useToast } from "../context/ToastContext";

function FinalReview({ candidateId, prep, onUpdate }) {
  const [reviewed, setReviewed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const notify = useToast();

  const handleMarkSubmitted = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const updated = await markSubmitted(candidateId, prep.job_id);
      onUpdate(updated);
      notify("Application tracked as submitted.", "success");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const isSubmitted = prep.status === "SUBMITTED";

  return (
    <div className="prep-result">
      <p className="prep-ready-banner">
        {isSubmitted ? "✓ Marked as Submitted" : "Application Ready for Review"}
      </p>
      <p className="job-meta">Platform detected: {prep.platform}</p>
      <p className="job-meta">{prep.message}</p>

      <div className="field-check-grid">
        <div className="field-check-row">
          <span>Application page opened</span>
          <span className={`field-check-status ${prep.status === "FAILED" ? "warn" : "ok"}`}>
            {prep.status === "FAILED" ? "⚠ Could not open" : "✓ Yes"}
          </span>
        </div>
        <div className="field-check-row">
          <span>Screenshot captured</span>
          <span className={`field-check-status ${prep.screenshot_available ? "ok" : "warn"}`}>
            {prep.screenshot_available ? "✓ Yes" : "⚠ Not available"}
          </span>
        </div>
      </div>

      {prep.screenshot_available && (
        <div className="prep-screenshot-wrap">
          <p className="hint">Screenshot of the official application page (nothing was submitted):</p>
          <img
            className="prep-screenshot"
            src={screenshotUrl(candidateId, prep.job_id)}
            alt={`Application page preview for ${prep.title}`}
          />
        </div>
      )}

      {prep.application_url && (
        <p>
          <a href={prep.application_url} target="_blank" rel="noreferrer">
            Open Official Application Page to Review &amp; Submit
          </a>
        </p>
      )}

      {error && <p className="error-text">{error}</p>}

      {!isSubmitted ? (
        <div className="approval-notice">
          <p style={{ fontWeight: 650 }}>IMPORTANT — the application has NOT been submitted.</p>
          <label className="radio-option">
            <input type="checkbox" checked={reviewed} onChange={(e) => setReviewed(e.target.checked)} />
            I have reviewed this application.
          </label>
          <p className="hint">
            This app never submits anything for you (Approval #2). Go apply on the official page
            above, then come back and confirm here so it's tracked correctly.
          </p>
          <button
            className="btn btn-primary"
            onClick={handleMarkSubmitted}
            disabled={!reviewed || submitting}
          >
            {submitting ? "Saving..." : "I've Submitted This Application"}
          </button>
        </div>
      ) : (
        <p className="unknown">This application is tracked as submitted.</p>
      )}
    </div>
  );
}

export default function ApplicationPreparation({ candidateId, selectedJobs }) {
  const [preparations, setPreparations] = useState({});
  const [preparingId, setPreparingId] = useState(null);
  const [errors, setErrors] = useState({});

  const handlePrepare = async (jobId) => {
    setPreparingId(jobId);
    setErrors((prev) => ({ ...prev, [jobId]: null }));
    try {
      const result = await prepareApplication(candidateId, jobId);
      setPreparations((prev) => ({ ...prev, [jobId]: result }));
    } catch (err) {
      setErrors((prev) => ({ ...prev, [jobId]: err.message }));
    } finally {
      setPreparingId(null);
    }
  };

  const handleUpdate = (jobId, updated) => {
    setPreparations((prev) => ({ ...prev, [jobId]: updated }));
  };

  return (
    <div>
      <h1>Application Preparation &amp; Final Review</h1>
      <p className="subtitle">Nothing is ever submitted automatically. You review and submit yourself.</p>

      <div className="job-list">
        {selectedJobs.map((job) => {
          const prep = preparations[job.id];
          return (
            <div className="job-card" key={job.id}>
              <h3>{job.title}</h3>
              <p className="company-meta">
                {job.company_name}
                {job.location && <span> · {job.location}</span>}
              </p>

              {!prep && (
                <>
                  <button
                    className="btn btn-primary"
                    onClick={() => handlePrepare(job.id)}
                    disabled={preparingId === job.id}
                  >
                    {preparingId === job.id ? "Preparing..." : "Prepare Application"}
                  </button>
                  {preparingId === job.id && (
                    <p className="hint">Opening the official application page and taking a screenshot...</p>
                  )}
                </>
              )}

              {errors[job.id] && <p className="error-text">{errors[job.id]}</p>}

              {prep && (
                <FinalReview
                  candidateId={candidateId}
                  prep={prep}
                  onUpdate={(updated) => handleUpdate(job.id, updated)}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
