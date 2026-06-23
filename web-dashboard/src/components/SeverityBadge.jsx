import { MaterialIcon } from "./MaterialIcon.jsx";

const SEVERITY_META = {
  critical: { label: "Critical", tone: "critical", icon: "shield_alert" },
  high: { label: "High", tone: "high", icon: "alert_triangle" },
  medium: { label: "Medium", tone: "medium", icon: "alert_circle" },
  low: { label: "Low", tone: "low", icon: "info" },
};

export function SeverityBadge({ severity, compact = false, showIcon = true }) {
  const key = String(severity || "medium").toLowerCase();
  const meta = SEVERITY_META[key] || SEVERITY_META.medium;

  return (
    <span
      className={`sev-badge sev-badge--${meta.tone}${compact ? " sev-badge--compact" : ""}`}
      title={meta.label}
    >
      {showIcon ? (
        <MaterialIcon name={meta.icon} size={compact ? 12 : 14} className="sev-badge__icon" />
      ) : (
        <span className="sev-badge__dot" aria-hidden />
      )}
      {!compact ? <span className="sev-badge__label">{meta.label}</span> : null}
    </span>
  );
}

export function severityRank(severity) {
  const ranks = { critical: 0, high: 1, medium: 2, low: 3 };
  return ranks[String(severity || "").toLowerCase()] ?? 9;
}
