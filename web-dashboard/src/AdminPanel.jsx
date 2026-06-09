import React, { useCallback, useEffect, useState } from "react";
import { Database, RefreshCw, Shield, Trash2, Users } from "lucide-react";

export function AdminPanel({ apiUrl, token, authHeaders }) {
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

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
    if (!window.confirm("Delete all expired PIN sessions from the database?")) return;
    const expired = sessions.filter((s) => s.status === "expired");
    for (const row of expired) {
      await fetch(`${apiUrl}/sessions/${row.id}`, { method: "DELETE", headers: authHeaders(token) });
    }
    await loadAll();
  }

  const byStatus = stats?.by_status ?? {};

  return (
    <section className="admin-panel">
      <header className="admin-panel-header">
        <div>
          <p className="eyebrow">Owner tools</p>
          <h2>
            <Shield size={18} /> Scanner admin
          </h2>
          <p className="muted">Sessions, reviewers, and verdict tags across the API.</p>
        </div>
        <div className="actions">
          <button type="button" onClick={loadAll} disabled={loading}>
            <RefreshCw size={16} /> Refresh
          </button>
          <button type="button" onClick={purgeExpired}>
            <Trash2 size={16} /> Purge expired
          </button>
        </div>
      </header>
      {error ? <div className="error-banner">{error}</div> : null}
      {loading && !stats ? <p className="muted">Loading admin data…</p> : null}
      {stats ? (
        <>
          <div className="admin-stat-grid">
            <div className="admin-stat">
              <strong>{stats.total_sessions ?? 0}</strong>
              <span>Total sessions</span>
            </div>
            <div className="admin-stat">
              <strong>{byStatus.completed ?? 0}</strong>
              <span>Completed</span>
            </div>
            <div className="admin-stat">
              <strong>{byStatus.pending ?? 0}</strong>
              <span>Pending PINs</span>
            </div>
            <div className="admin-stat">
              <strong>{users.length}</strong>
              <span>Discord logins</span>
            </div>
          </div>
          <div className="admin-table card-like">
            <h3>
              <Database size={16} /> Sessions
            </h3>
            <div className="admin-table-scroll">
              <table>
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
                    sessions.slice(0, 50).map((row) => (
                      <tr key={row.id}>
                        <td>{row.pin}</td>
                        <td>{row.status}</td>
                        <td>{row.reviewer_verdict || "—"}</td>
                        <td>{row.completed_at || "—"}</td>
                        <td>{row.reviewer_note ? row.reviewer_note.slice(0, 80) : "—"}</td>
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
          <div className="admin-table card-like">
            <h3>
              <Users size={16} /> Reviewer logins
            </h3>
            <div className="admin-table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Access</th>
                    <th>Last login</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length ? (
                    users.slice(0, 40).map((row) => (
                      <tr key={row.discord_id}>
                        <td>{row.username}</td>
                        <td>{row.has_access ? "Yes" : "No"}</td>
                        <td>{row.last_login_at || "—"}</td>
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
        </>
      ) : null}
    </section>
  );
}
