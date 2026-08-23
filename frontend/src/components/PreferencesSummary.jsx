const WORK_MODE_LABELS = {
  INDIA: "India",
  REMOTE: "Work From Home / Remote",
  BOTH: "India + Remote",
};

export default function PreferencesSummary({ preferences, onEdit, onContinue }) {
  const p = preferences;

  return (
    <div className="app-main--narrow" style={{ margin: "0 auto" }}>
      <h1>Preferences Saved</h1>
      <p className="subtitle">Here's what your AI assistant will search for.</p>

      <div className="surface-card" style={{ padding: 24, marginTop: 20 }}>
        <div className="profile-field">
          <h3>Work Mode</h3>
          <p>{WORK_MODE_LABELS[p.work_mode]}</p>
        </div>

        {(p.work_mode === "INDIA" || p.work_mode === "BOTH") && (
          <div className="profile-field">
            <h3>Cities</h3>
            <p>{p.cities.length ? p.cities.join(", ") : "Any city in India"}</p>
          </div>
        )}

        <div className="profile-field">
          <h3>Experience Level</h3>
          <p>{p.experience_level}</p>
        </div>

        <div className="profile-field">
          <h3>Role</h3>
          {p.role_source === "user" ? (
            <p>{p.preferred_role}</p>
          ) : (
            <>
              <p className="unknown">No role specified — your AI assistant inferred these from your resume:</p>
              {p.inferred_roles.length ? (
                <div className="tag-list" style={{ marginTop: 6 }}>
                  {p.inferred_roles.map((role) => <span className="tag" key={role}>{role}</span>)}
                </div>
              ) : (
                <p className="unknown">Could not infer suitable roles from the resume.</p>
              )}
            </>
          )}
        </div>
      </div>

      <div className="button-row">
        <button className="btn btn-primary" onClick={onContinue}>
          Start AI Company Search
        </button>
        <button className="btn btn-secondary" onClick={onEdit}>
          Edit Preferences
        </button>
      </div>
    </div>
  );
}
