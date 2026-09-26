import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ChevronRight,
  Clock,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  FolderSearch,
  Link2,
  Printer,
  Search,
  Shield,
  Users,
  X,
} from "lucide-react";
import { SeverityBadge } from "./components/SeverityBadge.jsx";
import { defenderSummary } from "./defenderSignals.js";
import { scanReviewFromReport } from "./reportDigest.js";
import { formatDisplayLocation, privacyPath, publicFindingLabels } from "./resultPrivacy.js";
import {
  collectRobloxAccountsFromReport,
  collectDiscordAccountsFromReport,
} from "./accountExtract.js";
import { forensicSourcesView } from "./forensicSources.js";
import {
  buildInvestigationFindings,
  engineVerdictPlain,
  filterFindings,
  METHODOLOGY_BLURB,
  severityCounts,
  sortFindings,
} from "./findingsModel.js";
import { compareSessions } from "./scanCompare.js";
import { exportReportPdf, findingsToCsv } from "./exportReportPdf.js";

const API_URL = import.meta.env.VITE_API_URL || "https://virello-secure.onrender.com";

const TABS = [
  { id: "overview", label: "Overview", icon: Shield },
  { id: "findings", label: "Findings", icon: AlertTriangle },
  { id: "timeline", label: "Timeline", icon: Clock },
  { id: "evidence", label: "Evidence", icon: Link2 },
  { id: "accounts", label: "Accounts", icon: Users },
  { id: "export", label: "Export", icon: Download },
];

const SEVERITY_OPTIONS = ["critical", "high", "medium", "low"];
const CONFIDENCE_OPTIONS = ["high", "medium", "low"];
const STATUS_OPTIONS = ["confirmed", "suspicious", "informational", "inconclusive"];

function confidencePct(finding) {
  if (finding.confidence == null) return "—";
  return `${Math.round(finding.confidence * 100)}%`;
}

function Panel({ icon: Icon, title, text, children, compact = false }) {
  return (
    <section className={`ws-panel${compact ? " ws-panel--compact" : ""}`}>
      <header className="ws-panel__head">
        {Icon ? <Icon size={18} strokeWidth={1.75} aria-hidden /> : null}
        <div>
          <h4>{title}</h4>
          {text ? <p>{text}</p> : null}
        </div>
      </header>
      {children ? <div className="ws-panel__body">{children}</div> : null}
    </section>
  );
}

function LocationHint({ row, path }) {
  const text = formatDisplayLocation(row) || privacyPath(path);
  if (!text) return null;
  return <span className="ws-mono muted">{text}</span>;
}

function StatusChip({ status }) {
  return <span className={`ws-status-chip ws-status-chip--${status}`}>{status}</span>;
}

function ConfidenceChip({ tier }) {
  return <span className={`ws-conf-chip ws-conf-chip--${tier}`}>{tier}</span>;
}

