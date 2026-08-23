import { useRef, useState } from "react";
import { uploadResume } from "../api/client";
import { useToast } from "../context/ToastContext";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx"];
const ANALYSIS_STEPS = ["Education", "Experience", "Technical Skills", "Projects", "Certifications", "Potential Job Roles"];

export default function ResumeUpload({ onAnalyzed }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | uploading | error
  const [error, setError] = useState(null);
  const inputRef = useRef(null);
  const notify = useToast();

  const isValidFile = (f) =>
    f && ACCEPTED_EXTENSIONS.some((ext) => f.name.toLowerCase().endsWith(ext));

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    if (!isValidFile(selected)) {
      setError("Only PDF and DOCX resumes are supported.");
      setFile(null);
      return;
    }
    setError(null);
    setFile(selected);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files?.[0];
    if (!dropped) return;
    if (!isValidFile(dropped)) {
      setError("Only PDF and DOCX resumes are supported.");
      return;
    }
    setError(null);
    setFile(dropped);
  };

  const handleSubmit = async () => {
    if (!file) return;
    setStatus("uploading");
    setError(null);
    try {
      const result = await uploadResume(file);
      setStatus("idle");
      notify("Resume analyzed successfully.", "success");
      onAnalyzed(result);
    } catch (err) {
      setStatus("error");
      setError(err.message);
    }
  };

  return (
    <div className="app-main--narrow" style={{ margin: "0 auto", textAlign: "center" }}>
      <h1 style={{ fontSize: "2rem" }}>Find jobs that fit YOU</h1>
      <p className="subtitle" style={{ marginBottom: 28 }}>
        Upload your resume and let your AI career assistant find relevant opportunities —
        no more manually checking hundreds of company career pages.
      </p>

      <div style={{ textAlign: "left" }}>
        <div
          className="dropzone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx"
            onChange={handleFileChange}
            hidden
          />
          <div className="dropzone-icon" aria-hidden="true">📄</div>
          {file ? (
            <p>✓ Resume uploaded<br /><strong>{file.name}</strong></p>
          ) : (
            <>
              <p><strong>Drag &amp; drop your resume here</strong></p>
              <p className="hint">or click to browse — PDF or DOCX</p>
            </>
          )}
        </div>

        {status === "uploading" && (
          <div className="progress-box">
            <p><strong>Analyzing your resume...</strong></p>
            <div className="status-checklist">
              {ANALYSIS_STEPS.map((step) => (
                <div className="status-checklist-item" key={step}>
                  <span className="check-icon active" aria-hidden="true">⟳</span>
                  {step}
                </div>
              ))}
            </div>
            <p className="hint" style={{ marginTop: 10 }}>
              Local models can take a few minutes for a full resume — thanks for your patience.
            </p>
          </div>
        )}

        {error && <p className="error-text">{error}</p>}

        <button
          className="btn btn-primary btn-block"
          style={{ marginTop: 20 }}
          disabled={!file || status === "uploading"}
          onClick={handleSubmit}
        >
          {status === "uploading" ? "Analyzing Resume..." : "Analyze Resume"}
        </button>

        <p className="privacy-note">
          Your resume is used only to build your candidate profile for this session.
          No information is shared externally without your explicit approval.
        </p>
      </div>
    </div>
  );
}
