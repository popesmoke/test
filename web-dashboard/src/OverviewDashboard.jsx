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
  const v = String(verdict || "").toLowerCase().trim();
  if (!v || v === "n/a" || v === "pending") return "pending";
  if (
    v === "cleared" ||
    v.includes("clean") ||
    v.includes("clear") ||
    v.includes("pass")
  ) {
    return "clean";
  }
  if (
    v === "ban" ||
    v === "suspicious" ||
    v.includes("threat") ||
    v.includes("fail") ||
    v.includes("cheat") ||
    v.includes("flag") ||
    v.includes("injector")
  ) {
    return "threat";
  }
  if (v === "follow-up" || v.includes("follow")) return "watch";
  return "watch";
}

/** Queue status pills: Waiting / In review / Cleared / Flagged / Expired */
function queueStatus(session) {
  if (session.status === "pending") return { key: "waiting", label: "Waiting" };
  if (session.status === "expired") return { key: "expired", label: "Expired" };
  if (session.status !== "completed") return { key: "waiting", label: session.status || "Unknown" };

  const tone = verdictTone(session.reviewer_verdict);
  if (tone === "clean") return { key: "cleared", label: "Cleared" };
  if (tone === "threat") return { key: "flagged", label: "Flagged" };
  if (session.reviewer_verdict) return { key: "review", label: "In review" };
  return { key: "review", label: "In review" };
}

function reviewOutcome(session) {
  if (session.status !== "completed") return "—";
  const tone = verdictTone(session.reviewer_verdict);
  if (tone === "threat") return { key: "flagged", label: "Flagged by reviewer" };
  if (tone === "watch") return { key: "follow-up", label: "Follow-up" };
  if (tone === "clean") return { key: "cleared", label: "Cleared" };
  return { key: "pending", label: "Awaiting review" };
}

function findingsCount(session) {
  const n =
    session.findings_count ??
    session.finding_count ??
    session.report_summary?.findings_count ??
    null;
  if (n == null || Number.isNaN(Number(n))) return "—";
  return String(n);
}

function copyPin(pin) {
  return navigator.clipboard?.writeText(String(pin)).catch(() => {});
}

