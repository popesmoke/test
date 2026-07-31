import React, { useMemo, useState } from "react";
import { MaterialIcon } from "./components/MaterialIcon.jsx";
import { formatDisplayDate } from "./dateFormat.js";

function relativeTime(iso) {
  if (!iso) return "—";
  const ms = Date.parse(iso);
  if (Number.isNaN(ms)) return "—";
  const diff = Date.now() - ms;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function verdictTone(verdict) {
  const v = String(verdict || "").toLowerCase();
  if (!v || v === "n/a" || v === "pending") return "pending";
  if (v.includes("clean") || v.includes("clear") || v.includes("pass")) return "clean";
  if (v.includes("threat") || v.includes("fail") || v.includes("cheat") || v.includes("ban")) return "threat";
  return "watch";
}

function statusLabel(status, verdict) {
  if (status === "pending") return "Waiting";
  if (status === "expired") return "Expired";
  const tone = verdictTone(verdict);
  if (tone === "clean") return "Clean";
  if (tone === "threat") return "Threat";
  if (tone === "watch") return "Needs review";
  return "Unreviewed";
}

function copyPin(pin) {
  return navigator.clipboard?.writeText(String(pin)).catch(() => {});
}

/** Demo sessions for the landing-page live preview */
export const DEMO_SESSIONS = [
  {
    id: 1042,
    pin: "841251",
    status: "pending",
    created_at: new Date(Date.now() - 4 * 60000).toISOString(),
    reviewer_verdict: null,
  },
  {
    id: 1041,
    pin: "749369",
    status: "completed",
    created_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    completed_at: new Date(Date.now() - 110 * 60000).toISOString(),
    reviewer_verdict: null,
  },
  {
    id: 1040,
    pin: "552018",
    status: "completed",
    created_at: new Date(Date.now() - 5 * 3600000).toISOString(),
    completed_at: new Date(Date.now() - 4.5 * 3600000).toISOString(),
    reviewed_at: new Date(Date.now() - 4 * 3600000).toISOString(),
    reviewer_verdict: "Clean",
  },
  {
    id: 1039,
    pin: "330714",
    status: "completed",
    created_at: new Date(Date.now() - 26 * 3600000).toISOString(),
    completed_at: new Date(Date.now() - 25 * 3600000).toISOString(),
    reviewed_at: new Date(Date.now() - 24 * 3600000).toISOString(),
    reviewer_verdict: "Threat — injector",
  },
  {
    id: 1038,
    pin: "918442",
    status: "expired",
    created_at: new Date(Date.now() - 30 * 3600000).toISOString(),
    expires_at: new Date(Date.now() - 28 * 3600000).toISOString(),
    reviewer_verdict: null,
  },
  {
    id: 1037,
    pin: "661203",
    status: "completed",
    created_at: new Date(Date.now() - 48 * 3600000).toISOString(),
    completed_at: new Date(Date.now() - 47 * 3600000).toISOString(),
    reviewed_at: new Date(Date.now() - 46 * 3600000).toISOString(),
    reviewer_verdict: "Clean",
  },
];

export function OverviewDashboard({
  sessions = [],
  onOpenScan,
  onNewScan,
  demo = false,
  compact = false,
}) {
  const [page, setPage] = useState(0);
  const [copiedId, setCopiedId] = useState(null);
  const pageSize = compact ? 4 : 7;

  const stats = useMemo(() => {
    const completed = sessions.filter((s) => s.status === "completed");
    const pending = sessions.filter((s) => s.status === "pending");
    const expired = sessions.filter((s) => s.status === "expired");
    const threats = completed.filter((s) => verdictTone(s.reviewer_verdict) === "threat");
    const clean = completed.filter((s) => verdictTone(s.reviewer_verdict) === "clean");
    const unreviewed = completed.filter((s) => !s.reviewer_verdict);
    const reviewed = completed.filter((s) => s.reviewer_verdict);
    const reviewRate = completed.length
      ? Math.round((reviewed.length / completed.length) * 100)
      : 0;
    return {
      total: sessions.length,
      pending,
      expired,
      threats,
      clean,
      unreviewed,
      completed,
      reviewRate,
    };
  }, [sessions]);

  const metrics = [
    {
      label: "Total scans",
      value: String(stats.total),
      icon: "radar",
      hint: `${stats.completed.length} completed`,
    },
    {
      label: "Waiting PINs",
      value: String(stats.pending.length),
      icon: "pin",
      hint: "Share during screenshare",
      accent: "warn",
    },
    {
      label: "Needs review",
      value: String(stats.unreviewed.length),
      icon: "report",
      hint: "Completed, no verdict yet",
      accent: "warn",
    },
    {
      label: "Threats flagged",
      value: String(stats.threats.length),
      icon: "shield_alert",
      hint: "Reviewer verdicts",
      accent: "bad",
    },
    {
      label: "Clean verdicts",
      value: String(stats.clean.length),
      icon: "check_circle",
      hint: `${stats.reviewRate}% review rate`,
      accent: "ok",
    },
  ];

  const chartPoints = useMemo(() => {
    const days = Array.from({ length: 7 }, (_, i) => {
      const d = new Date();
      d.setHours(0, 0, 0, 0);
      d.setDate(d.getDate() - (6 - i));
      return d;
    });
    const counts = days.map((day) => {
      const next = new Date(day);
      next.setDate(next.getDate() + 1);
      return sessions.filter((s) => {
        const t = Date.parse(s.completed_at || s.created_at || "");
        return !Number.isNaN(t) && t >= day.getTime() && t < next.getTime();
      }).length;
    });
    const max = Math.max(...counts, 1);
    return counts.map((count, i) => ({
      label: days[i].toLocaleDateString(undefined, { weekday: "short" }),
      count,
      y: 78 - (count / max) * 58,
    }));
  }, [sessions]);

  const linePath = chartPoints
    .map((p, i) => {
      const x = (i / Math.max(chartPoints.length - 1, 1)) * 240;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${p.y.toFixed(1)}`;
    })
    .join(" ");
  const areaPath = `${linePath} L240,90 L0,90 Z`;

  const pageCount = Math.max(1, Math.ceil(sessions.length / pageSize));
  const pageRows = sessions.slice(page * pageSize, page * pageSize + pageSize);

  async function handleCopy(pin, id, event) {
    event?.stopPropagation?.();
    if (demo) return;
    await copyPin(pin);
    setCopiedId(id);
    setTimeout(() => setCopiedId((prev) => (prev === id ? null : prev)), 1400);
  }

  return (
    <section className={`ov${compact ? " ov--compact" : ""}${demo ? " ov--demo" : ""}`}>
      <header className="ov__header">
        <div>
          <h1>Dashboard</h1>
          <p>Your PIN sessions, review queue, and recent verdicts.</p>
        </div>
        <div className="ov__header-actions">
          <button
            type="button"
            className="btn btn--primary btn--sm"
            onClick={onNewScan}
            disabled={demo}
          >
            <MaterialIcon name="add" size={14} color="ffffff" />
            New Scan
          </button>
        </div>
      </header>

      <div className="ov__metrics">
        {metrics.map((m) => (
          <article key={m.label} className={`ov__metric${m.accent ? ` ov__metric--${m.accent}` : ""}`}>
            <div className="ov__metric-icon">
              <MaterialIcon
                name={m.icon}
                size={18}
                color={m.accent === "ok" ? "22c55e" : m.accent === "warn" ? "eab308" : "ef4444"}
              />
            </div>
            <div className="ov__metric-body">
              <span className="ov__metric-label">{m.label}</span>
              <strong>{m.value}</strong>
              <em>{m.hint}</em>
            </div>
          </article>
        ))}
      </div>

      <div className="ov__layout">
        <div className="ov__panel ov__panel--table">
          <div className="ov__panel-head">
            <h2>Recent scans</h2>
            <span className="ov__chip">{sessions.length}</span>
          </div>
          <div className="ov__table-wrap">
            <table className="ov__table">
              <thead>
                <tr>
                  <th>PIN</th>
                  <th>Result</th>
                  <th>Updated</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {pageRows.length ? (
                  pageRows.map((row) => {
                    const tone =
                      row.status === "completed" ? verdictTone(row.reviewer_verdict) : row.status;
                    return (
                      <tr
                        key={row.id}
                        onClick={() => {
                          if (!demo) onOpenScan?.(row.id);
                        }}
                      >
                        <td>
                          <span className="ov__user">
                            <span className="ov__avatar">{String(row.pin || "?").slice(0, 1)}</span>
                            <span>
                              <strong>{row.pin}</strong>
                              <em>#{row.id}</em>
                            </span>
                          </span>
                        </td>
                        <td>
                          <span className={`ov__pill ov__pill--${tone}`}>
                            {statusLabel(row.status, row.reviewer_verdict)}
                          </span>
                        </td>
                        <td>{relativeTime(row.completed_at || row.created_at)}</td>
                        <td>
                          <button
                            type="button"
                            className="ov__icon-btn"
                            title="Copy PIN"
                            onClick={(e) => handleCopy(row.pin, row.id, e)}
                            disabled={demo}
                          >
                            <MaterialIcon
                              name={copiedId === row.id ? "check_circle" : "content_copy"}
                              size={14}
                              color={copiedId === row.id ? "22c55e" : "9aa3b2"}
                            />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={4} className="ov__empty">
                      No scans yet — create a PIN to start a review.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {pageCount > 1 ? (
            <div className="ov__pager">
              {Array.from({ length: Math.min(pageCount, 8) }, (_, i) => (
                <button
                  key={i}
                  type="button"
                  className={i === page ? "is-active" : ""}
                  onClick={() => setPage(i)}
                  disabled={demo}
                >
                  {i + 1}
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div className="ov__rail">
          <div className="ov__panel">
            <div className="ov__panel-head">
              <h2>Waiting for upload</h2>
              <span className="ov__chip">{stats.pending.length}</span>
            </div>
            {stats.pending.length ? (
              <ul className="ov__queue">
                {stats.pending.slice(0, 5).map((s) => (
                  <li key={s.id}>
                    <button
                      type="button"
                      className="ov__queue-main"
                      onClick={() => {
                        if (!demo) onOpenScan?.(s.id);
                      }}
                      disabled={demo}
                    >
                      <strong>{s.pin}</strong>
                      <span>Created {relativeTime(s.created_at)}</span>
                    </button>
                    <button
                      type="button"
                      className="ov__queue-copy"
                      onClick={(e) => handleCopy(s.pin, `p-${s.id}`, e)}
                      disabled={demo}
                    >
                      {copiedId === `p-${s.id}` ? "Copied" : "Copy"}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="ov__blank">No active PINs. Start a new scan when you’re on a call.</p>
            )}
          </div>

          <div className="ov__panel">
            <div className="ov__panel-head">
              <h2>Review queue</h2>
              <span className="ov__chip ov__chip--warn">{stats.unreviewed.length}</span>
            </div>
            {stats.unreviewed.length ? (
              <ul className="ov__queue">
                {stats.unreviewed.slice(0, 5).map((s) => (
                  <li key={s.id}>
                    <button
                      type="button"
                      className="ov__queue-main"
                      onClick={() => {
                        if (!demo) onOpenScan?.(s.id);
                      }}
                      disabled={demo}
                    >
                      <strong>{s.pin}</strong>
                      <span>Completed {relativeTime(s.completed_at)}</span>
                    </button>
                    <span className="ov__pill ov__pill--watch">Open</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="ov__blank">You’re caught up — no unreviewed reports.</p>
            )}
          </div>
        </div>
      </div>

      <div className="ov__bottom">
        <div className="ov__panel ov__panel--chart">
          <div className="ov__panel-head">
            <h2>Scan activity</h2>
            <span className="muted">Last 7 days</span>
          </div>
          <svg className="ov__chart" viewBox="0 0 240 90" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <linearGradient id="ovFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ef4444" stopOpacity="0.35" />
                <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path d={areaPath} fill="url(#ovFill)" />
            <path
              d={linePath}
              fill="none"
              stroke="#ef4444"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {chartPoints.map((p, i) => (
              <circle
                key={p.label}
                cx={(i / Math.max(chartPoints.length - 1, 1)) * 240}
                cy={p.y}
                r="3"
                fill="#ef4444"
              />
            ))}
          </svg>
          <div className="ov__chart-labels">
            {chartPoints.map((p) => (
              <span key={p.label}>
                {p.label}
                <em>{p.count}</em>
              </span>
            ))}
          </div>
        </div>

        <div className="ov__panel">
          <div className="ov__panel-head">
            <h2>Threat verdicts</h2>
          </div>
          {stats.threats.length ? (
            <ul className="ov__threats">
              {stats.threats.slice(0, 5).map((s) => (
                <li key={s.id}>
                  <MaterialIcon name="shield_alert" size={16} color="ef4444" />
                  <div>
                    <strong
                      role={demo ? undefined : "button"}
                      tabIndex={demo ? undefined : 0}
                      onClick={() => {
                        if (!demo) onOpenScan?.(s.id);
                      }}
                      onKeyDown={(e) => {
                        if (!demo && (e.key === "Enter" || e.key === " ")) onOpenScan?.(s.id);
                      }}
                    >
                      {s.pin}
                    </strong>
                    <span>{s.reviewer_verdict}</span>
                  </div>
                  <em>{relativeTime(s.reviewed_at || s.completed_at)}</em>
                </li>
              ))}
            </ul>
          ) : (
            <p className="ov__blank">No threat verdicts yet. Flagged cases will show up here.</p>
          )}
        </div>

        <div className="ov__panel">
          <div className="ov__panel-head">
            <h2>Latest verdicts</h2>
          </div>
          <ul className="ov__completions">
            {stats.completed
              .filter((s) => s.reviewer_verdict)
              .slice(0, 5)
              .map((s) => (
                <li key={s.id}>
                  <span className={`ov__dot ov__dot--${verdictTone(s.reviewer_verdict)}`} />
                  <div>
                    <strong>{s.pin}</strong>
                    <span>{s.reviewer_verdict}</span>
                  </div>
                  <em>{formatDisplayDate(s.reviewed_at || s.completed_at) || relativeTime(s.completed_at)}</em>
                </li>
              ))}
            {!stats.completed.some((s) => s.reviewer_verdict) ? (
              <li className="ov__blank-row">No verdicts recorded yet.</li>
            ) : null}
          </ul>
        </div>
      </div>
    </section>
  );
}
