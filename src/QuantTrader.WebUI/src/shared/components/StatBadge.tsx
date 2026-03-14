interface StatBadgeProps {
  label: string;
  value: string;
  tone?: "default" | "positive" | "warning";
}

export function StatBadge({ label, value, tone = "default" }: StatBadgeProps) {
  return (
    <div className={`stat-badge tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
