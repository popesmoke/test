import React, { useEffect, useMemo, useState } from "react";
import { MaterialIcon } from "./components/MaterialIcon.jsx";
import { SeverityBadge, severityRank } from "./components/SeverityBadge.jsx";
import { defenderSummary } from "./defenderSignals.js";
import { scanReviewFromReport } from "./reportDigest.js";
import { formatDisplayLocation, groupFlaggedPrograms, privacyPath, publicFindingDetail, publicFindingTitle } from "./resultPrivacy.js";
import {
  collectRobloxAccountsFromReport,
  collectDiscordAccountsFromReport,
} from "./accountExtract.js";
import { CollapseCard } from "./components/CollapseCard.jsx";
import { BypassPanel } from "./components/BypassPanel.jsx";
import { Pagination } from "./components/Pagination.jsx";
import { buildBypassReport } from "./bypassDetection.js";
import { usePagination } from "./hooks/usePagination.js";
import { genericReasonLabel, genericReasonDetail, plainDisplayText } from "./reviewerCopy.js";

const API_URL = import.meta.env.VITE_API_URL || "https://virello-secure.onrender.com";

const TABS = [
  { id: "summary", label: "Summary", icon: "description" },
  { id: "findings", label: "Findings", icon: "shield_alert" },
  { id: "bypass", label: "Bypass attempts", icon: "gpp_maybe" },
  { id: "activity", label: "Activity", icon: "history" },
  { id: "accounts", label: "Accounts", icon: "users" },
];

const VERDICT_META = {
  clean: { label: "Looks clear", tone: "clean", blurb: "Nothing major stood out on this scan." },
  watch: { label: "Review recommended", tone: "watch", blurb: "Some warning signs need a closer look." },
  bad: { label: "High concern", tone: "bad", blurb: "Multiple warning signs. Review carefully." },
};

function simpleVerdict(score, bypassRisk) {
  const combined = Math.min(100, Math.round(score * 0.75 + (bypassRisk || 0) * 0.35));
  if (combined >= 70) return { ...VERDICT_META.bad, combined };
  if (combined >= 35) return { ...VERDICT_META.watch, combined };
  return { ...VERDICT_META.clean, combined };
}

