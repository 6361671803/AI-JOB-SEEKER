import { useEffect } from "react";

function Section({ title, children }) {
  return (
    <div style={{ marginTop: 16 }}>
      <h3 style={{ fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.03em", color: "var(--text-faint)", marginBottom: 6 }}>
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function JobDescriptionModal({ job, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-label={`Job description for ${job.title}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <h2>{job.title}</h2>
            <p className="subtitle">
              {job.company_name}
              {job.location && <span> · {job.location}</span>}
              {job.work_mode && <span> · {job.work_mode}</span>}
            </p>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="funnel" style={{ marginTop: 0 }}>
          <span>Posted</span>
          <span>{job.date_posted || "Posting date unavailable"}</span>
          {job.employment_type && (<><span>·</span><span>{job.employment_type}</span></>)}
        </div>

        {job.experience_requirement && (
          <Section title="Experience Requirement">
            <p>{job.experience_requirement}</p>
          </Section>
        )}

        {job.education_requirement && (
          <Section title="Education Requirement">
            <p>{job.education_requirement}</p>
          </Section>
        )}

        {job.responsibilities && (
          <Section title="Responsibilities">
            <p style={{ whiteSpace: "pre-wrap" }}>{job.responsibilities}</p>
          </Section>
        )}

        {job.qualifications && (
          <Section title="Qualifications">
            <p style={{ whiteSpace: "pre-wrap" }}>{job.qualifications}</p>
          </Section>
        )}

        {job.required_skills?.length > 0 && (
          <Section title="Required Skills">
            <div className="tag-list">
              {job.required_skills.map((s, i) => <span className="tag" key={i}>{s}</span>)}
            </div>
          </Section>
        )}

        {job.preferred_skills?.length > 0 && (
          <Section title="Preferred Skills">
            <div className="tag-list">
              {job.preferred_skills.map((s, i) => <span className="tag" key={i}>{s}</span>)}
            </div>
          </Section>
        )}

        {!job.responsibilities && !job.qualifications && !job.experience_requirement && !job.education_requirement && (
          <p className="unknown" style={{ marginTop: 16 }}>
            No detailed description was found on this job's listing page — check the official
            posting for full details.
          </p>
        )}

        <div style={{ marginTop: 20 }}>
          {job.job_url ? (
            <a href={job.job_url} target="_blank" rel="noreferrer">View Official Job Posting</a>
          ) : (
            <span className="unknown">Job page link not found</span>
          )}
        </div>
      </div>
    </div>
  );
}
