import EmptyState from "./shared/EmptyState";

export default function CompanyResults({ result, onRediscover, onContinue }) {
  const { companies } = result;

  return (
    <div>
      <h1>Companies Discovered</h1>
      <p className="subtitle">
        Found {companies.length} companies. Next: search these official career pages for current
        job openings.
      </p>

      {companies.length === 0 ? (
        <EmptyState icon="🏢" title="No companies found yet">
          <p>No companies were confidently identified from the search results.</p>
          <ul>
            <li>Try broadening your preferred cities</li>
            <li>Allow remote roles if you haven't</li>
            <li>Let AI suggest roles instead of a specific title</li>
          </ul>
        </EmptyState>
      ) : (
        <div className="job-list">
          {companies.map((c) => (
            <div className="job-card" key={c.id}>
              <h3>{c.name}</h3>
              <p className="company-meta">
                {c.discovery_role && <span>{c.discovery_role}</span>}
                {c.discovery_role && c.discovery_location && <span> · </span>}
                {c.discovery_location && <span>{c.discovery_location}</span>}
              </p>
              <div className="company-links">
                {c.website ? (
                  <a href={c.website} target="_blank" rel="noreferrer">Official Website</a>
                ) : (
                  <span className="unknown">Official website not confidently found</span>
                )}
                {c.careers_url ? (
                  <a href={c.careers_url} target="_blank" rel="noreferrer">Careers Page</a>
                ) : (
                  <span className="unknown">Careers page not confidently found</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="button-row">
        <button className="btn btn-primary" onClick={onContinue}>
          Continue to Job Discovery
        </button>
        <button className="btn btn-secondary" onClick={onRediscover}>
          Re-run Discovery
        </button>
      </div>
    </div>
  );
}
