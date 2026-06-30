import React, { useEffect, useMemo, useState } from "react";
import { MaterialIcon } from "./components/MaterialIcon.jsx";
import { SeverityBadge, severityRank } from "./components/SeverityBadge.jsx";
import { defenderSummary } from "./defenderSignals.js";
import { scanReviewFromReport } from "./reportDigest.js";
import { formatDisplayLocation, privacyPath, publicFindingLabels } from "./resultPrivacy.js";
import {
  collectRobloxAccountsFromReport,
  collectDiscordAccountsFromReport,
} from "./accountExtract.js";
import { genericFindingTitle, genericReasonLabel, genericReasonDetail } from "./reviewerCopy.js";
import { forensicSourcesView, securitySignalsView } from "./forensicSources.js";

const API_URL = import.meta.env.VITE_API_URL || "https://virello-secure.onrender.com";

const TABS = [
  { id: "summary", label: "Summary", icon: "description" },
  { id: "findings", label: "Findings", icon: "shield_alert" },
  { id: "traces", label: "Traces", icon: "fact_check" },
  { id: "security", label: "Security", icon: "shield" },
  { id: "activity", label: "Activity", icon: "history" },
  { id: "accounts", label: "Accounts", icon: "users" },
];

const VERDICT_META = {
  clean: { label: "Looks clear", tone: "clean", blurb: "Nothing major stood out on this scan." },
  watch: { label: "Review recommended", tone: "watch", blurb: "Some warning signs need a closer look." },
  bad: { label: "High concern", tone: "bad", blurb: "Multiple warning signs — review carefully." },
};

function simpleVerdict(score, bypassRisk) {
  const combined = Math.min(100, Math.round(score * 0.75 + (bypassRisk || 0) * 0.35));
  if (combined >= 70) return { ...VERDICT_META.bad, combined };
  if (combined >= 35) return { ...VERDICT_META.watch, combined };
  return { ...VERDICT_META.clean, combined };
}

function buildProblems(report, summary) {
  const sec = report.security_integrity_signals ?? {};
  const bypass = sec.bypass_resilience ?? {};
  const problems = [];

  for (const row of bypass.findings ?? []) {
    problems.push({
      id: `bypass-${row.title}`,
      severity: row.severity || "medium",
      title: genericFindingTitle(row.title),
      detail: genericReasonDetail(row.title, row.detail),
    });
  }

  for (const reason of summary.reasons ?? []) {
    if (!reason.points) continue;
    problems.push({
      id: `score-${reason.label}`,
      severity: reason.points >= 20 ? "high" : reason.points >= 10 ? "medium" : "low",
      title: genericReasonLabel(reason.label),
      detail: genericReasonDetail(reason.label, reason.detail),
    });
  }

  const seen = new Set();
  return problems
    .filter((p) => {
      if (seen.has(p.title)) return false;
      seen.add(p.title);
      return true;
    })
    .sort((a, b) => severityRank(a.severity) - severityRank(b.severity));
}

function PanelHeader({ icon, title, text }) {
  return (
    <header className="ws-panel__head">
      <MaterialIcon name={icon} size={20} />
      <div>
        <h4>{title}</h4>
        {text ? <p>{text}</p> : null}
      </div>
    </header>
  );
}

function FindingRow({ problem, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <article className={`ws-finding ws-finding--${problem.severity}`}>
      <button type="button" className="ws-finding__toggle" onClick={() => setOpen((v) => !v)}>
        <SeverityBadge severity={problem.severity} />
        <strong>{problem.title}</strong>
        <MaterialIcon name="chevron_right" size={16} className={open ? "open" : ""} />
      </button>
      {open ? <p className="ws-finding__detail">{problem.detail}</p> : null}
    </article>
  );
}

function LocationHint({ row, path }) {
  const text = formatDisplayLocation(row) || privacyPath(path);
  if (!text) return null;
  return <span className="simple-location-hint muted">{text}</span>;
}

