export default function Stepper({ steps, currentIndex }) {
  return (
    <div className="stepper" role="list" aria-label="Progress">
      {steps.map((label, i) => (
        <span key={label} style={{ display: "contents" }}>
          <span
            role="listitem"
            className={`stepper-step ${i === currentIndex ? "active" : i < currentIndex ? "done" : ""}`}
          >
            <span className="stepper-dot">{i < currentIndex ? "✓" : i + 1}</span>
            {label}
          </span>
          {i < steps.length - 1 && <span className="stepper-sep" aria-hidden="true" />}
        </span>
      ))}
    </div>
  );
}
