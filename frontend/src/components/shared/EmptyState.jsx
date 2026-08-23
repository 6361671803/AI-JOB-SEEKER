export default function EmptyState({ icon = "○", title, children, action }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon" aria-hidden="true">{icon}</div>
      <h3>{title}</h3>
      {children}
      {action}
    </div>
  );
}
