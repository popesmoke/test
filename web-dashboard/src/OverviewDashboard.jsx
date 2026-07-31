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
  if (status === "pending") return "Pending";
  if (status === "expired") return "Expired";
  const tone = verdictTone(verdict);
  if (tone === "clean") return "Clean";
  if (tone === "threat") return "Threat Detected";
  if (tone === "watch") return "Needs Review";
  return "Completed";
}

export function OverviewDashboard({ sessions = [], onOpenScan, onNewScan }) {
  const [page, setPage] = useState(0);
  const pageSize = 6;

  const metrics = useMemo(() => {
    const total = sessions.length;
    const completed = sessions.filter((s) => s.status === "completed");
    const pending = sessions.filter((s) => s.status === "pending");
    const expired = sessions.filter((s) => s.status === "expired");
    const threats = completed.filter((s) => verdictTone(s.reviewer_verdict) === "threat").length;
    const clean = completed.filter((s) => verdictTone(s.reviewer_verdict) === "clean").length;
    const reviewed = completed.filter((s) => s.reviewer_verdict).length;
    const successRate = completed.length ? Math.round((reviewed / completed.length) * 1000) / 10 : 100;
    return [
      { label: "Total Scans", value: total.toLocaleString(), icon: "radar", hint: `${pending.length} pending` },
      { label: "Threats Flagged", value: threats.toLocaleString(), icon: "shield_alert", hint: "From reviewer verdicts" },
      { label: "Active PINs", value: pending.toLocaleString(), icon: "pin", hint: "Awaiting upload" },
      { label: "Clean Verdicts", value: clean.toLocaleString(), icon: "check_circle", hint: "Marked clean", ok: true },
      { label: "Review Rate", value: `${successRate}%`, icon: "speed", hint: "Completed with verdict", ok: true },
    ];
  }, [sessions]);

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
      y: 70 - (count / max) * 52,
    }));
  }, [sessions]);

  const alerts = useMemo(() => {
    const items = [];
    sessions.slice(0, 40).forEach((s) => {
      if (verdictTone(s.reviewer_verdict) === "threat") {
        items.push({
          id: `t-${s.id}`,
          title: "Threat verdict recorded",
          detail: `PIN ${s.pin} marked ${s.reviewer_verdict}`,
          time: relativeTime(s.reviewed_at || s.completed_at),
          tone: "bad",
          icon: "shield_alert",
        });
      } else if (s.status === "expired") {
        items.push({
          id: `e-${s.id}`,
          title: "Session expired",
          detail: `PIN ${s.pin} timed out without results`,
          time: relativeTime(s.expires_at || s.created_at),
          tone: "warn",
          icon: "alert_triangle",
        });
      } else if (s.status === "pending") {
        items.push({
          id: `p-${s.id}`,
          title: "PIN waiting",
          detail: `Session ${s.pin} ready for scanner`,
          time: relativeTime(s.created_at),
          tone: "info",
          icon: "pin",
        });
      }
    });
    return items.slice(0, 6);
  }, [sessions]);

  const recent = sessions;
  const pageCount = Math.max(1, Math.ceil(recent.length / pageSize));
  const pageRows = recent.slice(page * pageSize, page * pageSize + pageSize);

  const linePath = chartPoints
    .map((p, i) => {
      const x = (i / Math.max(chartPoints.length - 1, 1)) * 220;
      return `${i === 0 ? "M" : "L"}${x},${p.y}`;
    })
    .join(" ");
  const areaPath = `${linePath} L220,80 L0,80 Z`;

  const threatBars = useMemo(() => {
    const buckets = { Clean: 0, Threat: 0, Watch: 0, Pending: 0, Expired: 0 };
    sessions.forEach((s) => {
      if (s.status === "pending") buckets.Pending += 1;
      else if (s.status === "expired") buckets.Expired += 1;
      else {
        const tone = verdictTone(s.reviewer_verdict);
        if (tone === "clean") buckets.Clean += 1;
        else if (tone === "threat") buckets.Threat += 1;
        else buckets.Watch += 1;
      }
    });
    const max = Math.max(...Object.values(buckets), 1);
    return Object.entries(buckets).map(([name, count]) => ({
      name,
      count,
      pct: Math.round((count / max) * 100),
    }));
  }, [sessions]);

  return (
    <section className="ov">
      <header className="ov__header">
        <div>
          <h1>Dashboard</h1>
          <p>Monitor scans and detect threats in real-time.</p>
        </div>
        <div className="ov__header-actions">
          <span className="ov__range">
            <MaterialIcon name="schedule" size={14} color="9aa3b2" />
            Last 7 days
          </span>
          <button type="button" className="btn btn--primary btn--sm" onClick={onNewScan}>
            <MaterialIcon name="add" size={14} color="ffffff" />
            New Scan
          </button>
        </div>
      </header>

      <div className="ov__metrics">
        {metrics.map((m) => (
          <article key={m.label} className="ov__metric">
            <div className="ov__metric-icon">
              <MaterialIcon name={m.icon} size={18} color={m.ok ? "22c55e" : "ef4444"} />
            </div>
            <div>
              <span className="ov__metric-label">{m.label}</span>
              <strong>{m.value}</strong>
              <em className={m.ok ? "is-ok" : ""}>{m.hint}</em>
            </div>
          </article>
        ))}
      </div>

      <div className="ov__layout">
        <div className="ov__panel ov__panel--table">
          <div className="ov__panel-head">
            <h2>Recent Scans</h2>
            <span className="muted">{sessions.length} total</span>
          </div>
          <div className="ov__table-wrap">
            <table className="ov__table">
              <thead>
                <tr>
                  <th>PIN / User</th>
                  <th>Result</th>
                  <th>Status</th>
                  <th>Time</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {pageRows.length ? (
                  pageRows.map((row) => {
                    const tone = row.status === "completed" ? verdictTone(row.reviewer_verdict) : row.status;
                    return (
                      <tr key={row.id} onClick={() => onOpenScan?.(row.id)}>
                        <td>
                          <span className="ov__user">
                            <span className="ov__avatar">{String(row.pin || "?").slice(0, 1)}</span>
                            <span>
                              <strong>{row.pin}</strong>
                              <em>Session #{row.id}</em>
                            </span>
                          </span>
                        </td>
                        <td>
                          <span className={`ov__pill ov__pill--${tone}`}>
                            {statusLabel(row.status, row.reviewer_verdict)}
                          </span>
                        </td>
                        <td>{row.status}</td>
                        <td>{relativeTime(row.completed_at || row.created_at)}</td>
                        <td>Scanner</td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={5} className="ov__empty">
                      No scans yet. Create a PIN to start.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {pageCount > 1 ? (
            <div className="ov__pager">
              {Array.from({ length: pageCount }, (_, i) => (
                <button
                  key={i}
                  type="button"
                  className={i === page ? "is-active" : ""}
                  onClick={() => setPage(i)}
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
              <h2>Activity Over Time</h2>
            </div>
            <svg className="ov__chart" viewBox="0 0 220 90" preserveAspectRatio="none" aria-hidden="true">
              <defs>
                <linearGradient id="ovFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path d={areaPath} fill="url(#ovFill)" />
              <path d={linePath} fill="none" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              {chartPoints.map((p, i) => (
                <circle key={p.label} cx={(i / Math.max(chartPoints.length - 1, 1)) * 220} cy={p.y} r="3.2" fill="#ef4444" />
              ))}
            </svg>
            <div className="ov__chart-labels">
              {chartPoints.map((p) => (
                <span key={p.label}>{p.label}</span>
              ))}
            </div>
          </div>

          <div className="ov__panel">
            <div className="ov__panel-head">
              <h2>Session Mix</h2>
            </div>
            <ul className="ov__bars">
              {threatBars.map((bar) => (
                <li key={bar.name}>
                  <div className="ov__bars-meta">
                    <span>{bar.name}</span>
                    <em>{bar.count}</em>
                  </div>
                  <div className="ov__bars-track">
                    <i style={{ width: `${bar.pct}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="ov__bottom">
        <div className="ov__panel">
          <div className="ov__panel-head">
            <h2>System Status</h2>
          </div>
          <ul className="ov__status">
            {[
              ["Real-time Scanning", "Active"],
              ["PIN Sessions", "Operational"],
              ["Result Storage", "Operational"],
              ["API Service", "Operational"],
            ].map(([label, state]) => (
              <li key={label}>
                <i />
                <span>{label}</span>
                <em>{state}</em>
              </li>
            ))}
          </ul>
        </div>

        <div className="ov__panel ov__panel--alerts">
          <div className="ov__panel-head">
            <h2>Recent Alerts</h2>
          </div>
          <ul className="ov__alerts">
            {alerts.length ? (
              alerts.map((alert) => (
                <li key={alert.id} className={`tone-${alert.tone}`}>
                  <MaterialIcon
                    name={alert.icon}
                    size={16}
                    color={alert.tone === "warn" ? "eab308" : alert.tone === "info" ? "60a5fa" : "ef4444"}
                  />
                  <div>
                    <strong>{alert.title}</strong>
                    <span>{alert.detail}</span>
                  </div>
                  <em>{alert.time}</em>
                </li>
              ))
            ) : (
              <li className="ov__alerts-empty">No alerts from recent sessions.</li>
            )}
          </ul>
        </div>

        <div className="ov__panel">
          <div className="ov__panel-head">
            <h2>Latest Completions</h2>
          </div>
          <ul className="ov__completions">
            {sessions
              .filter((s) => s.status === "completed")
              .slice(0, 5)
              .map((s) => (
                <li key={s.id}>
                  <strong>{s.pin}</strong>
                  <span>{s.reviewer_verdict || "Unreviewed"}</span>
                  <em>{formatDisplayDate(s.completed_at) || relativeTime(s.completed_at)}</em>
                </li>
              ))}
            {!sessions.some((s) => s.status === "completed") ? (
              <li className="ov__alerts-empty">No completed scans yet.</li>
            ) : null}
          </ul>
        </div>
      </div>
    </section>
  );
}
