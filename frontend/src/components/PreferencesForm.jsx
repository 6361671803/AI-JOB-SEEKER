import { useState } from "react";
import { submitPreferences } from "../api/client";
import Stepper from "./shared/Stepper";

const EXPERIENCE_LEVELS = ["Internship", "Fresher", "Entry Level", "0-2 years", "2-5 years", "5+ years", "Any"];

const ROLE_SUGGESTIONS = [
  "AI Engineer", "ML Engineer", "Software Engineer", "Data Scientist", "Data Analyst",
  "Backend Developer", "Frontend Developer", "Full Stack Developer", "Cloud Engineer", "DevOps",
  "Cybersecurity", "Business Analyst", "Finance", "Marketing", "HR", "Operations", "Design", "Sales",
];

const WORK_MODE_OPTIONS = [
  { value: "INDIA", icon: "🇮🇳", title: "India", desc: "On-site / Hybrid" },
  { value: "REMOTE", icon: "🌐", title: "Remote", desc: "Work From Home" },
  { value: "BOTH", icon: "✦", title: "Both", desc: "India + Remote" },
];

const STEPS = ["Location", "Experience", "Role", "Review"];

export default function PreferencesForm({ candidateId, onSaved }) {
  const [wizardStep, setWizardStep] = useState(0);
  const [workMode, setWorkMode] = useState(null);
  const [cityInput, setCityInput] = useState("");
  const [cities, setCities] = useState([]);
  const [experienceLevel, setExperienceLevel] = useState(null);
  const [preferredRole, setPreferredRole] = useState("");
  const [aiSuggested, setAiSuggested] = useState(false);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  const showCities = workMode === "INDIA" || workMode === "BOTH";

  const addCity = () => {
    const value = cityInput.trim();
    if (!value) return;
    if (!cities.some((c) => c.toLowerCase() === value.toLowerCase())) {
      setCities([...cities, value]);
    }
    setCityInput("");
  };

  const removeCity = (city) => setCities(cities.filter((c) => c !== city));

  const canProceedFromLocation = !!workMode;
  const canProceedFromExperience = !!experienceLevel;

  const handleSubmit = async () => {
    setStatus("saving");
    setError(null);
    try {
      const result = await submitPreferences(candidateId, {
        work_mode: workMode,
        cities: showCities ? cities : [],
        experience_level: experienceLevel,
        preferred_role: aiSuggested ? null : (preferredRole || null),
      });
      setStatus("idle");
      onSaved(result);
    } catch (err) {
      setStatus("error");
      setError(err.message);
    }
  };

  return (
    <div className="app-main--narrow" style={{ margin: "0 auto" }}>
      <h1>Your Preferences</h1>
      <p className="subtitle">Tell us where and what you're looking for.</p>

      <Stepper steps={STEPS} currentIndex={wizardStep} />

      {wizardStep === 0 && (
        <div className="form-section">
          <h3>Where do you want to work?</h3>
          <div className="choice-grid">
            {WORK_MODE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`choice-card ${workMode === opt.value ? "selected" : ""}`}
                onClick={() => setWorkMode(opt.value)}
              >
                <span className="choice-card-icon" aria-hidden="true">{opt.icon}</span>
                <span className="choice-card-title">{opt.title}</span>
                <span className="choice-card-desc">{opt.desc}</span>
              </button>
            ))}
          </div>

          {showCities && (
            <div style={{ marginTop: 24 }}>
              <h3>Which cities are you interested in?</h3>
              <p className="hint">Leave blank for any city in India. Type a city and press Enter.</p>
              <div className="city-input-row">
                <input
                  type="text"
                  value={cityInput}
                  placeholder="e.g. Hyderabad, Bengaluru, Pune..."
                  onChange={(e) => setCityInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addCity();
                    }
                  }}
                />
                <button type="button" onClick={addCity}>Add</button>
              </div>
              {cities.length > 0 && (
                <div className="chip-list">
                  {cities.map((city) => (
                    <span className="chip" key={city}>
                      {city}
                      <button type="button" onClick={() => removeCity(city)} aria-label={`Remove ${city}`}>×</button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="button-row">
            <button className="btn btn-primary" disabled={!canProceedFromLocation} onClick={() => setWizardStep(1)}>
              Continue
            </button>
          </div>
        </div>
      )}

      {wizardStep === 1 && (
        <div className="form-section">
          <h3>What's your experience level?</h3>
          <div className="choice-grid">
            {EXPERIENCE_LEVELS.map((level) => (
              <button
                key={level}
                type="button"
                className={`choice-card ${experienceLevel === level ? "selected" : ""}`}
                onClick={() => setExperienceLevel(level)}
              >
                <span className="choice-card-title">{level}</span>
              </button>
            ))}
          </div>
          <div className="button-row">
            <button className="btn btn-secondary" onClick={() => setWizardStep(0)}>Back</button>
            <button className="btn btn-primary" disabled={!canProceedFromExperience} onClick={() => setWizardStep(2)}>
              Continue
            </button>
          </div>
        </div>
      )}

      {wizardStep === 2 && (
        <div className="form-section">
          <h3>What type of role are you looking for? <span className="optional-tag">(optional)</span></h3>
          <p className="hint">Skip if you're not sure — pick "AI suggested roles" and we'll infer from your resume.</p>

          <div className="chip-choice-grid">
            {ROLE_SUGGESTIONS.map((role) => (
              <button
                key={role}
                type="button"
                className={`chip-choice ${!aiSuggested && preferredRole === role ? "selected" : ""}`}
                onClick={() => { setAiSuggested(false); setPreferredRole(role); }}
              >
                {role}
              </button>
            ))}
          </div>

          <div style={{ marginTop: 16 }}>
            <input
              type="text"
              placeholder="Or type a custom role..."
              value={aiSuggested ? "" : preferredRole}
              disabled={aiSuggested}
              onChange={(e) => { setAiSuggested(false); setPreferredRole(e.target.value); }}
            />
          </div>

          <div style={{ marginTop: 16 }}>
            <button
              type="button"
              className={`chip-choice ${aiSuggested ? "selected" : ""}`}
              onClick={() => { setAiSuggested(true); setPreferredRole(""); }}
            >
              ✦ I'm open to roles suggested by AI
            </button>
          </div>

          <div className="button-row">
            <button className="btn btn-secondary" onClick={() => setWizardStep(1)}>Back</button>
            <button className="btn btn-primary" onClick={() => setWizardStep(3)}>Continue</button>
          </div>
        </div>
      )}

      {wizardStep === 3 && (
        <div className="form-section">
          <h3>Your Job Search Summary</h3>
          <div className="surface-card" style={{ padding: 20 }}>
            <div className="profile-field">
              <h3>Location</h3>
              <p>{WORK_MODE_OPTIONS.find((o) => o.value === workMode)?.title}</p>
            </div>
            {showCities && (
              <div className="profile-field">
                <h3>Cities</h3>
                <p>{cities.length ? cities.join(", ") : "Any city in India"}</p>
              </div>
            )}
            <div className="profile-field">
              <h3>Experience</h3>
              <p>{experienceLevel}</p>
            </div>
            <div className="profile-field">
              <h3>Role</h3>
              <p>{aiSuggested ? "AI-suggested roles based on your resume" : (preferredRole || "Not specified — AI will infer from your resume")}</p>
            </div>
            <div className="profile-field">
              <h3>Job Freshness</h3>
              <p>Last 30 days (adjustable later)</p>
            </div>
          </div>

          {error && <p className="error-text">{error}</p>}

          <div className="button-row">
            <button className="btn btn-secondary" onClick={() => setWizardStep(2)}>Back</button>
            <button className="btn btn-primary" onClick={handleSubmit} disabled={status === "saving"}>
              {status === "saving" ? "Saving..." : "Start AI Job Search"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
