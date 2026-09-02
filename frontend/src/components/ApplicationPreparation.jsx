import { useState } from "react";
import { prepareApplication, screenshotUrl } from "../api/client";

function FinalReview({ candidateId, prep }) {
  return (
    <div className="prep-result">
      <p className="prep-ready-banner">Application Ready for Review</p>
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

      <div className="approval-notice">
        <p style={{ fontWeight: 650 }}>IMPORTANT — this app never submits anything for you.</p>
        <p className="hint">
          Go apply on the official page above yourself. This app does not track whether or when
          you actually submit it.
        </p>
      </div>
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

              {prep && <FinalReview candidateId={candidateId} prep={prep} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
