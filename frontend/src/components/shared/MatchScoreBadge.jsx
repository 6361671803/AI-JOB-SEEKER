export function scoreTier(score) {
  if (score >= 85) return { cls: "score-strong", label: "Excellent Match" };
  if (score >= 70) return { cls: "score-moderate", label: "Strong Match" };
  return { cls: "score-weak", label: "Potential Match" };
}

export default function MatchScoreBadge({ score }) {
  const { cls, label } = scoreTier(score);
  return (
    <div className={`match-score-badge ${cls}`} title={label}>
      <span className="score-num">{score}%</span>
      <span className="score-label">{label}</span>
    </div>
  );
}
