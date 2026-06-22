import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Download,
  FileDown,
  FileText,
  FileCode2,
  HelpCircle,
  ListChecks,
  Play,
  Search,
  Shield,
  ShieldAlert,
  GitBranch,
  Users,
} from "lucide-react";
import { defenderSummary } from "./defenderSignals.js";
import { scanReviewFromReport } from "./reportDigest.js";
import { formatDisplayLocation, privacyPath } from "./resultPrivacy.js";

const VERDICT_META = {
  clean: {
    label: "Looks OK",
    tone: "clean",
    blurb: "No strong signs of cheats or cover-up on this scan.",
  },
  watch: {
    label: "Needs review",
    tone: "watch",
    blurb: "A few unusual signals — worth a closer look.",
  },
  bad: {
    label: "High risk",
    tone: "bad",
    blurb: "Multiple warning signs — review carefully.",
  },
};

const TABS = [
  { id: "overview", label: "Summary", icon: FileText },
  { id: "accounts", label: "Accounts", icon: Users },
  { id: "chains", label: "Evidence chains", icon: GitBranch },
  { id: "activity", label: "Activity", icon: Clock3 },
  { id: "downloads", label: "Downloads", icon: FileDown },
  { id: "execution", label: "Programs run", icon: Play },
  { id: "programs", label: "Program list", icon: FileCode2 },
  { id: "strings", label: "Keywords", icon: Search },
  { id: "security", label: "Security", icon: Shield },
];

const ACTIVITY_FILTERS = [
  { id: "all", label: "All" },
  { id: "executors", label: "Executors" },
  { id: "suspicious", label: "Suspicious files" },
  { id: "deletions", label: "Deletions" },
];

function classifyActivityFilter(event) {
  if (event?.filter) return event.filter;
  const summary = String(event?.summary || "").toLowerCase();
  const category = String(event?.category || "").toLowerCase();
  if (category === "deletions" || summary.includes("no longer on disk") || summary.includes("recycle bin")) {
    return "deletions";
  }
  if (summary.includes("executor") || summary.includes("suspicious program") || category === "commands") {
    return "executors";
  }
  if (category === "files" || summary.includes("suspicious file")) {
    return "suspicious";
  }
  return "other";
}

function simpleVerdict(score, bypassRisk) {
  const combined = Math.min(100, Math.round(score * 0.75 + (bypassRisk || 0) * 0.35));
  if (combined >= 70) return { ...VERDICT_META.bad, combined };
  if (combined >= 35) return { ...VERDICT_META.watch, combined };
  return { ...VERDICT_META.clean, combined };
}

function friendlyReason(label, detail) {
  const map = {
    "Known executor binary hash": "A file matched a known cheat program fingerprint.",
    "Roblox integrity signals": "Something around Roblox looked wrong.",
    "Executor / cheat path matches": "A file or folder looked like a cheat or loader.",
    "Executor / cheat-tagged recent files": "A recent file looked like a cheat or loader.",
    "Prefetch execution traces": "The PC recently ran a program on our watch list.",
    "Profile folder hits": "A suspicious file was in Downloads, Desktop, or Documents.",
    "Cheat-like filename hints": "A file name looked like a common cheat label.",
    "Weird filename pattern": "A file name looked randomly generated or disguised.",
    "Persistence entry": "Something was set to start automatically with Windows.",
    "Cross-source stem match": "The same program name showed up in more than one place.",
    "BAM activity": "The PC recently ran a program on our watch list.",
    "Defender signal": "Windows security settings or history looked unusual.",
    "Deletion or log clearing": "Signs appeared that logs or traces may have been cleaned up.",
    "Deleted cheat/executor traces recovered": "Cheat or executor files were deleted, but Windows still had traces of them.",
    "Executor artifact evidence": "Windows still has traces of a known executor (Prefetch, BAM, USN, etc.) even if the folder was deleted.",
    "Suspicious Recycle Bin items": "The Recycle Bin still holds files whose names look like cheats or loaders.",
    "Bypass / cover-up signals": "Signs appeared that someone may have tried to hide activity.",
    "No matched indicators": "Nothing major matched our watch lists on this scan.",
  };
  return map[label] || detail || label;
}