function buildProblems(report, summary) {
  const problems = [];

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

function WarningRow({ problem }) {
  return (
    <article className={`ws-static-finding ws-finding--${problem.severity}`}>
      <div className="ws-static-finding__head">
        <SeverityBadge severity={problem.severity} />
        <strong>{problem.title}</strong>
      </div>
      <p className="ws-static-finding__detail">{problem.detail}</p>
    </article>
  );
}

function ProgramGroup({ group, formatGmtPlus3 }) {
  const latest = group.items.reduce((best, row) => {
    if (!row.last_seen) return best;
    if (!best || row.last_seen > best) return row.last_seen;
    return best;
  }, null);
  const removedCount = group.items.filter((row) => row.file_exists === false).length;
  const subtitle = [
    `${group.items.length} trace${group.items.length === 1 ? "" : "s"}`,
    removedCount ? `${removedCount} removed from disk` : null,
    latest ? `last seen ${formatGmtPlus3(latest)}` : null,
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <CollapseCard
      icon="file_code"
      title={group.title}
      subtitle={subtitle}
      severity="high"
      badge={<span className="ws-collapse-pill">{group.items.length}</span>}
    >
      <ul className="ws-collapse-list">
        {group.items.map((row, index) => (
          <li key={`${row.name}-${row.last_seen}-${index}`} className="ws-collapse-list__item">
            <p className="ws-collapse-list__lead">{publicFindingDetail(row)}</p>
            <div className="ws-collapse-list__meta">
              <span>{row.file_exists === false ? "Removed from disk" : "Trace on disk"}</span>
              <time>{row.last_seen ? formatGmtPlus3(row.last_seen) : "Time unknown"}</time>
            </div>
            <LocationHint row={row} path={row.path} />
          </li>
        ))}
      </ul>
    </CollapseCard>
  );
}

function LinkedTraceCard({ chain, formatGmtPlus3 }) {
  const steps = chain.steps ?? [];
  const title = chain.labels?.length ? chain.labels.join(", ") : "Related activity";
  const latest = steps.reduce((best, step) => {
    if (!step.occurred_at) return best;
    if (!best || step.occurred_at > best) return step.occurred_at;
    return best;
  }, null);
  const subtitle = [
    `${steps.length} linked step${steps.length === 1 ? "" : "s"}`,
    latest ? `latest ${formatGmtPlus3(latest)}` : null,
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <CollapseCard
      icon="git_branch"
      title={title}
      subtitle={subtitle}
      severity={chain.confidence === "high" ? "high" : "medium"}
      badge={<SeverityBadge severity={chain.confidence === "high" ? "high" : "medium"} compact showIcon={false} />}
    >
      {chain.summary ? <p className="ws-collapse-list__lead">{chain.summary}</p> : null}
      <ol className="ws-collapse-steps">
        {steps.map((step, index) => (
          <li key={`${step.source}-${step.path}-${index}`}>
            <div className="ws-collapse-steps__head">
              <span className="ws-collapse-steps__action">
                {CHAIN_ACTION_LABELS[step.action] || step.action}
              </span>
              <time>{step.occurred_at ? formatGmtPlus3(step.occurred_at) : "Time unknown"}</time>
            </div>
            <p>{step.detail}</p>
            <LocationHint row={step} path={step.path} />
          </li>
        ))}
      </ol>
    </CollapseCard>
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
            {problems.slice(0, 5).map((problem) => (
              <WarningRow key={problem.id} problem={problem} />
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
  const programGroups = useMemo(() => groupFlaggedPrograms(programs), [programs]);
  const sortedChains = [...chains].sort((a, b) => {
    const aHigh = a.confidence === "high" ? 0 : 1;
    const bHigh = b.confidence === "high" ? 0 : 1;
    return aHigh - bHigh;
  });
  const problemsPage = usePagination(problems, 6);
  const chainsPage = usePagination(sortedChains, 5);
  const programsPage = usePagination(programGroups, 5);

  return (
    <>
      <section className="ws-panel">
        <PanelHeader icon="list_checks" title="Warning signs" text="Sorted by importance." />
        <div className="ws-panel__body">
          {problems.length ? (
            <>
              {problemsPage.slice.map((problem) => (
                <WarningRow key={problem.id} problem={problem} />
              ))}
              <Pagination {...problemsPage} onPageChange={problemsPage.goTo} />
            </>
          ) : (
            <p className="muted">No warning signs on this scan.</p>
          )}
        </div>
      </section>

      {sortedChains.length ? (
        <section className="ws-panel">
          <PanelHeader
            icon="git_branch"
            title="Linked traces"
            text="Related activity grouped together. Tap a card to expand the timeline."
          />
          <div className="ws-panel__body ws-collapse-stack">
            {chainsPage.slice.map((chain, index) => (
              <LinkedTraceCard key={`${chain.stem}-${index}`} chain={chain} formatGmtPlus3={formatGmtPlus3} />
            ))}
            <Pagination {...chainsPage} onPageChange={chainsPage.goTo} />
          </div>
        </section>
      ) : null}

      {programGroups.length ? (
        <section className="ws-panel">
          <PanelHeader
            icon="file_code"
            title="Flagged programs"
            text="Grouped by what matched. Tap a card to see each trace."
          />
          <div className="ws-panel__body ws-collapse-stack">
            {programsPage.slice.map((group) => (
              <ProgramGroup key={group.title} group={group} formatGmtPlus3={formatGmtPlus3} />
            ))}
            <Pagination {...programsPage} onPageChange={programsPage.goTo} />
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
];

function ActivityCard({ time, warn, children }) {
  return (
    <li className={`ws-activity-card${warn ? " ws-activity-card--warn" : ""}`}>
      <time className="ws-activity-card__time">{time}</time>
      <div className="ws-activity-card__body">{children}</div>
    </li>
  );
}

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

  const timelinePage = usePagination(events, 8);
  const downloadsPage = usePagination(downloads, 8);
  const programsPage = usePagination(executions, 8);

  useEffect(() => {
    timelinePage.reset();
    downloadsPage.reset();
    programsPage.reset();
  }, [view]);

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
            <>
              <ul className="ws-activity-list">
                {timelinePage.slice.map((event, index) => (
                  <ActivityCard
                    key={`${event.path}-${event.occurred_at}-${index}`}
                    time={event.occurred_at ? formatGmtPlus3(event.occurred_at) : "Time unknown"}
                  >
                    <p className="ws-activity-card__title">{plainDisplayText(event.summary || "Activity recorded")}</p>
                    <LocationHint row={event} path={event.path} />
                  </ActivityCard>
                ))}
              </ul>
              <Pagination {...timelinePage} onPageChange={timelinePage.goTo} />
            </>
          ) : (
            <p className="muted">No timeline events on this scan.</p>
          )
        ) : null}

        {view === "downloads" ? (
          downloads.length ? (
            <>
              <ul className="ws-activity-list">
                {downloadsPage.slice.map((row, index) => (
                  <ActivityCard
                    key={`${row.target_path}-${row.started_at}-${index}`}
                    warn={row.suspicious}
                    time={row.started_at ? formatGmtPlus3(row.started_at) : "Time unknown"}
                  >
                    <p className="ws-activity-card__title">
                      <strong>{row.file_name || "Download"}</strong>
                      <span className="ws-activity-card__via"> via {row.browser || "browser"}</span>
                    </p>
                    {row.matched_labels?.length ? (
                      <p className="ws-activity-card__meta muted">{publicFindingTitle(row.matched_labels, row)}</p>
                    ) : null}
                    <LocationHint row={row} path={row.target_path} />
                  </ActivityCard>
                ))}
              </ul>
              <Pagination {...downloadsPage} onPageChange={downloadsPage.goTo} />
            </>
          ) : (
            <p className="muted">No download history found.</p>
          )
        ) : null}

        {view === "programs" ? (
          executions.length ? (
            <>
              <ul className="ws-activity-list">
                {programsPage.slice.map((row, index) => (
                  <ActivityCard
                    key={`${row.path}-${row.occurred_at}-${index}`}
                    warn={row.suspicious}
                    time={row.occurred_at ? formatGmtPlus3(row.occurred_at) : "Time unknown"}
                  >
                    <p className="ws-activity-card__title">
                      <strong>{row.name || row.file_name || "Program"}</strong>
                    </p>
                    {row.summary ? (
                      <p className="ws-activity-card__meta muted">{plainDisplayText(row.summary)}</p>
                    ) : null}
                    <LocationHint row={row} path={row.path} />
                  </ActivityCard>
                ))}
              </ul>
              <Pagination {...programsPage} onPageChange={programsPage.goTo} />
            </>
          ) : (
            <p className="muted">No program execution traces found.</p>
          )
        ) : null}
      </div>
    </section>
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

  const robloxPage = usePagination(robloxAccounts, 12);
  const discordPage = usePagination(discordAccounts, 12);

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
            <>
              <div className="ws-account-grid">
                {robloxPage.slice.map((account) => {
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
                      <span className="ws-account-card__link">
                        {(account.sources ?? []).slice(0, 2).join(", ") || "View profile"}
                      </span>
                    </span>
                  </a>
                );
              })}
              </div>
              <Pagination {...robloxPage} onPageChange={robloxPage.goTo} />
            </>
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
            <>
              <div className="ws-account-grid">
                {discordPage.slice.map((account) => {
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
                      <span className="ws-account-card__link">
                        {(account.sources ?? []).slice(0, 2).join(", ") || "Discord account"}
                      </span>
                    </span>
                  </div>
                );
              })}
              </div>
              <Pagination {...discordPage} onPageChange={discordPage.goTo} />
            </>
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
  const bypassView = useMemo(
    () => buildBypassReport(report.security_integrity_signals?.bypass_resilience ?? {}),
    [report],
  );

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
            {id === "bypass" && bypassView.findingCount ? (
              <span className="ws-review-nav__badge">{bypassView.findingCount}</span>
            ) : null}
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
        {tab === "bypass" ? <BypassPanel report={report} /> : null}
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
