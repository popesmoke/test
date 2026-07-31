import React, { useCallback, useEffect, useMemo, useState } from "react";
import { MaterialIcon } from "./components/MaterialIcon.jsx";
import { ConfirmModal } from "./components/ConfirmModal.jsx";
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
  return `${Math.floor(hours / 24)}d ago`;
}

const ADMIN_TABS = [
  { id: "overview", label: "Overview", icon: "dashboard" },
  { id: "sessions", label: "Sessions", icon: "database" },
  { id: "users", label: "Users", icon: "group" },
  { id: "tools", label: "Tools", icon: "admin_panel_settings" },
];

export function AdminPanel({ apiUrl, token, authHeaders }) {
  const [tab, setTab] = useState("overview");
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [purgeOpen, setPurgeOpen] = useState(false);
  const [purgeBusy, setPurgeBusy] = useState(false);
  const [userQuery, setUserQuery] = useState("");

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const headers = authHeaders(token);
      const [statsRes, sessionsRes, usersRes] = await Promise.all([
        fetch(`${apiUrl}/admin/stats`, { headers }),
        fetch(`${apiUrl}/admin/sessions`, { headers }),
        fetch(`${apiUrl}/admin/users`, { headers }),
      ]);
      if (!statsRes.ok) throw new Error(`Admin stats failed: ${statsRes.status}`);
      setStats(await statsRes.json());
      setSessions(sessionsRes.ok ? await sessionsRes.json() : []);
      setUsers(usersRes.ok ? await usersRes.json() : []);
      setError("");
    } catch (caught) {
      setError(caught.message);
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token, authHeaders]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  async function purgeExpired() {
    setPurgeBusy(true);
    try {
      const expired = sessions.filter((s) => s.status === "expired");
      for (const row of expired) {
        await fetch(`${apiUrl}/sessions/${row.id}`, { method: "DELETE", headers: authHeaders(token) });
      }
      setPurgeOpen(false);
      await loadAll();
    } finally {
      setPurgeBusy(false);
    }
  }

  const byStatus = stats?.by_status ?? {};
  const completed = byStatus.completed ?? 0;
  const pending = byStatus.pending ?? 0;
  const expired = byStatus.expired ?? 0;
  const total = stats?.total_sessions ?? 0;
  const withAccess = users.filter((u) => u.has_access).length;

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

  const linePath = chartPoints
    .map((p, i) => {
      const x = (i / Math.max(chartPoints.length - 1, 1)) * 220;
      return `${i === 0 ? "M" : "L"}${x},${p.y}`;
    })
    .join(" ");
  const areaPath = `${linePath} L220,80 L0,80 Z`;

  const filteredUsers = users.filter((u) => {
    const q = userQuery.trim().toLowerCase();
    if (!q) return true;
    return String(u.username || "").toLowerCase().includes(q) || String(u.discord_id || "").includes(q);
  });

  const metricCards = [
    { label: "Total Sessions", value: total, icon: "database", hint: "All time" },
    { label: "Completed", value: completed, icon: "check_circle", hint: "Uploaded results", ok: true },
    { label: "Pending PINs", value: pending, icon: "pin", hint: "Awaiting scan" },
    { label: "Expired", value: expired, icon: "schedule", hint: "Timed out" },
    { label: "Reviewers", value: users.length, icon: "group", hint: `${withAccess} with access`, ok: true },
  ];

  return (
    <section className="ad">
      <header className="ad__header">
        <div>
          <p className="ad__eyebrow">Super admin</p>
          <h1>Admin Dashboard</h1>
          <p>Sessions, reviewers, and platform health across the API.</p>
        </div>
        <div className="ad__header-actions">
          <button type="button" className="btn btn--ghost btn--sm" onClick={loadAll} disabled={loading}>
            <MaterialIcon name="refresh" size={16} />
            Refresh
          </button>
          <button type="button" className="btn btn--primary btn--sm" onClick={() => setPurgeOpen(true)}>
            <MaterialIcon name="delete_sweep" size={16} color="ffffff" />
            Purge expired
          </button>
        </div>
      </header>

      <nav className="ad__tabs" aria-label="Admin sections">
        {ADMIN_TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={tab === item.id ? "is-active" : ""}
            onClick={() => setTab(item.id)}
          >
            <MaterialIcon name={item.icon} size={16} color={tab === item.id ? "ffffff" : "9aa3b2"} />
            {item.label}
          </button>
        ))}
      </nav>

      {error ? <div className="error-banner">{error}</div> : null}
      {loading && !stats ? <p className="muted">Loading admin data…</p> : null}

      {stats ? (
        <>
          {tab === "overview" ? (
            <>
              <div className="ad__metrics">
                {metricCards.map((m) => (
                  <article key={m.label} className="ad__metric">
                    <div className="ad__metric-icon">
                      <MaterialIcon name={m.icon} size={18} color={m.ok ? "22c55e" : "ef4444"} />
                    </div>
                    <div>
                      <span>{m.label}</span>
                      <strong>{Number(m.value).toLocaleString()}</strong>
                      <em className={m.ok ? "is-ok" : ""}>{m.hint}</em>
                    </div>
                  </article>
                ))}
              </div>

              <div className="ad__layout">
                <div className="ad__panel ad__panel--wide">
                  <div className="ad__panel-head">
                    <h2>Session Volume</h2>
                  </div>
                  <svg className="ad__chart" viewBox="0 0 220 90" preserveAspectRatio="none" aria-hidden="true">
                    <defs>
                      <linearGradient id="adFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ef4444" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <path d={areaPath} fill="url(#adFill)" />
                    <path d={linePath} fill="none" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" />
                    {chartPoints.map((p, i) => (
                      <circle key={p.label} cx={(i / Math.max(chartPoints.length - 1, 1)) * 220} cy={p.y} r="3.2" fill="#ef4444" />
                    ))}
                  </svg>
                  <div className="ad__chart-labels">
                    {chartPoints.map((p) => (
                      <span key={p.label}>
                        {p.label}
                        <em>{p.count}</em>
                      </span>
                    ))}
                  </div>
                </div>

                <div className="ad__panel">
                  <div className="ad__panel-head">
                    <h2>Status Breakdown</h2>
                  </div>
                  <ul className="ad__status-bars">
                    {[
                      ["Completed", completed, "ok"],
                      ["Pending", pending, "warn"],
                      ["Expired", expired, "bad"],
                    ].map(([label, count, tone]) => {
                      const pct = total ? Math.round((count / total) * 100) : 0;
                      return (
                        <li key={label}>
                          <div className="ad__status-meta">
                            <span>{label}</span>
                            <em>
                              {count} · {pct}%
                            </em>
                          </div>
                          <div className={`ad__status-track tone-${tone}`}>
                            <i style={{ width: `${pct}%` }} />
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>

                <div className="ad__panel">
                  <div className="ad__panel-head">
                    <h2>Recent Completions</h2>
                  </div>
                  <ul className="ad__feed">
                    {(stats.recent_completions || []).length ? (
                      (stats.recent_completions || []).slice(0, 8).map((row, i) => (
                        <li key={`${row.completed_at}-${i}`}>
                          <MaterialIcon name="check_circle" size={14} color="22c55e" />
                          <div>
                            <strong>Scan completed</strong>
                            <span>{formatDisplayDate(row.completed_at) || relativeTime(row.completed_at)}</span>
                          </div>
                        </li>
                      ))
                    ) : (
                      <li className="ad__empty">No recent completions.</li>
                    )}
                  </ul>
                </div>
              </div>
            </>
          ) : null}

          {tab === "sessions" ? (
            <div className="ad__panel">
              <div className="ad__panel-head">
                <h2>
                  <MaterialIcon name="database" size={16} /> All Sessions
                </h2>
                <span className="muted">{sessions.length} shown</span>
              </div>
              <div className="ad__table-scroll">
                <table className="ad__table">
                  <thead>
                    <tr>
                      <th>PIN</th>
                      <th>Status</th>
                      <th>Verdict</th>
                      <th>Completed</th>
                      <th>Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.length ? (
                      sessions.slice(0, 80).map((row) => (
                        <tr key={row.id}>
                          <td>
                            <strong>{row.pin}</strong>
                          </td>
                          <td>
                            <span className={`ad__pill ad__pill--${row.status}`}>{row.status}</span>
                          </td>
                          <td>{row.reviewer_verdict || "—"}</td>
                          <td>{row.completed_at ? relativeTime(row.completed_at) : "—"}</td>
                          <td className="ad__note">{row.reviewer_note ? row.reviewer_note.slice(0, 90) : "—"}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5}>No sessions.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {tab === "users" ? (
            <div className="ad__panel">
              <div className="ad__panel-head">
                <h2>
                  <MaterialIcon name="group" size={16} /> Reviewer Logins
                </h2>
                <label className="ad__search">
                  <MaterialIcon name="search" size={14} color="9aa3b2" />
                  <input
                    value={userQuery}
                    onChange={(e) => setUserQuery(e.target.value)}
                    placeholder="Filter users…"
                  />
                </label>
              </div>
              <div className="ad__table-scroll">
                <table className="ad__table">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Access</th>
                      <th>Last login</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.length ? (
                      filteredUsers.slice(0, 60).map((row) => (
                        <tr key={row.discord_id}>
                          <td>
                            <span className="ad__user">
                              <span className="ad__avatar">{String(row.username || "?").slice(0, 1).toUpperCase()}</span>
                              <span>
                                <strong>{row.username}</strong>
                                <em>{row.discord_id}</em>
                              </span>
                            </span>
                          </td>
                          <td>
                            <span className={`ad__pill ad__pill--${row.has_access ? "completed" : "expired"}`}>
                              {row.has_access ? "Access" : "No access"}
                            </span>
                          </td>
                          <td>{row.last_login_at ? relativeTime(row.last_login_at) : "—"}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={3}>No Discord users recorded yet.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {tab === "tools" ? (
            <div className="ad__tools">
              <article className="ad__panel">
                <div className="ad__panel-head">
                  <h2>Maintenance</h2>
                </div>
                <p className="muted">
                  Remove expired PIN sessions that no longer hold useful scan data. Completed sessions are kept.
                </p>
                <button type="button" className="btn btn--primary" onClick={() => setPurgeOpen(true)}>
                  <MaterialIcon name="delete_sweep" size={16} color="ffffff" />
                  Purge {expired} expired session{expired === 1 ? "" : "s"}
                </button>
              </article>
              <article className="ad__panel">
                <div className="ad__panel-head">
                  <h2>Platform</h2>
                </div>
                <ul className="ad__platform">
                  <li>
                    <MaterialIcon name="shield" size={16} color="22c55e" />
                    <div>
                      <strong>Access control</strong>
                      <span>Discord role gate + super-admin IDs</span>
                    </div>
                  </li>
                  <li>
                    <MaterialIcon name="cloud" size={16} color="ef4444" />
                    <div>
                      <strong>API</strong>
                      <span>{apiUrl.replace(/^https?:\/\//, "")}</span>
                    </div>
                  </li>
                  <li>
                    <MaterialIcon name="groups" size={16} color="60a5fa" />
                    <div>
                      <strong>Reviewers with access</strong>
                      <span>
                        {withAccess} / {users.length}
                      </span>
                    </div>
                  </li>
                </ul>
              </article>
            </div>
          ) : null}
        </>
      ) : null}

      <ConfirmModal
        open={purgeOpen}
        title="Purge expired sessions?"
        message="This permanently removes every expired PIN session from the database."
        confirmLabel="Purge expired"
        busy={purgeBusy}
        onCancel={() => {
          if (!purgeBusy) setPurgeOpen(false);
        }}
        onConfirm={purgeExpired}
      />
    </section>
  );
}