function OverviewTab({ verdict, findings, counts, report, formatGmtPlus3, onOpenFinding }) {
  const top = findings.slice(0, 6);
  const sources = forensicSourcesView(report.security_integrity_signals ?? {});
  const defenderView = defenderSummary(report.security_integrity_signals?.defender);
  const env = report.performance_environment ?? {};

  return (
    <>
      <div className="ws-risk-model" aria-label="Risk and confidence model">
        <section className={`ws-risk-model__verdict ws-risk-model__verdict--${verdict.tone}`}>
          <p className="ws-eyebrow">Engine verdict</p>
          <h3>{verdict.label}</h3>
          <p>{verdict.blurb}</p>
          {verdict.incomplete ? (
            <p className="ws-risk-model__warn">Scan incomplete — treat weaker signals as inconclusive.</p>
          ) : null}
        </section>

        <section className="ws-risk-model__axis" aria-label="Severity summary">
          <p className="ws-eyebrow">Severity</p>
          <div className="ws-risk-bars">
            {["critical", "high", "medium", "low"].map((sev) => (
              <div key={sev} className={`ws-risk-bar ws-risk-bar--${sev}`}>
                <span>{sev}</span>
                <strong>{counts[sev] || 0}</strong>
              </div>
            ))}
          </div>
          <p className="ws-risk-model__hint">Impact if the indicator is genuine.</p>
        </section>

        <section className="ws-risk-model__axis" aria-label="Confidence summary">
          <p className="ws-eyebrow">Confidence</p>
          <div className="ws-risk-bars">
            <div className="ws-risk-bar ws-risk-bar--conf-high">
              <span>high</span>
              <strong>{counts.confidenceHigh}</strong>
            </div>
            <div className="ws-risk-bar ws-risk-bar--conf-medium">
              <span>medium</span>
              <strong>{counts.confidenceMedium}</strong>
            </div>
            <div className="ws-risk-bar ws-risk-bar--conf-low">
              <span>low</span>
              <strong>{counts.confidenceLow}</strong>
            </div>
          </div>
          <p className="ws-risk-model__hint">How strongly evidence supports each indicator.</p>
        </section>
      </div>

      <section className="ws-panel ws-panel--compact">
        <header className="ws-panel__head">
          <FolderSearch size={18} strokeWidth={1.75} aria-hidden />
          <div>
            <h4>Methodology</h4>
            <p>{METHODOLOGY_BLURB}</p>
          </div>
        </header>
      </section>

      <div className="ws-metrics">
        <div className="ws-metric">
          <strong>{counts.total}</strong>
          <span>findings</span>
        </div>
        <div className="ws-metric">
          <strong>{counts.confirmed + counts.suspicious}</strong>
          <span>actionable</span>
        </div>
        <div className="ws-metric">
          <strong>{sources.collectedCount ?? "—"}</strong>
          <span>layers checked</span>
        </div>
        <div className="ws-metric">
          <strong>{verdict.engineScore}</strong>
          <span>engine score</span>
        </div>
      </div>

      <Panel
        icon={AlertTriangle}
        title="Top findings"
        text="Highest severity first — open a row for full investigative detail."
      >
        {top.length ? (
          <ul className="ws-findings-preview">
            {top.map((finding) => (
              <li key={finding.id}>
                <button type="button" className="ws-findings-preview__row" onClick={() => onOpenFinding(finding.id)}>
                  <SeverityBadge severity={finding.severity} compact />
                  <span className="ws-findings-preview__title">{finding.title}</span>
                  <ConfidenceChip tier={finding.confidenceTier} />
                  <StatusChip status={finding.status} />
                  <ChevronRight size={14} aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <div className="ws-empty-state">
            <p>No investigative findings on this scan.</p>
          </div>
        )}
      </Panel>

      {(env.os || env.boot_time || defenderView.available) && (
        <Panel icon={Shield} title="Environment" text="Host context collected with the report." compact>
          <dl className="ws-env-grid">
            {env.os ? (
              <>
                <dt>OS</dt>
                <dd>{env.os}</dd>
              </>
            ) : null}
            {env.boot_time ? (
              <>
                <dt>Last boot</dt>
                <dd>{formatGmtPlus3(env.boot_time)}</dd>
              </>
            ) : null}
            {report.generated_at ? (
              <>
                <dt>Scan time</dt>
                <dd>{formatGmtPlus3(report.generated_at)}</dd>
              </>
            ) : null}
            {defenderView.available ? (
              <>
                <dt>Defender</dt>
                <dd>{defenderView.statusLabel}</dd>
              </>
            ) : null}
          </dl>
        </Panel>
      )}
    </>
  );
}

function FindingDetail({ finding, formatGmtPlus3, onClose }) {
  if (!finding) return null;
  return (
    <aside className="ws-finding-detail" aria-label="Finding detail">
      <header className="ws-finding-detail__head">
        <div>
          <div className="ws-finding-detail__meta">
            <SeverityBadge severity={finding.severity} />
            <ConfidenceChip tier={finding.confidenceTier} />
            <StatusChip status={finding.status} />
          </div>
          <h3>{finding.title}</h3>
          <p className="ws-mono muted">{finding.category} · {finding.detectionMethod}</p>
        </div>
        <button type="button" className="ws-icon-btn" onClick={onClose} aria-label="Close detail">
          <X size={16} />
        </button>
      </header>

      <section>
        <h4>Why flagged</h4>
        <p>{finding.whyFlagged}</p>
      </section>

      <section>
        <h4>Evidence</h4>
        {finding.evidence?.length ? (
          <ul className="ws-evidence-list">
            {finding.evidence.map((item, index) => (
              <li key={`${item.label}-${index}`}>
                <span className="ws-eyebrow">{item.label}</span>
                <p className={item.kind === "hash" || item.kind === "path" ? "ws-mono" : ""}>{item.value}</p>
                {item.timestamp ? <time>{formatGmtPlus3(item.timestamp)}</time> : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No structured evidence excerpts.</p>
        )}
      </section>

      <section>
        <h4>Assessment</h4>
        <dl className="ws-env-grid">
          <dt>Severity</dt>
          <dd>{finding.severity}</dd>
          <dt>Confidence</dt>
          <dd>
            {finding.confidenceTier}
            {finding.confidence != null ? ` (${confidencePct(finding)})` : ""}
          </dd>
          <dt>Status</dt>
          <dd>{finding.status}</dd>
          {finding.location ? (
            <>
              <dt>Location</dt>
              <dd className="ws-mono">{finding.location}</dd>
            </>
          ) : null}
          {finding.timestamp ? (
            <>
              <dt>Timestamp</dt>
              <dd>{formatGmtPlus3(finding.timestamp)}</dd>
            </>
          ) : null}
          {finding.hashes?.length ? (
            <>
              <dt>Hashes</dt>
              <dd className="ws-mono">{finding.hashes.join("\n")}</dd>
            </>
          ) : null}
          {finding.relatedIds?.length ? (
            <>
              <dt>Related</dt>
              <dd>{finding.relatedIds.length} linked finding(s)</dd>
            </>
          ) : null}
        </dl>
      </section>

      <section>
        <h4>Recommended action</h4>
        <p>{finding.recommendedAction}</p>
      </section>
    </aside>
  );
}

function FindingsTab({
  findings,
  formatGmtPlus3,
  selectedId,
  setSelectedId,
  searchRef,
}) {
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState([]);
  const [confidence, setConfidence] = useState([]);
  const [category, setCategory] = useState([]);
  const [status, setStatus] = useState([]);
  const [sortKey, setSortKey] = useState("severity");
  const listRef = useRef(null);

  const categories = useMemo(() => {
    const set = new Set(findings.map((f) => f.category).filter(Boolean));
    return [...set].sort();
  }, [findings]);

  const filtered = useMemo(
    () =>
      sortFindings(
        filterFindings(findings, { query, severity, confidence, category, status }),
        sortKey,
      ),
    [findings, query, severity, confidence, category, status, sortKey],
  );

  const selected = filtered.find((f) => f.id === selectedId) || findings.find((f) => f.id === selectedId) || null;
  const selectedIndex = filtered.findIndex((f) => f.id === selectedId);

  const toggleFilter = (list, setList, value) => {
    setList((prev) => (prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]));
  };

  useEffect(() => {
    if (!filtered.length) return;
    if (selectedId === undefined) {
      setSelectedId(filtered[0].id);
      return;
    }
    if (selectedId === null) return;
    if (!filtered.some((f) => f.id === selectedId)) {
      setSelectedId(filtered[0].id);
    }
  }, [filtered, selectedId, setSelectedId]);

  const onListKeyDown = useCallback(
    (event) => {
      if (!filtered.length) return;
      if (event.key === "ArrowDown") {
        event.preventDefault();
        const next = Math.min(filtered.length - 1, Math.max(0, selectedIndex) + 1);
        setSelectedId(filtered[next].id);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        const next = Math.max(0, (selectedIndex < 0 ? 0 : selectedIndex) - 1);
        setSelectedId(filtered[next].id);
      } else if (event.key === "Escape") {
        setSelectedId(null);
      }
    },
    [filtered, selectedIndex, setSelectedId],
  );

  return (
    <div className="ws-findings-layout">
      <div className="ws-findings-main">
        <div className="ws-findings-toolbar">
          <label className="ws-search">
            <Search size={14} aria-hidden />
            <input
              ref={searchRef}
              type="search"
              placeholder="Search findings… (/)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <select value={sortKey} onChange={(e) => setSortKey(e.target.value)} aria-label="Sort findings">
            <option value="severity">Sort: severity</option>
            <option value="confidence">Sort: confidence</option>
            <option value="time">Sort: time</option>
            <option value="title">Sort: title</option>
            <option value="status">Sort: status</option>
            <option value="category">Sort: category</option>
          </select>
          {(query || severity.length || confidence.length || category.length || status.length) ? (
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => {
                setQuery("");
                setSeverity([]);
                setConfidence([]);
                setCategory([]);
                setStatus([]);
              }}
            >
              Clear filters
            </button>
          ) : null}
        </div>

        <div className="ws-filter-groups">
          <FilterGroup
            label="Severity"
            options={SEVERITY_OPTIONS}
            selected={severity}
            onToggle={(v) => toggleFilter(severity, setSeverity, v)}
          />
          <FilterGroup
            label="Confidence"
            options={CONFIDENCE_OPTIONS}
            selected={confidence}
            onToggle={(v) => toggleFilter(confidence, setConfidence, v)}
          />
          <FilterGroup
            label="Status"
            options={STATUS_OPTIONS}
            selected={status}
            onToggle={(v) => toggleFilter(status, setStatus, v)}
          />
          {categories.length ? (
            <FilterGroup
              label="Category"
              options={categories}
              selected={category}
              onToggle={(v) => toggleFilter(category, setCategory, v)}
            />
          ) : null}
        </div>

        <div
          className="ws-findings-table-wrap"
          ref={listRef}
          tabIndex={0}
          onKeyDown={onListKeyDown}
          role="listbox"
          aria-label="Findings list"
        >
          <table className="ws-findings-table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Finding</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length ? (
                filtered.map((finding) => {
                  const active = finding.id === selectedId;
                  return (
                    <tr
                      key={finding.id}
                      role="option"
                      aria-selected={active}
                      className={active ? "is-active" : ""}
                      onClick={() => setSelectedId(finding.id)}
                    >
                      <td>
                        <SeverityBadge severity={finding.severity} compact />
                      </td>
                      <td>
                        <strong>{finding.title}</strong>
                        <span className="ws-findings-table__sub">{finding.category}</span>
                      </td>
                      <td>
                        <div className="ws-conf-cell">
                          <ConfidenceChip tier={finding.confidenceTier} />
                          <span className="ws-mono muted">{confidencePct(finding)}</span>
                        </div>
                      </td>
                      <td>
                        <StatusChip status={finding.status} />
                      </td>
                      <td className="ws-mono">
                        {finding.timestamp ? formatGmtPlus3(finding.timestamp) : "—"}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={5} className="ws-empty">
                    No findings match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selected ? (
        <FindingDetail
          finding={selected}
          formatGmtPlus3={formatGmtPlus3}
          onClose={() => setSelectedId(null)}
        />
      ) : (
        <aside className="ws-finding-detail ws-finding-detail--empty" aria-label="Finding detail">
          <p className="muted">Select a finding to inspect severity, confidence, and evidence separately.</p>
        </aside>
      )}
    </div>
  );
}

function FilterGroup({ label, options, selected, onToggle }) {
  return (
    <div className="ws-filter-group">
      <span className="ws-eyebrow">{label}</span>
      <div className="ws-filter-row">
        {options.map((option) => (
          <button
            key={option}
            type="button"
            className={selected.includes(option) ? "active" : ""}
            onClick={() => onToggle(option)}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}

function TimelineTab({ review, activity, activityEventSummary, formatGmtPlus3 }) {
  const block = review.last_computer_activity ?? {};
  let events = block.events ?? [];
  if (!events.length && (activity?.events ?? []).length) {
    events = (activity.events ?? [])
      .filter((e) => e.occurred_at || e.category === "execution" || e.time_unknown)
      .map((e) => ({
        occurred_at: e.occurred_at,
        summary: activityEventSummary ? activityEventSummary(e) : e.summary || e.label,
        path: e.path,
        category: e.category,
        time_unknown: e.time_unknown,
        name: e.name,
        location_hint: e.location_hint,
      }));
  }
  events = [...events].sort((a, b) => {
    const aMs = a.occurred_at ? new Date(a.occurred_at).getTime() : 0;
    const bMs = b.occurred_at ? new Date(b.occurred_at).getTime() : 0;
    return bMs - aMs;
  });

  return (
    <Panel icon={Clock} title="Activity timeline" text="Chronological events from scan review.">
      {events.length ? (
        <ul className="ws-timeline">
          {events.slice(0, 80).map((event, index) => (
            <li key={`${event.path}-${event.occurred_at}-${index}`}>
              <time>{event.occurred_at ? formatGmtPlus3(event.occurred_at) : "—"}</time>
              <div>
                <p>{event.summary || "Activity recorded"}</p>
                <LocationHint row={event} path={event.path} />
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No timeline events on this scan.</p>
      )}
    </Panel>
  );
}

function EvidenceTab({ review, report, formatGmtPlus3 }) {
  const sec = report.security_integrity_signals ?? {};
  const verdictChains = sec.evidence_verdict?.provenance_chains ?? [];
  const chains = verdictChains.length ? verdictChains : review.evidence_chains?.chains ?? [];
  const sources = forensicSourcesView(sec);

  return (
    <>
      <Panel
        icon={Link2}
        title="Provenance chains"
        text="Related traces grouped when multiple sources agree."
      >
        {chains.length ? (
          <ul className="ws-chain-list">
            {chains.map((chain, index) => (
              <li key={`${chain.stem}-${index}`} className="ws-chain-card">
                <div className="ws-chain-card__head">
                  <strong>
                    {publicFindingLabels(chain.labels ?? []).join(", ") ||
                      chain.stem ||
                      "Related activity"}
                  </strong>
                  <ConfidenceChip tier={chain.confidence_tier || chain.confidence || "medium"} />
                </div>
                <p>{chain.summary}</p>
                <ol className="ws-chain-steps">
                  {(chain.steps ?? []).map((step, stepIndex) => (
                    <li key={`${step.source}-${step.path}-${stepIndex}`}>
                      <div className="ws-chain-step-meta">
                        <span>{step.action || step.source || "trace"}</span>
                        <time>
                          {step.occurred_at ? formatGmtPlus3(step.occurred_at) : "Time unknown"}
                        </time>
                      </div>
                      <p>{step.detail || step.summary || privacyPath(step.path) || "Related trace"}</p>
                      <LocationHint row={step} path={step.path} />
                    </li>
                  ))}
                </ol>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No provenance chains on this scan.</p>
        )}
      </Panel>

      {sources.available ? (
        <Panel icon={FolderSearch} title="Trace layers checked" text={sources.summary}>
          <ul className="ws-trace-list">
            {sources.sources.map((row) => (
              <li key={row.id} className={`ws-trace-row ws-trace-row--${row.tone}`}>
                <span>{row.statusLabel}</span>
                <strong>{row.label}</strong>
                {row.count > 0 ? <em className="muted">{row.count}</em> : null}
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
    </>
  );
}

function robloxHeadshotUrl(account) {
  return account.headshot_url || null;
}

function discordAvatarUrl(account) {
  const userId = String(account.user_id || "");
  if (!userId) return null;
  const hash = account.avatar_hash;
  if (hash) return `https://cdn.discordapp.com/avatars/${userId}/${hash}.png?size=128`;
  try {
    const avatarIndex = Number((BigInt(userId) >> 22n) % 6n);
    return `https://cdn.discordapp.com/embed/avatars/${avatarIndex}.png`;
  } catch {
    return null;
  }
}

function AccountsTab({ report, token }) {
  const roblox = report.application_diagnostics?.roblox ?? {};
  const discord = report.application_diagnostics?.discord ?? {};
  const robloxAccounts = useMemo(() => collectRobloxAccountsFromReport(roblox), [roblox]);
  const discordAccounts = useMemo(
    () => collectDiscordAccountsFromReport(discord, report),
    [discord, report],
  );
  const [profiles, setProfiles] = useState({});

  useEffect(() => {
    const userIds = robloxAccounts.map((a) => a.user_id).filter(Boolean);
    if (!token || !userIds.length) {
      setProfiles({});
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`${API_URL}/roblox/profiles`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ user_ids: userIds }),
        });
        if (!response.ok || cancelled) return;
        const payload = await response.json();
        const next = {};
        for (const profile of payload.profiles ?? []) {
          if (profile?.user_id) next[String(profile.user_id)] = profile;
        }
        if (!cancelled) setProfiles(next);
      } catch {
        if (!cancelled) setProfiles({});
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [robloxAccounts, token]);

  return (
    <>
      <Panel icon={Users} title="Roblox accounts" text="Detected in client, browser, or local storage.">
        {robloxAccounts.length ? (
          <div className="ws-account-grid">
            {robloxAccounts.slice(0, 24).map((account) => {
              const resolved = profiles[account.user_id] ?? {};
              const displayName = account.username || resolved.username || `Account ${account.user_id}`;
              const avatar = robloxHeadshotUrl({ ...account, headshot_url: resolved.headshot_url });
              return (
                <a
                  key={account.user_id}
                  href={`https://www.roblox.com/users/${encodeURIComponent(account.user_id)}/profile`}
                  target="_blank"
                  rel="noreferrer"
                  className="ws-account-card"
                >
                  {avatar ? (
                    <img src={avatar} alt="" className="ws-account-card__avatar" loading="lazy" />
                  ) : (
                    <span className="ws-account-card__avatar" aria-hidden />
                  )}
                  <span className="ws-account-card__body">
                    <span className="ws-account-card__name">{displayName}</span>
                    <span className="ws-account-card__link">View profile</span>
                  </span>
                </a>
              );
            })}
          </div>
        ) : (
          <p className="muted">No Roblox accounts found on this device.</p>
        )}
      </Panel>

      <Panel icon={Users} title="Discord accounts" text="Detected in Discord app or browser login.">
        {discordAccounts.length ? (
          <div className="ws-account-grid">
            {discordAccounts.slice(0, 24).map((account) => {
              const userId = String(account.user_id || "");
              const displayName = account.display_name || `User ${userId}`;
              const avatar = account.avatar_url || discordAvatarUrl(account);
              return (
                <div key={userId} className="ws-account-card ws-account-card--static">
                  {avatar ? (
                    <img src={avatar} alt="" className="ws-account-card__avatar" loading="lazy" />
                  ) : (
                    <span className="ws-account-card__avatar" aria-hidden />
                  )}
                  <span className="ws-account-card__body">
                    <span className="ws-account-card__name">{displayName}</span>
                    <span className="ws-account-card__link">Discord account</span>
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="muted">No Discord accounts found on this device.</p>
        )}
      </Panel>
    </>
  );
}

function downloadBlob(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function ExportTab({ detail, report, summary, findings, brandName }) {
  const pin = detail?.pin || "scan";

  return (
    <Panel icon={Download} title="Export" text="Download or print a professional investigation package.">
      <div className="ws-export-actions">
        <button
          type="button"
          className="btn btn--primary btn--sm"
          onClick={() =>
            downloadBlob(
              `virello-findings-${pin}.json`,
              JSON.stringify({ pin, generated_at: new Date().toISOString(), findings }, null, 2),
              "application/json",
            )
          }
        >
          <FileJson size={14} />
          Findings JSON
        </button>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() =>
            downloadBlob(`virello-findings-${pin}.csv`, findingsToCsv(findings), "text/csv;charset=utf-8")
          }
        >
          <FileSpreadsheet size={14} />
          Findings CSV
        </button>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() =>
            downloadBlob(
              `virello-report-${pin}.json`,
              JSON.stringify(detail ?? { report, summary }, null, 2),
              "application/json",
            )
          }
        >
          <FileText size={14} />
          Full report JSON
        </button>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => exportReportPdf({ detail, report, summary, findings, brandName })}
        >
          <Printer size={14} />
          Print / HTML report
        </button>
      </div>
      <p className="muted ws-export-note">
        Exported findings keep path privacy redaction. Indicators assist review and are not automatic guilt.
      </p>
    </Panel>
  );
}

function CompareControl({ sessions, detail, report, summary, token }) {
  const candidates = useMemo(() => {
    if (!sessions?.length || !detail?.id) return [];
    return sessions.filter((s) => s.status === "completed" && s.id !== detail.id);
  }, [sessions, detail?.id]);

  const [compareId, setCompareId] = useState("");
  const [prevPayload, setPrevPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!compareId || !token) {
      setPrevPayload(null);
      setError("");
      setLoading(false);
      return undefined;
    }
    const cached = candidates.find((s) => String(s.id) === String(compareId));
    if (cached?.report) {
      setPrevPayload({ report: cached.report, summary: null });
      setError("");
      setLoading(false);
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    setError("");
    setPrevPayload(null);
    (async () => {
      try {
        const response = await fetch(`${API_URL}/sessions/${compareId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) throw new Error(`Compare load failed (${response.status})`);
        const data = await response.json();
        if (cancelled) return;
        if (!data?.report) throw new Error("Selected scan has no report payload");
        setPrevPayload({ report: data.report, summary: null });
      } catch (caught) {
        if (!cancelled) {
          setPrevPayload(null);
          setError(caught.message || "Could not load comparison scan");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [candidates, compareId, token]);

  const comparison = useMemo(() => {
    if (!prevPayload?.report) return null;
    return compareSessions(prevPayload.report, report, prevPayload.summary, summary);
  }, [prevPayload, report, summary]);

  if (!candidates.length) return null;

  return (
    <div className="ws-compare">
      <div className="ws-compare__controls">
        <label>
          <span className="ws-eyebrow">Compare scans</span>
          <select value={compareId} onChange={(e) => setCompareId(e.target.value)}>
            <option value="">Compare with previous completed scan…</option>
            {candidates.map((s) => (
              <option key={s.id} value={s.id}>
                PIN {s.pin} · #{s.id}
                {s.completed_at ? ` · ${String(s.completed_at).slice(0, 10)}` : ""}
              </option>
            ))}
          </select>
        </label>
        {loading ? <span className="muted">Loading prior scan…</span> : null}
        {error ? <span className="ws-compare__error">{error}</span> : null}
        {comparison ? (
          <div className="ws-compare__summary">
            <span>+{comparison.summary.addedCount} added</span>
            <span>−{comparison.summary.removedCount} removed</span>
            <span>~{comparison.summary.changedCount} changed</span>
            <span>
              {comparison.summary.previousCount} → {comparison.summary.currentCount}
            </span>
          </div>
        ) : null}
      </div>

      {comparison ? (
        <div className="ws-compare__diff">
          <CompareDiffColumn
            title="Added"
            empty="No new findings versus prior scan."
            items={comparison.added}
          />
          <CompareDiffColumn
            title="Removed"
            empty="Nothing dropped versus prior scan."
            items={comparison.removed}
          />
          <CompareDiffColumn
            title="Changed"
            empty="No severity/confidence/status shifts."
            items={comparison.changed.map((row) => ({
              id: row.current.id,
              title: row.current.title,
              severity: row.current.severity,
              confidenceTier: row.current.confidenceTier,
              status: row.current.status,
              note: `${row.previous.severity}/${row.previous.confidenceTier}/${row.previous.status} → ${row.current.severity}/${row.current.confidenceTier}/${row.current.status}`,
            }))}
          />
        </div>
      ) : null}
    </div>
  );
}

function CompareDiffColumn({ title, empty, items }) {
  return (
    <section className="ws-compare__col">
      <h4>
        {title} <em>{items.length}</em>
      </h4>
      {items.length ? (
        <ul>
          {items.slice(0, 12).map((item) => (
            <li key={item.id}>
              <SeverityBadge severity={item.severity} compact />
              <div>
                <strong>{item.title}</strong>
                <span>
                  {item.confidenceTier} conf · {item.status}
                  {item.note ? ` · ${item.note}` : ""}
                </span>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">{empty}</p>
      )}
    </section>
  );
}

/**
 * Professional investigation console.
 * Compatible props: report, summary, activity, activityEventSummary, formatGmtPlus3, token
 * Optional: detail, sessions, brandName
 */
export function SimpleResults({
  report,
  summary,
  activity,
  activityEventSummary,
  formatGmtPlus3,
  token,
  detail = null,
  sessions = null,
  brandName = "Virello Scanner",
}) {
  const [tab, setTab] = useState("overview");
  // undefined = auto-select first; null = user closed detail panel
  const [selectedFindingId, setSelectedFindingId] = useState(undefined);
  const searchRef = useRef(null);

  const review = useMemo(() => scanReviewFromReport(report), [report]);
  const findings = useMemo(() => buildInvestigationFindings(report, summary), [report, summary]);
  const counts = useMemo(() => severityCounts(findings), [findings]);
  const verdict = useMemo(() => engineVerdictPlain(report, summary), [report, summary]);

  const openFinding = useCallback((id) => {
    setSelectedFindingId(id);
    setTab("findings");
  }, []);

  useEffect(() => {
    function onKey(event) {
      const tag = event.target?.tagName;
      const typing = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || event.target?.isContentEditable;
      if (event.key === "/" && !typing && !event.metaKey && !event.ctrlKey && !event.altKey) {
        event.preventDefault();
        setTab("findings");
        requestAnimationFrame(() => searchRef.current?.focus());
      }
      if (event.key === "Escape" && selectedFindingId) {
        setSelectedFindingId(null);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedFindingId]);

  return (
    <div className="ws-simple">
      <nav className="ws-review-nav" aria-label="Investigation sections">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`ws-review-nav__tab ${tab === id ? "ws-review-nav__tab--active" : ""}`}
            onClick={() => setTab(id)}
          >
            <Icon size={15} strokeWidth={1.75} aria-hidden />
            {label}
            {id === "findings" && counts.total ? <em>{counts.total}</em> : null}
          </button>
        ))}
      </nav>

      {sessions?.length ? (
        <CompareControl
          sessions={sessions}
          detail={detail}
          report={report}
          summary={summary}
          token={token}
        />
      ) : null}

      <div className="ws-simple__content">
        {tab === "overview" ? (
          <OverviewTab
            verdict={verdict}
            findings={findings}
            counts={counts}
            report={report}
            formatGmtPlus3={formatGmtPlus3}
            onOpenFinding={openFinding}
          />
        ) : null}
        {tab === "findings" ? (
          <FindingsTab
            findings={findings}
            formatGmtPlus3={formatGmtPlus3}
            selectedId={selectedFindingId}
            setSelectedId={setSelectedFindingId}
            searchRef={searchRef}
          />
        ) : null}
        {tab === "timeline" ? (
          <TimelineTab
            review={review}
            activity={activity}
            activityEventSummary={activityEventSummary}
            formatGmtPlus3={formatGmtPlus3}
          />
        ) : null}
        {tab === "evidence" ? (
          <EvidenceTab review={review} report={report} formatGmtPlus3={formatGmtPlus3} />
        ) : null}
        {tab === "accounts" ? <AccountsTab report={report} token={token} /> : null}
        {tab === "export" ? (
          <ExportTab
            detail={detail}
            report={report}
            summary={summary}
            findings={findings}
            brandName={brandName}
          />
        ) : null}
      </div>
    </div>
  );
}
