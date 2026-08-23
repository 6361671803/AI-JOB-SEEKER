import { useState } from "react";
import { approveApplicationPreparation } from "../api/client";
import MatchScoreBadge from "./shared/MatchScoreBadge";
import JobDescriptionModal from "./shared/JobDescriptionModal";

export default function ApplicationApproval({ candidateId, selectedJobs, onBack, onApproved }) {
  const [status, setStatus] = useState("idle"); // idle | approving | approved | error
  const [error, setError] = useState(null);
  const [descriptionJob, setDescriptionJob] = useState(null);

  const handleApprove = async () => {
    setStatus("approving");
    setError(null);
    try {
      const result = await approveApplicationPreparation(candidateId);
      setStatus("approved");
      onApproved(result);
    } catch (err) {
      setStatus("error");
      setError(err.message);
    }
  };

  return (
    <div>
      <h1>Approval #1: Prepare Applications?</h1>
      <p className="subtitle">Confirm the jobs you want your AI assistant to start preparing.</p>

      <p>
        You selected <strong>{selectedJobs.length}</strong> job{selectedJobs.length === 1 ? "" : "s"}.
      </p>

      <div className="job-list">
        {selectedJobs.map((j) => (
          <div className="job-card" key={j.id}>
            <div className="job-card-header">
              <h3>{j.title}</h3>
              {j.match && <MatchScoreBadge score={j.match.overall_score} />}
            </div>
            <p className="company-meta">
              {j.company_name}
              {j.location && <span> · {j.location}</span>}
            </p>
            <div className="company-links">
              <button className="btn-ghost" onClick={() => setDescriptionJob(j)}>Job Description</button>
            </div>
          </div>
        ))}
      </div>

      <div className="approval-notice">
        <p>
          The application agent will now prepare these applications by opening each company's
          official application page and filling in what it can from your resume.
        </p>
        <p>
          <strong>It will NOT submit any application without your approval.</strong> You'll review
          every field before anything is sent — that's Approval #2, later.
        </p>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="button-row">
        <button className="btn btn-primary" onClick={handleApprove} disabled={status === "approving"}>
          {status === "approving" ? "Confirming..." : "Start Application Preparation"}
        </button>
        <button className="btn btn-secondary" onClick={onBack}>
          Back to Job Selection
        </button>
      </div>

      {descriptionJob && <JobDescriptionModal job={descriptionJob} onClose={() => setDescriptionJob(null)} />}
    </div>
  );
}