export function OverviewDashboard({
  sessions = [],
  onOpenScan,
  onNewScan,
  demo = false,
  compact = false,
}) {
  const [page, setPage] = useState(0);
  const [copiedId, setCopiedId] = useState(null);
  const pageSize = compact ? 5 : 8;

  const stats = useMemo(() => {
    const completed = sessions.filter((s) => s.status === "completed");
    const pending = sessions.filter((s) => s.status === "pending");
    const expired = sessions.filter((s) => s.status === "expired");
    const flagged = completed.filter((s) => verdictTone(s.reviewer_verdict) === "threat");
    const cleared = completed.filter((s) => verdictTone(s.reviewer_verdict) === "clean");
    const inReview = completed.filter((s) => !s.reviewer_verdict || verdictTone(s.reviewer_verdict) === "watch");
    return {
      total: sessions.length,
      pending,
      expired,
      flagged,
      cleared,
      inReview,
      completed,
    };
  }, [sessions]);

  const pageCount = Math.max(1, Math.ceil(sessions.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const pageRows = sessions.slice(safePage * pageSize, safePage * pageSize + pageSize);

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
          <p className="ov__eyebrow">Investigation queue</p>
          <h1>Case desk</h1>
          <p>Track each PIN from first upload through reviewer decision.</p>
        </div>
        <div className="ov__header-actions">
          <button
            type="button"
            className="btn btn--primary ov__cta"
            onClick={onNewScan}
            disabled={demo}
          >
            <MaterialIcon name="add" size={16} color="ffffff" />
            New investigation
          </button>
        </div>
      </header>

      <div className="ov__metrics">
        <article className="ov__metric">
          <span className="ov__metric-label">All cases</span>
          <strong>{stats.total}</strong>
          <em>{stats.completed.length} completed</em>
        </article>
        <article className="ov__metric ov__metric--warn">
          <span className="ov__metric-label">Waiting</span>
          <strong>{stats.pending.length}</strong>
          <em>PIN shared, no upload yet</em>
        </article>
        <article className="ov__metric ov__metric--warn">
          <span className="ov__metric-label">In review</span>
          <strong>{stats.inReview.length}</strong>
          <em>Submitted reports, no decision yet</em>
        </article>
        <article className="ov__metric ov__metric--bad">
          <span className="ov__metric-label">Flagged</span>
          <strong>{stats.flagged.length}</strong>
          <em>Marked by a reviewer</em>
        </article>
        <article className="ov__metric ov__metric--ok">
          <span className="ov__metric-label">Cleared</span>
          <strong>{stats.cleared.length}</strong>
          <em>Marked cleared by a reviewer</em>
        </article>
      </div>

      <div className="ov__panel ov__panel--table">
        <div className="ov__panel-head">
          <h2>Cases in your queue</h2>
          <span className="ov__chip">{sessions.length}</span>
        </div>
        <div className="ov__table-wrap">
          <table className="ov__table">
            <thead>
              <tr>
                <th>PIN</th>
                <th>Status</th>
                <th>Reviewer outcome</th>
                <th>Evidence items</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.length ? (
                pageRows.map((row) => {
                  const status = queueStatus(row);
                  const outcome = reviewOutcome(row);
                  return (
                    <tr
                      key={row.id}
                      onClick={() => {
                        if (!demo) onOpenScan?.(row.id);
                      }}
                    >
                      <td>
                        <span className="ov__pin-cell">
                          <strong className="ov__pin">{row.pin}</strong>
                          <em>#{row.id}</em>
                        </span>
                      </td>
                      <td>
                        <span className={`ov__pill ov__pill--${status.key}`}>{status.label}</span>
                      </td>
                      <td>
                        {typeof outcome === "object" ? (
                          <span className={`ov__risk ov__risk--${outcome.key}`}>{outcome.label}</span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="ov__mono">{findingsCount(row)}</td>
                      <td>{relativeTime(row.completed_at || row.created_at)}</td>
                      <td>
                        <div className="ov__row-actions" onClick={(e) => e.stopPropagation()}>
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
                          <button
                            type="button"
                            className="ov__text-btn"
                            disabled={demo || row.status === "expired"}
                            onClick={() => {
                              if (!demo) onOpenScan?.(row.id);
                            }}
                          >
                            Open
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} className="ov__empty">
                    <strong>No investigations yet</strong>
                    <span>Create a PIN, share it during screenshare, and open the case when the scan uploads.</span>
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
                className={i === safePage ? "is-active" : ""}
                onClick={() => setPage(i)}
                disabled={demo}
              >
                {i + 1}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {!compact ? (
        <div className="ov__bottom">
          <div className="ov__panel">
            <div className="ov__panel-head">
              <h2>Waiting for upload</h2>
              <span className="ov__chip">{stats.pending.length}</span>
            </div>
            {stats.pending.length ? (
              <ul className="ov__queue">
                {stats.pending.slice(0, 6).map((s) => (
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
              <p className="ov__blank">No active PINs awaiting upload.</p>
            )}
          </div>

          <div className="ov__panel">
            <div className="ov__panel-head">
              <h2>Flagged cases</h2>
              <span className="ov__chip ov__chip--warn">{stats.flagged.length}</span>
            </div>
            {stats.flagged.length ? (
              <ul className="ov__threats">
                {stats.flagged.slice(0, 6).map((s) => (
                  <li key={s.id}>
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
              <p className="ov__blank">No flagged verdicts recorded.</p>
            )}
          </div>

          <div className="ov__panel">
            <div className="ov__panel-head">
              <h2>Recent clearances</h2>
            </div>
            <ul className="ov__completions">
              {stats.cleared.slice(0, 6).map((s) => (
                <li key={s.id}>
                  <span className="ov__dot ov__dot--clean" />
                  <div>
                    <strong>{s.pin}</strong>
                    <span>{s.reviewer_verdict || "Cleared"}</span>
                  </div>
                  <em>{formatDisplayDate(s.reviewed_at || s.completed_at) || relativeTime(s.completed_at)}</em>
                </li>
              ))}
              {!stats.cleared.length ? <li className="ov__blank-row">No cleared cases yet.</li> : null}
            </ul>
          </div>
        </div>
      ) : null}
    </section>
  );
}
