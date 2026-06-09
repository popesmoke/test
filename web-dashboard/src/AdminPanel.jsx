import React, { useCallback, useEffect, useState } from "react";
import { Database, RefreshCw, Shield } from "lucide-react";

export function AdminPanel({ apiUrl, token, authHeaders }) {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadStats = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${apiUrl}/admin/stats`, { headers: authHeaders(token) });
      if (!response.ok) {
        throw new Error(`Admin stats failed: ${response.status}`);
      }
      setStats(await response.json());
      setError("");
    } catch (caught) {
      setError(caught.message);
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token, authHeaders]);

  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  const byStatus = stats?.by_status ?? {};

  return (
    <section className="admin-panel">
      <header className="admin-panel-header">
        <div>
          <p className="eyebrow">Owner tools</p>
          <h2>
            <Shield size={18} /> Scanner admin
          </h2>
          <p className="muted">Session totals and recent completions for the diagnostic API.</p>
        </div>
        <button type="button" onClick={loadStats} disabled={loading}>
          <RefreshCw size={16} /> Refresh
        </button>
      </header>
      {error ? <div className="error-banner">{error}</div> : null}
      {loading && !stats ? <p className="muted">Loading admin stats…</p> : null}
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
              <strong>{byStatus.expired ?? 0}</strong>
              <span>Expired</span>
            </div>
          </div>
          <div className="admin-recent card-like">
            <h3>
              <Database size={16} /> Recent completions
            </h3>
            {(stats.recent_completions ?? []).length ? (
              <ul className="admin-recent-list">
                {stats.recent_completions.map((row, index) => (
                  <li key={`${row.completed_at}-${index}`}>
                    <span>{row.status}</span>
                    <time>{row.completed_at}</time>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No completed scans yet.</p>
            )}
          </div>
        </>
      ) : null}
    </section>
  );
}
