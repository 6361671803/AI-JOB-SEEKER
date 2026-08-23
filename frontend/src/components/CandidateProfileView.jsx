function TagField({ label, items }) {
  return (
    <div className="profile-field">
      <h3>{label}</h3>
      {items && items.length > 0 ? (
        <div className="tag-list">
          {items.map((item, i) => <span className="tag" key={i}>{item}</span>)}
        </div>
      ) : (
        <p className="unknown">Not found in resume</p>
      )}
    </div>
  );
}

function ListField({ label, items }) {
  if (!items || items.length === 0) {
    return (
      <div className="profile-field">
        <h3>{label}</h3>
        <p className="unknown">Not found in resume</p>
      </div>
    );
  }
  return (
    <div className="profile-field">
      <h3>{label}</h3>
      <ul>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default function CandidateProfileView({ candidate, onStartOver, onContinue }) {
  const { profile } = candidate;

  return (
    <div className="app-main--narrow" style={{ margin: "0 auto" }}>
      <h1>Your Career Profile</h1>
      <p className="subtitle">
        Extracted from <strong>{candidate.resume_filename}</strong> — nothing here was inferred
        beyond what your resume actually states.
      </p>

      <div className="surface-card" style={{ padding: 24, marginTop: 20 }}>
        <div className="profile-summary">
          <div className="profile-field">
            <h3>Name</h3>
            <p>{profile.name || <span className="unknown">Not found in resume</span>}</p>
          </div>
          <div className="profile-field">
            <h3>Years of Experience</h3>
            <p>
              {profile.years_of_experience !== null && profile.years_of_experience !== undefined
                ? profile.years_of_experience
                : <span className="unknown">Not determinable from resume</span>}
            </p>
          </div>
          <div className="profile-field">
            <h3>Contact</h3>
            <p>{profile.email || <span className="unknown">No email found</span>}</p>
            <p>{profile.phone || <span className="unknown">No phone found</span>}</p>
          </div>
        </div>

        <TagField label="Skills" items={profile.skills} />
        <TagField label="Technologies" items={profile.technologies} />
        <TagField label="Potential Roles" items={profile.roles} />
        <TagField label="Certifications" items={profile.certifications} />
        <TagField label="Known Locations" items={profile.locations} />

        <div className="profile-field">
          <h3>Education</h3>
          {profile.education?.length ? (
            <ul>
              {profile.education.map((e, i) => (
                <li key={i}>
                  {[e.degree, e.field_of_study, e.institution, e.year].filter(Boolean).join(" — ") || "Unspecified entry"}
                </li>
              ))}
            </ul>
          ) : (
            <p className="unknown">Not found in resume</p>
          )}
        </div>

        <ListField
          label="Experience"
          items={profile.experience?.map((e) => [e.title, e.company, e.duration].filter(Boolean).join(" — ") || "Unspecified entry")}
        />

        <ListField
          label="Projects"
          items={profile.projects?.map((p) => `${p.name || "Unnamed project"}${p.technologies?.length ? ` (${p.technologies.join(", ")})` : ""}`)}
        />
      </div>

      <div className="button-row">
        <button className="btn btn-primary" onClick={onContinue}>
          Continue to Preferences
        </button>
        <button className="btn btn-secondary" onClick={onStartOver}>
          Upload a Different Resume
        </button>
      </div>
    </div>
  );
}
