import React, { useCallback, useEffect, useState } from "react";
import { MaterialIcon } from "./MaterialIcon.jsx";

const EMPTY_CHANGELOG = { version: "", title: "", body: "", is_published: true };
const EMPTY_ALERT = { message: "", severity: "info", active: true, dismissible: true };

export function AdminSitePanel({ apiUrl, headers }) {
  const [changelog, setChangelog] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [settings, setSettings] = useState({ demo_video_url: "" });
  const [changelogDraft, setChangelogDraft] = useState(EMPTY_CHANGELOG);
  const [alertDraft, setAlertDraft] = useState(EMPTY_ALERT);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [changelogRes, alertsRes, settingsRes] = await Promise.all([
      fetch(`${apiUrl}/admin/changelog`, { headers }),
      fetch(`${apiUrl}/admin/alerts`, { headers }),
      fetch(`${apiUrl}/admin/site-settings`, { headers }),
    ]);
    if (changelogRes.ok) setChangelog(await changelogRes.json());
    if (alertsRes.ok) setAlerts(await alertsRes.json());
    if (settingsRes.ok) setSettings(await settingsRes.json());
  }, [apiUrl, headers]);

  useEffect(() => {
    void load().catch((caught) => setError(caught.message));
  }, [load]);

  async function post(path, body) {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${apiUrl}${path}`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      await load();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(path) {
    setBusy(true);
    try {
      const response = await fetch(`${apiUrl}${path}`, { method: "DELETE", headers });
      if (!response.ok) throw new Error(`Delete failed: ${response.status}`);
      await load();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="admin-site-panel">
      {error ? <div className="error-banner">{error}</div> : null}

      <section className="card-like admin-site-section">
        <h3>
          <MaterialIcon name="smart_display" size={16} /> Demo video URL
        </h3>
        <p className="muted">Shown on the landing page. Leave empty for the placeholder until your video is ready.</p>
        <input
          className="admin-input"
          value={settings.demo_video_url || ""}
          onChange={(event) => setSettings({ ...settings, demo_video_url: event.target.value })}
          placeholder="https://…/demo.mp4"
        />
        <button
          type="button"
          className="btn btn--primary btn--sm"
          disabled={busy}
          onClick={() => post("/admin/site-settings", settings)}
        >
          Save video URL
        </button>
      </section>

      <section className="card-like admin-site-section">
        <h3>
          <MaterialIcon name="campaign" size={16} /> Site alerts
        </h3>
        <p className="muted">Banner shown on every public page. Only you can publish these from admin.</p>
        <textarea
          className="admin-textarea"
          rows={2}
          value={alertDraft.message}
          onChange={(event) => setAlertDraft({ ...alertDraft, message: event.target.value })}
          placeholder="Maintenance tonight at 22:00 UTC…"
        />
        <div className="admin-inline-row">
          <select
            value={alertDraft.severity}
            onChange={(event) => setAlertDraft({ ...alertDraft, severity: event.target.value })}
          >
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>
          <button
            type="button"
            className="btn btn--primary btn--sm"
            disabled={busy || !alertDraft.message.trim()}
            onClick={() => {
              void post("/admin/alerts", alertDraft).then(() => setAlertDraft(EMPTY_ALERT));
            }}
          >
            Publish alert
          </button>
        </div>
        <ul className="admin-recent-list">
          {alerts.map((alert) => (
            <li key={alert.id}>
              <span>
                [{alert.severity}] {alert.message}
              </span>
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => remove(`/admin/alerts/${alert.id}`)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="card-like admin-site-section">
        <h3>
          <MaterialIcon name="history_edu" size={16} /> Changelog
        </h3>
        <p className="muted">Public release notes at /changelog.</p>
        <div className="admin-inline-row">
          <input
            className="admin-input"
            value={changelogDraft.version}
            onChange={(event) => setChangelogDraft({ ...changelogDraft, version: event.target.value })}
            placeholder="1.2.0"
          />
          <input
            className="admin-input"
            value={changelogDraft.title}
            onChange={(event) => setChangelogDraft({ ...changelogDraft, title: event.target.value })}
            placeholder="Title"
          />
        </div>
        <textarea
          className="admin-textarea"
          rows={4}
          value={changelogDraft.body}
          onChange={(event) => setChangelogDraft({ ...changelogDraft, body: event.target.value })}
          placeholder="What changed…"
        />
        <button
          type="button"
          className="btn btn--primary btn--sm"
          disabled={busy || !changelogDraft.version.trim() || !changelogDraft.title.trim()}
          onClick={() => {
            void post("/admin/changelog", changelogDraft).then(() => setChangelogDraft(EMPTY_CHANGELOG));
          }}
        >
          Publish changelog entry
        </button>
        <ul className="admin-recent-list">
          {changelog.map((entry) => (
            <li key={entry.id}>
              <span>
                v{entry.version} — {entry.title}
              </span>
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => remove(`/admin/changelog/${entry.id}`)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
