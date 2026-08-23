function uniqueSorted(values) {
  return [...new Set(values.filter(Boolean))].sort();
}

export default function JobFilters({ jobs, filters, onChange }) {
  const locations = uniqueSorted(jobs.map((j) => j.location));
  const workModes = uniqueSorted(jobs.map((j) => j.work_mode));

  const toggleSetValue = (key, value) => {
    const current = filters[key];
    const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
    onChange({ ...filters, [key]: next });
  };

  return (
    <div className="filters-panel" aria-label="Job filters">
      {locations.length > 0 && (
        <>
          <h4>Location</h4>
          <div className="filter-checkbox-list">
            {locations.map((loc) => (
              <label className="filter-checkbox" key={loc}>
                <input
                  type="checkbox"
                  checked={filters.locations.includes(loc)}
                  onChange={() => toggleSetValue("locations", loc)}
                />
                {loc}
              </label>
            ))}
          </div>
        </>
      )}

      {workModes.length > 0 && (
        <>
          <h4>Work Mode</h4>
          <div className="filter-checkbox-list">
            {workModes.map((mode) => (
              <label className="filter-checkbox" key={mode}>
                <input
                  type="checkbox"
                  checked={filters.workModes.includes(mode)}
                  onChange={() => toggleSetValue("workModes", mode)}
                />
                {mode}
              </label>
            ))}
          </div>
        </>
      )}

      <h4>Minimum Match Score</h4>
      <input
        type="range"
        min="0"
        max="100"
        step="5"
        value={filters.minScore}
        onChange={(e) => onChange({ ...filters, minScore: Number(e.target.value) })}
        style={{ width: "100%" }}
        aria-label="Minimum match score"
      />
      <p className="hint">{filters.minScore}% and above</p>

      {(filters.locations.length > 0 || filters.workModes.length > 0 || filters.minScore > 0) && (
        <button
          className="btn-ghost"
          onClick={() => onChange({ locations: [], workModes: [], minScore: 0 })}
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
