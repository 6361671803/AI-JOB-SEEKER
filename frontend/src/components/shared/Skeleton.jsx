export default function SkeletonCards({ count = 3 }) {
  return (
    <div className="job-list" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton skeleton-card" />
      ))}
    </div>
  );
}