function SummaryTab({ verdict, problems, review, report, formatGmtPlus3 }) {
  const activity = review.last_computer_activity ?? {};
  const deletionCount = (activity.events ?? []).filter((event) => {
    const summary = String(event.summary || "").toLowerCase();
    return event.category === "deletions" || summary.includes("no longer on disk");
  }).length;
  const defenderView = defenderSummary(report.security_integrity_signals?.defender);

  return (
    <>
      <div className="ws-bento">
        <section className={`ws-bento__verdict ws-bento__verdict--${verdict.tone}`}>
          <p className="ws-bento__verdict-label">Assessment</p>
          <h3>{verdict.label}</h3>
          <p>{verdict.blurb}</p>
        </section>
        <section className="ws-bento__meter" aria-label={`Concern level ${verdict.combined} out of 100`}>
          <strong>{verdict.combined}</strong>
          <span>concern level</span>
        </section>
      </div>

      <section className="ws-metrics">
        <div className="ws-metric">
          <strong>{problems.length}</strong>
          <span>warning signs</span>
        </div>
        <div className="ws-metric">
          <strong>{review.evidence_chains?.chain_count ?? 0}</strong>
          <span>linked traces</span>
        </div>
        <div className="ws-metric">
          <strong>{deletionCount}</strong>
          <span>deletions logged</span>
        </div>
        <div className="ws-metric">
          <strong>{review.download_history?.suspicious_count ?? 0}</strong>
          <span>flagged downloads</span>
        </div>
      </section>

      {problems.length ? (
        <section className="ws-panel">
          <PanelHeader icon="priority_high" title="Top concerns" text="Most important items first." />
          <div className="ws-panel__body">
            {problems.slice(0, 5).map((problem, index) => (
              <FindingRow key={problem.id} problem={problem} defaultOpen={index === 0} />
            ))}
          </div>
        </section>
      ) : (
        <div className="ws-empty-state">
          <MaterialIcon name="check_circle" size={28} />
          <p>Nothing concerning stood out on this scan.</p>
        </div>
      )}

      {defenderView.available ? (
        <section className="ws-panel ws-panel--compact">
          <PanelHeader icon="shield" title="Windows security" text={defenderView.statusLabel} />
        </section>
      ) : null}
    </>
  );
}

const CHAIN_ACTION_LABELS = {
  executed: "Ran",
  ran: "Ran",
  downloaded: "Downloaded",
  deleted: "Deleted",
  on_disk: "On disk",
  known_hash: "Known match",
  removed_trace: "Trace remains",
  filesystem: "File system",
  correlated: "Linked",
  traced: "Traced",
};