function buildSimpleProblems(report, summary) {
  const sec = report.security_integrity_signals ?? {};
  const bypass = sec.bypass_resilience ?? {};
  const problems = [];

  for (const row of bypass.findings ?? []) {
    problems.push({
      id: `bypass-${row.title}`,
      severity: row.severity || "medium",
      title: row.title,
      detail: row.detail,
    });
  }

  for (const reason of summary.reasons ?? []) {
    if (!reason.points) continue;
    problems.push({
      id: `score-${reason.label}`,
      severity: reason.points >= 20 ? "high" : reason.points >= 10 ? "medium" : "low",
      title: friendlyReason(reason.label, reason.detail),
      detail: reason.detail,
    });
  }

  const seen = new Set();
  return problems.filter((p) => {
    if (seen.has(p.title)) return false;
    seen.add(p.title);
    return true;
  });
}

function SimpleStat({ label, value, hint }) {
  return (
    <div className="ws-metric">
      <strong>{value}</strong>
      <span>{label}</span>
      {hint ? <small>{hint}</small> : null}
    </div>
  );
}

function ProblemCard({ problem }) {
  const [open, setOpen] = useState(false);
  const icon =
    problem.severity === "high" || problem.severity === "critical" ? (
      <ShieldAlert size={18} />
    ) : problem.severity === "medium" ? (
      <AlertTriangle size={18} />
    ) : (
      <HelpCircle size={18} />
    );

  return (
    <article className={`ws-finding ws-finding--${problem.severity}`}>
      <button type="button" className="ws-finding__toggle" onClick={() => setOpen((v) => !v)}>
        <span className="ws-finding__icon">{icon}</span>
        <strong>{problem.title}</strong>
        <ChevronRight size={16} className={open ? "open" : ""} />
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

function activityEventBadge(event) {
  const summary = String(event?.summary || "").toLowerCase();
  if (event?.category === "deletions" || summary.includes("no longer on disk") || summary.includes("recycle bin")) {
    return { label: "Deletion", tone: "deletion" };
  }
  if (summary.includes("download")) return { label: "Download", tone: "browser" };
  if (summary.includes("program") || summary.includes("executed") || summary.includes("ran")) {
    return { label: "Execution", tone: "execution" };
  }
  return { label: "Activity", tone: "neutral" };
}

function OverviewTab({ verdict, problems, review, formatGmtPlus3 }) {
  const activity = review.last_computer_activity ?? {};
  const deletionCount = (activity.events ?? []).filter((event) => {
    const summary = String(event.summary || "").toLowerCase();
    return event.category === "deletions" || summary.includes("no longer on disk");
  }).length;
  return (
    <>
      <div className="ws-bento">
        <section className={`ws-bento__verdict ws-bento__verdict--${verdict.tone}`}>
          <p className="ws-bento__verdict-label">Assessment</p>
          <h3>{verdict.label}</h3>
          <p>{verdict.blurb}</p>
        </section>
        <section className="ws-bento__meter" aria-label={`Overall concern level ${verdict.combined} out of 100`}>
          <strong>{verdict.combined}</strong>
          <span>concern level</span>
        </section>
      </div>

      <section className="ws-metrics">
        <SimpleStat label="Warning signs" value={problems.length} hint="Expand below" />
        <SimpleStat label="Timeline events" value={activity.event_count ?? 0} hint="Chronological" />
        <SimpleStat
          label="Evidence chains"
          value={review.evidence_chains?.chain_count ?? 0}
          hint="Multi-trace"
        />
        <SimpleStat label="Deleted traces" value={deletionCount} hint="Still logged" />
        <SimpleStat label="Word matches" value={review.string_detection?.hit_count ?? 0} hint="In logs" />
      </section>

      <section className="ws-panel">
        <header className="ws-panel__head">
          <ListChecks size={20} />
          <div>
            <h4>What stood out</h4>
            <p>The main things a reviewer should know, in plain words.</p>
          </div>
        </header>
        <div className="ws-panel__body">
          {problems.length ? (
            <div>
              {problems.slice(0, 12).map((problem) => (
                <ProblemCard key={problem.id} problem={problem} />
              ))}
            </div>
          ) : (
            <div className="ws-empty-state">
              <CheckCircle2 size={24} />
              <p>Nothing concerning jumped out on this scan.</p>
            </div>
          )}
        </div>
      </section>
    </>
  );
}

function ActivityTab({ review, activity, activityEventSummary, formatGmtPlus3 }) {
  const block = review.last_computer_activity ?? {};
  const [activityFilter, setActivityFilter] = useState("all");
  let events = block.events ?? [];
  if (!events.length && (activity?.events ?? []).length) {
    events = (activity.events ?? [])
      .filter((e) => e.occurred_at || e.category === "execution" || e.time_unknown)
      .map((e) => ({
        occurred_at: e.occurred_at,
        summary: activityEventSummary(e),
        path: e.path,
        category: e.category,
        filter: classifyActivityFilter(e),
        time_unknown: e.time_unknown,
        timestamp_source: e.timestamp_source,
      }));
  }
  events = events.filter((event) => classifyActivityFilter(event) !== "other");
  const counts = ACTIVITY_FILTERS.reduce((acc, row) => {
    acc[row.id] =
      row.id === "all"
        ? events.length
        : events.filter((event) => classifyActivityFilter(event) === row.id).length;
    return acc;
  }, {});
  const shown =
    activityFilter === "all"
      ? events
      : events.filter((event) => classifyActivityFilter(event) === activityFilter);
  shown.sort((a, b) => {
    const aSusp = classifyActivityFilter(a) === "executors" || a.suspicious ? 1 : 0;
    const bSusp = classifyActivityFilter(b) === "executors" || b.suspicious ? 1 : 0;
    if (aSusp !== bSusp) return bSusp - aSusp;
    const aMs = a.occurred_at ? new Date(a.occurred_at).getTime() : 0;
    const bMs = b.occurred_at ? new Date(b.occurred_at).getTime() : 0;
    return bMs - aMs;
  });

  return (
    <section className="ws-panel">
      <header className="ws-panel__head">
        <Clock3 size={20} />
        <div>
          <h4>Last computer activity</h4>
          <p>Executors, suspicious files, and deletions only. Newest first.</p>
        </div>
      </header>
      <div className="ws-panel__body">
      <div className="ws-filter-row">
        {ACTIVITY_FILTERS.map((row) => (
          <button
            key={row.id}
            type="button"
            className={activityFilter === row.id ? "active" : ""}
            onClick={() => setActivityFilter(row.id)}
          >
            {row.label} ({counts[row.id] ?? 0})
          </button>
        ))}
      </div>
      {(block.milestones ?? []).length ? (
        <ul className="simple-milestones">
          {block.milestones.map((m) => (
            <li key={`${m.label}-${m.occurred_at}`}>
              <time>{formatGmtPlus3(m.occurred_at)}</time>
              <strong>{m.label}</strong>
              <span>{m.summary}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {shown.length ? (
        <ul className="ws-timeline">
          {shown.map((event, index) => {
            const badge = activityEventBadge(event);
            return (
            <li key={`${event.path}-${event.occurred_at}-${index}`}>
              <time>{event.occurred_at ? formatGmtPlus3(event.occurred_at) : "—"}</time>
              <div>
                <span className="ws-tag">{badge.label}</span>
                <p>{event.summary || "Activity recorded"}</p>
                {event.timestamp_source && event.occurred_at ? (
                  <p className="muted small-note">
                    Time from {event.timestamp_source.replace(/_/g, " ")}
                  </p>
                ) : null}
                {event.gap_human ? (
                  <p className="muted">
                    Recycle Bin emptied <strong>{event.gap_human}</strong> after this delete.
                  </p>
                ) : null}
                <LocationHint row={event} path={event.path} />
              </div>
            </li>
            );
          })}
        </ul>
      ) : (
        <p className="muted">No activity in this filter.</p>
      )}
      </div>
    </section>
  );
}

const CHAIN_ACTION_LABELS = {
  executed: "Ran",
  ran: "Ran",
  downloaded: "Downloaded",
  deleted: "Deleted",
  on_disk: "On disk",
  known_hash: "Known hash",
  removed_trace: "Trace remains",
  filesystem: "Filesystem",
  correlated: "Correlated",
  traced: "Traced",
};

function EvidenceChainsTab({ review, formatGmtPlus3 }) {
  const block = review.evidence_chains ?? {};
  const chains = block.chains ?? [];
  const [onlyHigh, setOnlyHigh] = useState(false);
  const shown = onlyHigh ? chains.filter((c) => c.confidence === "high") : chains;

  return (
    <section className="simple-panel">
      <header className="simple-panel-head">
        <GitBranch size={22} />
        <div>
          <h4>Evidence chains</h4>
          <p>When multiple traces agree — e.g. downloaded, ran, then deleted but still logged.</p>
        </div>
      </header>
      <div className="simple-filter-row">
        <button type="button" className={!onlyHigh ? "active" : ""} onClick={() => setOnlyHigh(false)}>
          All chains ({block.chain_count ?? chains.length})
        </button>
        <button type="button" className={onlyHigh ? "active" : ""} onClick={() => setOnlyHigh(true)}>
          High confidence ({chains.filter((c) => c.confidence === "high").length})
        </button>
      </div>
      {shown.length ? (
        <ul className="simple-chain-list">
          {shown.map((chain) => (
            <li key={chain.stem} className={`simple-chain-card simple-chain-card--${chain.confidence || "medium"}`}>
              <div className="simple-chain-head">
                <strong>{chain.labels?.length ? chain.labels.join(", ") : chain.stem}</strong>
                <span className={`simple-chain-badge simple-chain-badge--${chain.confidence || "medium"}`}>
                  {chain.confidence === "high" ? "High confidence" : "Medium"}
                </span>
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
      ) : (
        <div className="simple-empty">
          <CheckCircle2 size={28} />
          <p>No multi-trace evidence chains on this scan.</p>
        </div>
      )}
    </section>
  );
}

function AccountsTab({ report, token, formatGmtPlus3 }) {
  const roblox = report.application_diagnostics?.roblox ?? {};
  const discord = report.application_diagnostics?.discord ?? {};
  const robloxIds = roblox.aggregate_user_ids ?? (roblox.accounts ?? []).map((a) => a.user_id).filter(Boolean);
  const discordAccounts = discord.accounts ?? [];

  return (
    <section className="simple-panel">
      <header className="simple-panel-head">
        <Users size={22} />
        <div>
          <h4>Linked accounts</h4>
          <p>Roblox and Discord accounts found on this device — usernames and profile links only.</p>
        </div>
      </header>
      <h5 className="simple-subhead">Roblox</h5>
      {robloxIds.length ? (
        <p className="muted panel-intro">{robloxIds.length} account(s) detected. Open forensic view for avatars and profile links.</p>
      ) : (
        <p className="muted">No Roblox accounts were found.</p>
      )}
      <h5 className="simple-subhead">Discord</h5>
      {discordAccounts.length ? (
        <ul className="simple-program-list">
          {discordAccounts.map((account) => (
            <li key={account.user_id}>
              <div>
                <strong>{account.display_name || `User ${account.user_id}`}</strong>
                <p className="muted">Discord ID {account.user_id}</p>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No Discord accounts were found in local client data.</p>
      )}
    </section>
  );
}

function DownloadsTab({ review, formatGmtPlus3 }) {
  const block = review.download_history ?? {};
  const items = block.items ?? [];
  const [onlyFlagged, setOnlyFlagged] = useState(false);
  let shown = onlyFlagged ? items.filter((i) => i.suspicious) : items;
  shown = [...shown].sort((a, b) => {
    if (a.suspicious !== b.suspicious) return a.suspicious ? -1 : 1;
    const aMs = a.started_at ? new Date(a.started_at).getTime() : 0;
    const bMs = b.started_at ? new Date(b.started_at).getTime() : 0;
    return bMs - aMs;
  });

  return (
    <section className="simple-panel">
      <header className="simple-panel-head">
        <FileDown size={22} />
        <div>
          <h4>Browser download history</h4>
          <p>Files downloaded through Chrome, Edge, Brave, or Firefox — like the browser's own download list.</p>
        </div>
      </header>
      <div className="simple-filter-row">
        <button type="button" className={!onlyFlagged ? "active" : ""} onClick={() => setOnlyFlagged(false)}>
          All downloads ({block.download_count ?? 0})
        </button>
        <button type="button" className={onlyFlagged ? "active" : ""} onClick={() => setOnlyFlagged(true)}>
          Flagged ({block.suspicious_count ?? 0})
        </button>
      </div>
      {shown.length ? (
        <ul className="simple-timeline">
          {shown.slice(0, 50).map((row, index) => (
            <li
              key={`${row.target_path}-${row.started_at}-${index}`}
              className={row.suspicious ? "simple-timeline--warn" : ""}
            >
              <time title={row.timestamp_label || "Download time"}>
                {row.started_at ? formatGmtPlus3(row.started_at) : "Time unknown"}
              </time>
              <p>
                <strong>{row.file_name || "Download"}</strong> — via {row.browser || "browser"}
                {row.state ? ` (${row.state})` : ""}
              </p>
              {row.executor_site ? (
                <p className="muted">
                  Downloaded from a site associated with <strong>{row.executor_site}</strong>
                </p>
              ) : null}
              {row.matched_labels?.length ? (
                <p className="muted">Matched: {row.matched_labels.join(", ")}</p>
              ) : null}
              {row.url && row.suspicious ? (
                <details className="simple-path-fold">
                  <summary>Show download page link</summary>
                  <code>{row.url}</code>
                </details>
              ) : null}
              <LocationHint row={row} path={row.target_path} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">
          No browser download records were read. The browser may be closed, profiles encrypted, or history cleared.
        </p>
      )}
    </section>
  );
}

function ExecutionTab({ review, formatGmtPlus3 }) {
  const block = review.execution_activity ?? {};
  const items = block.items ?? [];

  return (
    <section className="simple-panel">
      <header className="simple-panel-head">
        <Play size={22} />
        <div>
          <h4>Execution activity</h4>
          <p>Programs and files that look like they were run on this PC.</p>
        </div>
      </header>
      <p className="muted panel-intro">
        {block.suspicious_count ?? 0} flagged · {block.event_count ?? 0} total runs traced
      </p>
      {items.length ? (
        <ul className="simple-timeline">
          {items.slice(0, 40).map((row, index) => (
            <li
              key={`${row.path}-${row.occurred_at}-${index}`}
              className={row.suspicious ? "simple-timeline--warn" : ""}
            >
              <time>{row.occurred_at ? formatGmtPlus3(row.occurred_at) : "Time unknown"}</time>
              <p>
                <strong>{row.name || row.file_name || "Program"}</strong> — {row.summary}
              </p>
              <LocationHint row={row} path={row.path} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No execution traces were recorded.</p>
      )}
    </section>
  );
}

function ProgramsTab({ review, formatGmtPlus3 }) {
  const block = review.executable_inventory ?? {};
  const items = block.items ?? [];
  const [onlyFlagged, setOnlyFlagged] = useState(true);
  const shown = onlyFlagged ? items.filter((i) => i.suspicious) : items;

  return (
    <section className="simple-panel">
      <header className="simple-panel-head">
        <FileCode2 size={22} />
        <div>
          <h4>Program list (executables)</h4>
          <p>Apps and files found on this PC, with suspicious items highlighted.</p>
        </div>
      </header>
      <div className="simple-filter-row">
        <button
          type="button"
          className={onlyFlagged ? "active" : ""}
          onClick={() => setOnlyFlagged(true)}
        >
          Flagged only ({block.suspicious_count ?? 0})
        </button>
        <button
          type="button"
          className={!onlyFlagged ? "active" : ""}
          onClick={() => setOnlyFlagged(false)}
        >
          All found ({block.total_count ?? 0})
        </button>
      </div>
      {shown.length ? (
        <ul className="simple-program-list">
          {shown.slice(0, 50).map((row, index) => (
            <li key={`${row.path}-${index}`} className={row.suspicious ? "simple-program--warn" : ""}>
              <div>
                <strong>{row.name || row.file_name || "File"}</strong>
                {row.labels?.length ? (
                  <span className="simple-tag">{row.labels.slice(0, 2).join(", ")}</span>
                ) : null}
                <p className="muted">
                  {row.file_exists === false ? "Removed from disk · " : ""}
                  {row.sources?.includes("removed_artifact")
                    ? "Recovered from system traces after Recycle Bin cleanup · "
                    : ""}
                  Last seen {row.last_seen ? formatGmtPlus3(row.last_seen) : "unknown"}
                </p>
              </div>
              <LocationHint row={row} path={row.path} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No programs in this filter. Try showing all found.</p>
      )}
    </section>
  );
}

function SecurityTab({ report, formatGmtPlus3 }) {
  const sec = report.security_integrity_signals ?? {};
  const defenderView = defenderSummary(sec.defender);
  const quarantine = defenderView.quarantine ?? [];
  const serviceEvents = sec.windows_service_change_events?.events ?? [];
  const psEvents = sec.powershell_operational_events?.events ?? [];

  return (
    <section className="simple-panel">
      <header className="simple-panel-head">
        <Shield size={22} />
        <div>
          <h4>Security & antivirus</h4>
          <p>Defender status, quarantine history, PowerShell logs, and service changes.</p>
        </div>
      </header>
      {defenderView.available ? (
        <p className={`simple-verdict-line simple-verdict-line--${defenderView.tone}`}>
          {defenderView.statusLabel}
        </p>
      ) : (
        <p className="muted">{defenderView.detail}</p>
      )}
      <div className="simple-stats-row">
        <SimpleStat label="Threat records" value={defenderView.threatCount ?? 0} />
        <SimpleStat label="Quarantine" value={defenderView.quarantineCount ?? 0} />
        <SimpleStat label="PowerShell events" value={psEvents.length} />
        <SimpleStat label="Service changes" value={serviceEvents.length} />
      </div>
      {quarantine.length ? (
        <ul className="simple-timeline">
          {quarantine.slice(0, 15).map((row, index) => (
            <li key={`q-${index}`} className="simple-timeline--warn">
              <time>{row.DetectionTime || row.InitialDetectionTime || "Unknown time"}</time>
              <p>
                <strong>{row.ThreatName || "Threat"}</strong>
                {row.ProcessName ? ` — ${row.ProcessName}` : ""}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No quarantine rows were recorded on this scan.</p>
      )}
      {serviceEvents.length ? (
        <>
          <h5 className="simple-subhead">Recent service changes</h5>
          <ul className="simple-timeline">
            {serviceEvents.slice(0, 8).map((row, index) => (
              <li key={`svc-${index}`}>
                <time>{row.TimeCreated ? formatGmtPlus3(row.TimeCreated) : "—"}</time>
                <p>{(row.Message || "").slice(0, 200)}</p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

function StringsTab({ review, formatGmtPlus3 }) {
  const block = review.string_detection ?? {};
  const items = block.items ?? [];

  return (
    <section className="simple-panel">
      <header className="simple-panel-head">
        <Search size={22} />
        <div>
          <h4>Word matches (string detection)</h4>
          <p>Cheat, injection, or cleanup words found inside files, logs, or command history.</p>
        </div>
      </header>
      {items.length ? (
        <ul className="simple-string-list">
          {items.slice(0, 40).map((row, index) => (
            <li key={`${row.file_path}-${index}`}>
              <p className="simple-string-snippet">"{row.snippet}"</p>
              <p className="muted">
                Suspicious text pattern detected
                {row.occurred_at ? ` · ${formatGmtPlus3(row.occurred_at)}` : ""}
              </p>
              <LocationHint row={row} path={row.file_path} />
            </li>
          ))}
        </ul>
      ) : (
        <div className="simple-empty">
          <CheckCircle2 size={28} />
          <p>No suspicious words were found in scanned text.</p>
        </div>
      )}
    </section>
  );
}

export function SimpleResults({
  report,
  summary,
  activity,
  activityEventSummary,
  formatGmtPlus3,
  token,
  onExpertMode,
  onDownload,
  onPrintPdf,
}) {
  const [tab, setTab] = useState("overview");
  const sec = report.security_integrity_signals ?? {};
  const bypass = sec.bypass_resilience ?? {};
  const review = useMemo(() => scanReviewFromReport(report), [report]);
  const verdict = useMemo(
    () => simpleVerdict(summary.score, bypass.risk_score ?? 0),
    [summary.score, bypass.risk_score],
  );
  const problems = useMemo(() => buildSimpleProblems(report, summary), [report, summary]);

  return (
    <div className="ws-simple">
      <div className="ws-simple__content">
        {tab === "overview" ? (
          <OverviewTab verdict={verdict} problems={problems} review={review} formatGmtPlus3={formatGmtPlus3} />
        ) : null}
        {tab === "accounts" ? (
          <AccountsTab report={report} token={token} formatGmtPlus3={formatGmtPlus3} />
        ) : null}
        {tab === "chains" ? <EvidenceChainsTab review={review} formatGmtPlus3={formatGmtPlus3} /> : null}
        {tab === "activity" ? (
          <ActivityTab
            review={review}
            activity={activity}
            activityEventSummary={activityEventSummary}
            formatGmtPlus3={formatGmtPlus3}
          />
        ) : null}
        {tab === "downloads" ? <DownloadsTab review={review} formatGmtPlus3={formatGmtPlus3} /> : null}
        {tab === "execution" ? <ExecutionTab review={review} formatGmtPlus3={formatGmtPlus3} /> : null}
        {tab === "programs" ? <ProgramsTab review={review} formatGmtPlus3={formatGmtPlus3} /> : null}
        {tab === "strings" ? <StringsTab review={review} formatGmtPlus3={formatGmtPlus3} /> : null}
        {tab === "security" ? <SecurityTab report={report} formatGmtPlus3={formatGmtPlus3} /> : null}
      </div>

      <nav className="ws-dock" aria-label="Report sections">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`ws-dock__tab ${tab === id ? "ws-dock__tab--active" : ""}`}
            onClick={() => setTab(id)}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </nav>
    </div>
  );
}
