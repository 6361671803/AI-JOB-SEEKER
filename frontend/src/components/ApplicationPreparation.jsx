import { useState } from "react";
import { prepareApplication, screenshotUrl, updateReviewFields } from "../api/client";

function categorize(field) {
  if (field.filled && (field.source === "resume" || field.source === "resume_file")) return "resume";
  if (field.filled && field.source === "user_provided") return "user";
  if (!field.filled && (field.source === "unrecognized_field" || field.source === "could_not_fill")) return "uncertain";
  return "missing"; // missing_from_resume, no_resume_file_available, requires_your_input
}

function EditableField({ field, draft, onDraftChange, onSave, saving }) {
  return (
    <div className="review-editable-field">
      <label>
        <strong>{field.label}</strong>
        <span className="hint"> — {(field.source || "unknown").replace(/_/g, " ")}</span>
      </label>
      <div className="review-editable-row">
        <input
          type="text"
          value={draft}
          placeholder="Type your own answer (for your reference only)"
          onChange={(e) => onDraftChange(field.label, e.target.value)}
        />
        <button className="btn btn-secondary" onClick={() => onSave(field.label)} disabled={saving || !draft}>
          Save
        </button>
      </div>
    </div>
  );
}

function FinalReview({ candidateId, prep, onUpdate }) {
  const [drafts, setDrafts] = useState({});
  const [savingLabel, setSavingLabel] = useState(null);
  const [error, setError] = useState(null);

  const byCategory = { resume: [], user: [], missing: [], uncertain: [] };
  for (const f of prep.fields) byCategory[categorize(f)].push(f);
  const resumeAttached = prep.fields.some((f) => f.field_type === "resume_upload" && f.filled);
  const needsReview = byCategory.missing.length + byCategory.uncertain.length;

  const handleSaveDraft = async (label) => {
    setSavingLabel(label);
    setError(null);
    try {
      const updated = await updateReviewFields(candidateId, prep.job_id, { [label]: drafts[label] });
      onUpdate(updated);
      setDrafts((prev) => ({ ...prev, [label]: "" }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingLabel(null);
    }
  };

  return (
    <div className="prep-result">
      <p className="prep-ready-banner">Application Ready for Review</p>
      <p className="job-meta">Platform detected: {prep.platform}</p>
      <p className="job-meta">{prep.message}</p>

      <div className="field-check-grid">
        <div className="field-check-row">
          <span>Application page found</span>
          <span className="field-check-status ok">✓ Yes</span>
        </div>
        <div className="field-check-row">
          <span>Resume attached</span>
          <span className={`field-check-status ${resumeAttached ? "ok" : "warn"}`}>
            {resumeAttached ? "✓ Yes" : "⚠ Attach manually"}
          </span>
        </div>
        <div className="field-check-row">
          <span>Fields auto-filled from resume</span>
          <span className="field-check-status ok">{byCategory.resume.length + byCategory.user.length}</span>
        </div>
        <div className="field-check-row">
          <span>Fields needing your review</span>
          <span className={`field-check-status ${needsReview ? "warn" : "ok"}`}>{needsReview}</span>
        </div>
      </div>

      {prep.fields.length > 0 && (
        <div className="review-categories">
          <div className="review-category">
            <h4>Resume-derived ({byCategory.resume.length})</h4>
            {byCategory.resume.length === 0 ? (
              <p className="unknown">None</p>
            ) : (
              byCategory.resume.map((f, i) => (
                <p key={i} className="field-filled">✓ <strong>{f.label}:</strong> {f.value}</p>
              ))
            )}
          </div>

          <div className="review-category">
            <h4>AI-generated (0)</h4>
            <p className="unknown">None — this agent never invents answers on your behalf.</p>
          </div>

          <div className="review-category">
            <h4>Your own answers ({byCategory.user.length})</h4>
            {byCategory.user.length === 0 ? (
              <p className="unknown">None yet</p>
            ) : (
              byCategory.user.map((f, i) => (
                <p key={i} className="field-filled">✓ <strong>{f.label}:</strong> {f.value}</p>
              ))
            )}
          </div>

          {byCategory.missing.length > 0 && (
            <div className="review-category">
              <h4>Missing — needs your input ({byCategory.missing.length})</h4>
              {byCategory.missing.map((f, i) => (
                <EditableField
                  key={i}
                  field={f}
                  draft={drafts[f.label] || ""}
                  onDraftChange={(label, v) => setDrafts((prev) => ({ ...prev, [label]: v }))}
                  onSave={handleSaveDraft}
                  saving={savingLabel === f.label}
                />
              ))}
            </div>
          )}

          {byCategory.uncertain.length > 0 && (
            <div className="review-category">
              <h4>Uncertain / unrecognized ({byCategory.uncertain.length})</h4>
              {byCategory.uncertain.map((f, i) => (
                <EditableField
                  key={i}
                  field={f}
                  draft={drafts[f.label] || ""}
                  onDraftChange={(label, v) => setDrafts((prev) => ({ ...prev, [label]: v }))}
                  onSave={handleSaveDraft}
                  saving={savingLabel === f.label}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {prep.screenshot_available && (
        <div className="prep-screenshot-wrap">
          <p className="hint">Screenshot of the form as filled (nothing was submitted):</p>
          <img
            className="prep-screenshot"
            src={screenshotUrl(candidateId, prep.job_id)}
            alt={`Filled application preview for ${prep.title}`}
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

      <div className="approval-notice">
        <p style={{ fontWeight: 650 }}>IMPORTANT — the application has NOT been submitted.</p>
        <p className="hint">
          This app never submits anything for you, and does not track whether you go on to submit
          it. Review every field above, attach your resume if it isn't already, then open the
          official application page and submit it yourself.
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
                    <p className="hint">Opening the official application page and mapping your resume to its fields...</p>
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