function FindingsTab({ problems, review, formatGmtPlus3 }) {
  const chains = review.evidence_chains?.chains ?? [];
  const programs = (review.executable_inventory?.items ?? []).filter((row) => row.suspicious);
  const sortedChains = [...chains].sort((a, b) => {
    const aHigh = a.confidence === "high" ? 0 : 1;
    const bHigh = b.confidence === "high" ? 0 : 1;
    return aHigh - bHigh;
  });

  return (
    <>
      <section className="ws-panel">
        <PanelHeader icon="list_checks" title="Warning signs" text="Sorted by importance." />
        <div className="ws-panel__body">
          {problems.length ? (
            problems.map((problem) => <FindingRow key={problem.id} problem={problem} />)
          ) : (
            <p className="muted">No warning signs on this scan.</p>
          )}
        </div>
      </section>

      {sortedChains.length ? (
        <section className="ws-panel">
          <PanelHeader icon="git_branch" title="Linked traces" text="Related activity grouped together." />
          <div className="ws-panel__body">
            <ul className="simple-chain-list">
              {sortedChains.map((chain) => (
                <li key={chain.stem} className={`simple-chain-card simple-chain-card--${chain.confidence || "medium"}`}>
                  <div className="simple-chain-head">
                    <strong>{chain.labels?.length ? chain.labels.join(", ") : "Related activity"}</strong>
                    <SeverityBadge
                      severity={chain.confidence === "high" ? "high" : "medium"}
                      compact
                    />
                  </div>
                  <p>{chain.summary}</p>
                  <ol className="simple-chain-steps">
                    {(chain.steps ?? []).map((step, index) => (
                      <li key={`${step.source}-${step.path}-${index}`}>
                        <div className="simple-chain-step-meta">
                          <span className="simple-chain-step-action">
                            {CHAIN_ACTION_LABELS[step.action] || step.action}
                          </span>
                          <time>{step.occurred_at ? formatGmtPlus3(step.occurred_at) : "Time unknown"}</time>
                        </div>
                        <p>{step.detail}</p>
                        <LocationHint row={step} path={step.path} />
                      </li>
                    ))}
                  </ol>
                </li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}

      {programs.length ? (
        <section className="ws-panel">
          <PanelHeader icon="file_code" title="Flagged programs" text="Files that matched review rules." />
          <div className="ws-panel__body">
            <ul className="simple-program-list">
              {programs.slice(0, 30).map((row, index) => (
                <li key={`${row.path}-${index}`} className="simple-program--warn">
                  <div>
                    <strong>{row.name || row.file_name || "File"}</strong>
                    {row.labels?.length ? (
                      <span className="simple-tag">{publicFindingLabels(row.labels).join(", ")}</span>
                    ) : null}
                    <p className="muted">
                      {row.file_exists === false ? "Removed from disk · " : ""}
                      Last seen {row.last_seen ? formatGmtPlus3(row.last_seen) : "unknown"}
                    </p>
                  </div>
                  <LocationHint row={row} path={row.path} />
                </li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}
    </>
  );
}

const ACTIVITY_VIEWS = [
  { id: "timeline", label: "Timeline" },
  { id: "downloads", label: "Downloads" },
  { id: "programs", label: "Programs run" },
  { id: "deletions", label: "Deletions" },
];

function ActivityTab({ review, activity, activityEventSummary, formatGmtPlus3 }) {
  const [view, setView] = useState("timeline");
  const block = review.last_computer_activity ?? {};
  let events = block.events ?? [];
  if (!events.length && (activity?.events ?? []).length) {
    events = (activity.events ?? [])
      .filter((e) => e.occurred_at || e.category === "execution" || e.time_unknown)
      .map((e) => ({
        occurred_at: e.occurred_at,
        summary: activityEventSummary(e),
        path: e.path,
        category: e.category,
        time_unknown: e.time_unknown,
      }));
  }
  events = [...events].sort((a, b) => {
    const aMs = a.occurred_at ? new Date(a.occurred_at).getTime() : 0;
    const bMs = b.occurred_at ? new Date(b.occurred_at).getTime() : 0;
    return bMs - aMs;
  });

  const downloads = [...(review.download_history?.items ?? [])].sort((a, b) => {
    if (a.suspicious !== b.suspicious) return a.suspicious ? -1 : 1;
    const aMs = a.started_at ? new Date(a.started_at).getTime() : 0;
    const bMs = b.started_at ? new Date(b.started_at).getTime() : 0;
    return bMs - aMs;
  });

  const executions = [...(review.execution_activity?.items ?? [])].sort((a, b) => {
    if (a.suspicious !== b.suspicious) return a.suspicious ? -1 : 1;
    const aMs = a.occurred_at ? new Date(a.occurred_at).getTime() : 0;
    const bMs = b.occurred_at ? new Date(b.occurred_at).getTime() : 0;
    return bMs - aMs;
  });

  const deletions = events.filter((event) => {
    const summary = String(event.summary || "").toLowerCase();
    return event.category === "deletions" || summary.includes("no longer on disk") || summary.includes("recycle");
  });

  return (
    <section className="ws-panel">
      <PanelHeader icon="history" title="Activity" text="Recent events on this PC." />
      <div className="ws-panel__body">
        <div className="ws-filter-row">
          {ACTIVITY_VIEWS.map((row) => (
            <button
              key={row.id}
              type="button"
              className={view === row.id ? "active" : ""}
              onClick={() => setView(row.id)}
            >
              {row.label}
            </button>
          ))}
        </div>

        {view === "timeline" ? (
          events.length ? (
            <ul className="ws-timeline">
              {events.slice(0, 40).map((event, index) => (
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
          )
        ) : null}

        {view === "downloads" ? (
          downloads.length ? (
            <ul className="simple-timeline">
              {downloads.slice(0, 40).map((row, index) => (
                <li
                  key={`${row.target_path}-${row.started_at}-${index}`}
                  className={row.suspicious ? "simple-timeline--warn" : ""}
                >
                  <time>{row.started_at ? formatGmtPlus3(row.started_at) : "—"}</time>
                  <p>
                    <strong>{row.file_name || "Download"}</strong> via {row.browser || "browser"}
                  </p>
                  {row.matched_labels?.length ? (
                    <p className="muted">{publicFindingLabels(row.matched_labels).join(", ")}</p>
                  ) : null}
                  <LocationHint row={row} path={row.target_path} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No download history found.</p>
          )
        ) : null}

        {view === "programs" ? (
          executions.length ? (
            <ul className="simple-timeline">
              {executions.slice(0, 40).map((row, index) => (
                <li
                  key={`${row.path}-${row.occurred_at}-${index}`}
                  className={row.suspicious ? "simple-timeline--warn" : ""}
                >
                  <time>{row.occurred_at ? formatGmtPlus3(row.occurred_at) : "—"}</time>
                  <p>
                    <strong>{row.name || row.file_name || "Program"}</strong> {row.summary}
                  </p>
                  <LocationHint row={row} path={row.path} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No program execution traces found.</p>
          )
        ) : null}

        {view === "deletions" ? (
          deletions.length ? (
            <ul className="simple-timeline">
              {deletions.slice(0, 40).map((event, index) => (
                <li key={`${event.path}-${event.occurred_at}-${index}`} className="simple-timeline--warn">
                  <time>{event.occurred_at ? formatGmtPlus3(event.occurred_at) : "—"}</time>
                  <p>{event.summary || "File removed or deleted"}</p>
                  <LocationHint row={event} path={event.path} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No deletion events recorded on this scan.</p>
          )
        ) : null}
      </div>
    </section>
  );
}

function TracesTab({ report }) {
  const view = forensicSourcesView(report.security_integrity_signals ?? {});

  if (!view.available) {
    return (
      <section className="ws-panel">
        <PanelHeader icon="fact_check" title="Trace layers" text={view.summary} />
      </section>
    );
  }

  return (
    <>
      <section className="ws-panel ws-panel--compact">
        <PanelHeader icon="fact_check" title="What was checked" text={view.summary} />
      </section>

      <section className="ws-panel">
        <PanelHeader icon="checklist" title="Trace sources" text="Each row is a Windows data layer reviewed on this scan." />
        <div className="ws-panel__body">
          <ul className="simple-trace-list">
            {view.sources.map((row) => (
              <li key={row.id} className={`simple-trace-row simple-trace-row--${row.tone}`}>
                <span className="simple-trace-status">{row.statusLabel}</span>
                <strong>{row.label}</strong>
                {row.count > 0 ? <span className="muted">{row.count} record(s)</span> : null}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {view.inconsistencies.length ? (
        <section className="ws-panel">
          <PanelHeader
            icon="compare_arrows"
            title="Cross-check mismatches"
            text="When one trace says a program ran but another does not — worth a closer look."
          />
          <div className="ws-panel__body">
            <ul className="simple-timeline">
              {view.inconsistencies.map((row, index) => (
                <li key={`${row.type}-${index}`} className="simple-timeline--warn">
                  <SeverityBadge severity={row.severity} compact />
                  <p>{row.summary}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}
    </>
  );
}

function SecurityTab({ report, formatGmtPlus3 }) {
  const sec = report.security_integrity_signals ?? {};
  const defenderView = defenderSummary(sec.defender);
  const signals = securitySignalsView(sec);

  return (
    <>
      {defenderView.available ? (
        <section className="ws-panel">
          <PanelHeader icon="shield" title="Windows Defender" text={defenderView.statusLabel} />
          <div className="ws-panel__body">
            <div className="ws-metrics ws-metrics--compact">
              <div className="ws-metric">
                <strong>{signals.threatCount}</strong>
                <span>threat signals</span>
              </div>
              <div className="ws-metric">
                <strong>{signals.exclusionCount}</strong>
                <span>folder exclusions</span>
              </div>
              <div className="ws-metric">
                <strong>{defenderView.quarantineCount}</strong>
                <span>quarantine items</span>
              </div>
            </div>
            {defenderView.userExclusions?.length ? (
              <ul className="simple-program-list">
                {defenderView.userExclusions.slice(0, 8).map((path) => (
                  <li key={path} className="simple-program--warn">
                    <p className="muted">Excluded folder: {privacyPath(path)}</p>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </section>
      ) : null}

      <section className="ws-panel">
        <PanelHeader icon="delete_sweep" title="Log clearing & cleanup" text="Signs that logs or traces may have been wiped." />
        <div className="ws-panel__body">
          {signals.logClearingHints.length ? (
            <ul className="simple-timeline">
              {signals.logClearingHints.map((hint) => (
                <li key={hint} className="simple-timeline--warn">
                  <p>{hint}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No major log-clearing signals on this scan.</p>
          )}
          {signals.traceCleanerCount > 0 ? (
            <ul className="simple-timeline">
              {signals.traceCleaners.slice(0, 12).map((row, index) => (
                <li key={`${row.type}-${index}`} className="simple-timeline--warn">
                  <p>{row.summary || row.detail || "Cleanup tool or command detected"}</p>
                  {row.occurred_at ? (
                    <time className="muted">{formatGmtPlus3(row.occurred_at)}</time>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </section>

      <section className="ws-panel ws-panel--compact">
        <PanelHeader
          icon="event_note"
          title="Event logs"
          text={
            signals.eventLogCount
              ? `${signals.eventLogCount} recent Windows events were sampled.`
              : "Event log sample was not available on this scan."
          }
        />
      </section>
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
  const avatarIndex = (BigInt(userId) >> 22n) % 6n;
  return `https://cdn.discordapp.com/embed/avatars/${avatarIndex}.png`;
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
      <section className="ws-panel">
        <PanelHeader
          icon="sports_esports"
          title="Roblox accounts"
          text="Found in the game client, browser, or local storage."
        />
        <div className="ws-panel__body">
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
        </div>
      </section>

      <section className="ws-panel">
        <PanelHeader
          icon="forum"
          title="Discord accounts"
          text="Found in the Discord app or browser login."
        />
        <div className="ws-panel__body">
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
        </div>
      </section>
    </>
  );
}

export function SimpleResults({ report, summary, activity, activityEventSummary, formatGmtPlus3, token }) {
  const [tab, setTab] = useState("summary");
  const sec = report.security_integrity_signals ?? {};
  const bypass = sec.bypass_resilience ?? {};
  const review = useMemo(() => scanReviewFromReport(report), [report]);
  const verdict = useMemo(
    () => simpleVerdict(summary.score, bypass.risk_score ?? 0),
    [summary.score, bypass.risk_score],
  );
  const problems = useMemo(() => buildProblems(report, summary), [report, summary]);

  return (
    <div className="ws-simple">
      <nav className="ws-review-nav" aria-label="Review sections">
        {TABS.map(({ id, label, icon }) => (
          <button
            key={id}
            type="button"
            className={`ws-review-nav__tab ${tab === id ? "ws-review-nav__tab--active" : ""}`}
            onClick={() => setTab(id)}
          >
            <MaterialIcon name={icon} size={16} />
            {label}
          </button>
        ))}
      </nav>

      <div className="ws-simple__content">
        {tab === "summary" ? (
          <SummaryTab
            verdict={verdict}
            problems={problems}
            review={review}
            report={report}
            formatGmtPlus3={formatGmtPlus3}
          />
        ) : null}
        {tab === "findings" ? (
          <FindingsTab problems={problems} review={review} formatGmtPlus3={formatGmtPlus3} />
        ) : null}
        {tab === "traces" ? <TracesTab report={report} /> : null}
        {tab === "security" ? <SecurityTab report={report} formatGmtPlus3={formatGmtPlus3} /> : null}
        {tab === "activity" ? (
          <ActivityTab
            review={review}
            activity={activity}
            activityEventSummary={activityEventSummary}
            formatGmtPlus3={formatGmtPlus3}
          />
        ) : null}
        {tab === "accounts" ? <AccountsTab report={report} token={token} /> : null}
      </div>
    </div>
  );
}
