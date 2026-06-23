import React, { useCallback, useEffect, useMemo, useState } from "react";
import { MaterialIcon } from "./components/MaterialIcon.jsx";
import { ConfirmModal } from "./components/ConfirmModal.jsx";
import { Pagination } from "./components/Pagination.jsx";
import { usePagination } from "./hooks/usePagination.js";

const VERDICTS = ["", "cleared", "suspicious", "ban", "follow-up"];
const STATUS_FILTERS = ["", "pending", "completed", "expired"];

function formatWhen(value) {
  if (!value) return "n/a";
  return String(value).replace("T", " ").replace("Z", " UTC");
}

export function AdminPanel({ apiUrl, token, authHeaders }) {
  const [tab, setTab] = useState("overview");
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [purgeOpen, setPurgeOpen] = useState(false);
  const [purgeBusy, setPurgeBusy] = useState(false);
  const [backupBusy, setBackupBusy] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [reviewDraft, setReviewDraft] = useState({ verdict: "", note: "" });
  const [userDraft, setUserDraft] = useState({ admin_notes: "", access_override: "", admin_banned: false });

  const headers = useMemo(() => authHeaders(token), [authHeaders, token]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const query = new URLSearchParams();
      if (statusFilter) query.set("status", statusFilter);
      if (search.trim()) query.set("q", search.trim());
      const sessionPath = query.toString() ? `/admin/sessions?${query}` : "/admin/sessions";
      const [statsRes, healthRes, sessionsRes, usersRes] = await Promise.all([
        fetch(`${apiUrl}/admin/stats`, { headers }),
        fetch(`${apiUrl}/admin/health`, { headers }),
        fetch(`${apiUrl}${sessionPath}`, { headers }),
        fetch(`${apiUrl}/admin/users`, { headers }),
      ]);
      if (!statsRes.ok) throw new Error(`Admin stats failed: ${statsRes.status}`);
      setStats(await statsRes.json());
      setHealth(healthRes.ok ? await healthRes.json() : null);
      setSessions(sessionsRes.ok ? await sessionsRes.json() : []);
      setUsers(usersRes.ok ? await usersRes.json() : []);
      setError("");
    } catch (caught) {
      setError(caught.message);
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, headers, search, statusFilter]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const sessionsPage = usePagination(sessions, 15);
  const usersPage = usePagination(users, 15);

  async function loadSessionDetail(sessionId) {
    setActionBusy(true);
    try {
      const response = await fetch(`${apiUrl}/admin/sessions/${sessionId}`, { headers });
      if (!response.ok) throw new Error(`Failed to load session: ${response.status}`);
      const detail = await response.json();
      setSelectedSession(detail);
      setReviewDraft({
        verdict: detail.reviewer_verdict || "",
        note: detail.reviewer_note || "",
      });
    } catch (caught) {
      setError(caught.message);
    } finally {
      setActionBusy(false);
    }
  }

  function openUserEditor(user) {
    setSelectedUser(user);
    setUserDraft({
      admin_notes: user.admin_notes || "",
      access_override: user.access_override == null ? "" : String(user.access_override),
      admin_banned: Boolean(user.admin_banned),
    });
  }

  async function saveSessionReview() {
    if (!selectedSession) return;
    setActionBusy(true);
    try {
      const response = await fetch(`${apiUrl}/admin/sessions/${selectedSession.id}/review`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(reviewDraft),
      });
      if (!response.ok) throw new Error(`Review save failed: ${response.status}`);
      setSelectedSession(null);
      await loadAll();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setActionBusy(false);
    }
  }

  async function deleteSession(sessionId) {
    if (!window.confirm(`Delete session #${sessionId} permanently?`)) return;
    setActionBusy(true);
    try {
      const response = await fetch(`${apiUrl}/admin/sessions/${sessionId}`, { method: "DELETE", headers });
      if (!response.ok) throw new Error(`Delete failed: ${response.status}`);
      if (selectedSession?.id === sessionId) setSelectedSession(null);
      await loadAll();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setActionBusy(false);
    }
  }

  async function saveUserControls() {
    if (!selectedUser) return;
    setActionBusy(true);
    try {
      const body = {
        admin_banned: userDraft.admin_banned,
        admin_notes: userDraft.admin_notes,
      };
      if (userDraft.access_override === "") {
        body.access_override = null;
      } else {
        body.access_override = Number(userDraft.access_override);
      }
      const response = await fetch(`${apiUrl}/admin/users/${selectedUser.discord_id}`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error(`User update failed: ${response.status}`);
      setSelectedUser(null);
      await loadAll();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setActionBusy(false);
    }
  }

  async function purgeExpired() {
    setPurgeBusy(true);
    try {
      const response = await fetch(`${apiUrl}/admin/sessions/purge`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ status: "expired" }),
      });
      if (!response.ok) throw new Error(`Purge failed: ${response.status}`);
      setPurgeOpen(false);
      await loadAll();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setPurgeBusy(false);
    }
  }

  async function triggerBackup() {
    setBackupBusy(true);
    try {
      const response = await fetch(`${apiUrl}/admin/backup`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: "{}",
      });
      if (!response.ok) throw new Error(`Backup failed: ${response.status}`);
      await loadAll();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBackupBusy(false);
    }
  }

  const byStatus = stats?.by_status ?? {};
  const byVerdict = stats?.by_verdict ?? {};
  const storage = stats?.storage ?? health?.storage ?? null;

  return (
    <section className="admin-panel">
      <header className="admin-panel-header">
        <div>
          <p className="eyebrow">Owner tools</p>
          <h2>
            <MaterialIcon name="admin_panel_settings" size={18} /> Scanner admin
          </h2>
          <p className="muted">Full control over sessions, reviewers, storage sync, and access overrides.</p>
        </div>
        <div className="actions">
          <button type="button" className="btn btn--ghost btn--sm" onClick={loadAll} disabled={loading}>
            <MaterialIcon name="refresh" size={16} /> Refresh
          </button>
          <button type="button" className="btn btn--ghost btn--sm" onClick={triggerBackup} disabled={backupBusy}>
            <MaterialIcon name="backup" size={16} /> {backupBusy ? "Backing up…" : "Backup now"}
          </button>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setPurgeOpen(true)}>
            <MaterialIcon name="delete_sweep" size={16} /> Purge expired
          </button>
        </div>
      </header>

      <nav className="admin-tabs" aria-label="Admin sections">
        {[
          { id: "overview", label: "Overview" },
          { id: "sessions", label: "Sessions" },
          { id: "users", label: "Users" },
          { id: "storage", label: "Storage" },
        ].map((row) => (
          <button
            key={row.id}
            type="button"
            className={tab === row.id ? "active" : ""}
            onClick={() => setTab(row.id)}
          >
            {row.label}
          </button>
        ))}
      </nav>

      {error ? <div className="error-banner">{error}</div> : null}
      {loading && !stats ? <p className="muted">Loading admin data…</p> : null}

      {stats && tab === "overview" ? (
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
              <strong>{byStatus.expired ?? 0}</strong>
              <span>Expired</span>
            </div>
            <div className="admin-stat">
              <strong>{stats.discord_users ?? users.length}</strong>
              <span>Discord logins</span>
            </div>
            <div className="admin-stat">
              <strong>{stats.banned_users ?? 0}</strong>
              <span>Banned users</span>
            </div>
          </div>
          <div className="admin-split-grid">
            <div className="admin-table card-like">
              <h3>
                <MaterialIcon name="gavel" size={16} /> Verdict breakdown
              </h3>
              <ul className="admin-recent-list">
                {Object.keys(byVerdict).length ? (
                  Object.entries(byVerdict).map(([verdict, count]) => (
                    <li key={verdict}>
                      <span>{verdict}</span>
                      <strong>{count}</strong>
                    </li>
                  ))
                ) : (
                  <li>
                    <span>No verdicts yet</span>
                  </li>
                )}
              </ul>
            </div>
            <div className="admin-table card-like">
              <h3>
                <MaterialIcon name="history" size={16} /> Recent completions
              </h3>
              <ul className="admin-recent-list">
                {(stats.recent_completions ?? []).map((row) => (
                  <li key={`${row.completed_at}-${row.status}`}>
                    <span>{formatWhen(row.completed_at)}</span>
                    <strong>{row.status}</strong>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      ) : null}

      {tab === "sessions" ? (
        <div className="admin-table card-like">
          <div className="admin-toolbar">
            <input
              type="search"
              placeholder="Search PIN, verdict, note, creator…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              {STATUS_FILTERS.map((value) => (
                <option key={value || "all"} value={value}>
                  {value ? value : "All statuses"}
                </option>
              ))}
            </select>
            <button type="button" className="btn btn--ghost btn--sm" onClick={loadAll}>
              Apply filters
            </button>
          </div>
          <div className="admin-table-scroll">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>PIN</th>
                  <th>Status</th>
                  <th>Verdict</th>
                  <th>Created by</th>
                  <th>Completed</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessionsPage.slice.length ? (
                  sessionsPage.slice.map((row) => (
                    <tr key={row.id}>
                      <td>{row.id}</td>
                      <td>{row.pin}</td>
                      <td>{row.status}</td>
                      <td>{row.reviewer_verdict || "n/a"}</td>
                      <td>{row.created_by || "n/a"}</td>
                      <td>{formatWhen(row.completed_at)}</td>
                      <td className="admin-actions-cell">
                        <button type="button" className="btn btn--ghost btn--sm" onClick={() => loadSessionDetail(row.id)}>
                          Open
                        </button>
                        <button type="button" className="btn btn--ghost btn--sm" onClick={() => deleteSession(row.id)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7}>No sessions match your filters.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <Pagination {...sessionsPage} onPageChange={sessionsPage.goTo} />
        </div>
      ) : null}

      {tab === "users" ? (
        <div className="admin-table card-like">
          <div className="admin-table-scroll">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Discord ID</th>
                  <th>Access</th>
                  <th>Role access</th>
                  <th>Banned</th>
                  <th>Last login</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {usersPage.slice.length ? (
                  usersPage.slice.map((row) => (
                    <tr key={row.discord_id}>
                      <td>{row.username}</td>
                      <td>{row.discord_id}</td>
                      <td>{row.has_access ? "Yes" : "No"}</td>
                      <td>{row.has_role_access ? "Yes" : "No"}</td>
                      <td>{row.admin_banned ? "Yes" : "No"}</td>
                      <td>{formatWhen(row.last_login_at)}</td>
                      <td>
                        <button type="button" className="btn btn--ghost btn--sm" onClick={() => openUserEditor(row)}>
                          Manage
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7}>No Discord users recorded yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <Pagination {...usersPage} onPageChange={usersPage.goTo} />
        </div>
      ) : null}

      {tab === "storage" && storage ? (
        <div className="admin-table card-like">
          <h3>
            <MaterialIcon name="cloud_sync" size={16} /> Storage & sync
          </h3>
          <ul className="admin-recent-list">
            <li>
              <span>Mode</span>
              <strong>{storage.mode || "unknown"}</strong>
            </li>
            <li>
              <span>Configured</span>
              <strong>{storage.configured ? "Yes" : "No"}</strong>
            </li>
            <li>
              <span>Channel ID</span>
              <strong>{storage.channel_id || "n/a"}</strong>
            </li>
            <li>
              <span>Backup file</span>
              <strong>{storage.snapshot_file || "virello-scanner-backup.txt"}</strong>
            </li>
            <li>
              <span>Last sync</span>
              <strong>{formatWhen(storage.last_sync_at)}</strong>
            </li>
          </ul>
          <p className="muted admin-storage-hint">
            One backup file is uploaded per change (debounced ~2.5s). On redeploy the latest backup file is restored
            from Discord automatically.
          </p>
        </div>
      ) : null}

      {selectedSession ? (
        <div className="admin-drawer card-like">
          <header className="admin-drawer__head">
            <h3>
              Session #{selectedSession.id} · PIN {selectedSession.pin}
            </h3>
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => setSelectedSession(null)}>
              Close
            </button>
          </header>
          <p className="muted">
            Status: {selectedSession.status} · Created {formatWhen(selectedSession.created_at)} · By{" "}
            {selectedSession.created_by || "unknown"}
          </p>
          <label className="admin-field">
            <span>Verdict</span>
            <select
              value={reviewDraft.verdict}
              onChange={(event) => setReviewDraft((prev) => ({ ...prev, verdict: event.target.value }))}
            >
              {VERDICTS.map((value) => (
                <option key={value || "none"} value={value}>
                  {value || "No verdict"}
                </option>
              ))}
            </select>
          </label>
          <label className="admin-field">
            <span>Reviewer note</span>
            <textarea
              rows={4}
              value={reviewDraft.note}
              onChange={(event) => setReviewDraft((prev) => ({ ...prev, note: event.target.value }))}
            />
          </label>
          <div className="actions">
            <button type="button" className="btn btn--primary btn--sm" disabled={actionBusy} onClick={saveSessionReview}>
              Save review
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              disabled={actionBusy}
              onClick={() => deleteSession(selectedSession.id)}
            >
              Delete session
            </button>
          </div>
        </div>
      ) : null}

      {selectedUser ? (
        <div className="admin-drawer card-like">
          <header className="admin-drawer__head">
            <h3>
              {selectedUser.username} ({selectedUser.discord_id})
            </h3>
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => setSelectedUser(null)}>
              Close
            </button>
          </header>
          <label className="admin-field admin-field--checkbox">
            <input
              type="checkbox"
              checked={userDraft.admin_banned}
              onChange={(event) => setUserDraft((prev) => ({ ...prev, admin_banned: event.target.checked }))}
            />
            <span>Banned from dashboard (overrides Discord role)</span>
          </label>
          <label className="admin-field">
            <span>Access override</span>
            <select
              value={userDraft.access_override}
              onChange={(event) => setUserDraft((prev) => ({ ...prev, access_override: event.target.value }))}
            >
              <option value="">Use Discord role</option>
              <option value="1">Force grant access</option>
              <option value="0">Force deny access</option>
            </select>
          </label>
          <label className="admin-field">
            <span>Admin notes</span>
            <textarea
              rows={3}
              value={userDraft.admin_notes}
              onChange={(event) => setUserDraft((prev) => ({ ...prev, admin_notes: event.target.value }))}
            />
          </label>
          <button type="button" className="btn btn--primary btn--sm" disabled={actionBusy} onClick={saveUserControls}>
            Save user controls
          </button>
        </div>
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
