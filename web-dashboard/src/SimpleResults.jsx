import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Download,
  FileDown,
  FileCode2,
  HelpCircle,
  ListChecks,
  Play,
  Search,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { scanReviewFromReport } from "./reportDigest.js";

const VERDICT_META = {
  clean: {
    label: "Looks OK",
    emoji: "✅",
    tone: "clean",
    blurb: "We did not see strong signs of cheats, hidden tools, or cover-up tricks on this scan.",
  },
  watch: {
    label: "Something odd",
    emoji: "⚠️",
    tone: "watch",
    blurb: "A few things looked unusual. A reviewer should take a closer look.",
  },
  bad: {
    label: "Very suspicious",
    emoji: "🚨",
    tone: "bad",
    blurb: "Many warning signs showed up. This scan needs careful review.",
  },
};

const TABS = [
  { id: "overview", label: "Summary", icon: Sparkles },
  { id: "activity", label: "Last activity", icon: Clock3 },
  { id: "downloads", label: "Download history", icon: FileDown },
  { id: "execution", label: "Programs run", icon: Play },
  { id: "programs", label: "Program list", icon: FileCode2 },
  { id: "strings", label: "Word matches", icon: Search },
];

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
    <div className="simple-stat">
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
      <ShieldAlert size={22} />
    ) : problem.severity === "medium" ? (
      <AlertTriangle size={22} />
    ) : (
      <HelpCircle size={22} />
    );

  return (
    <article className={`simple-problem simple-problem--${problem.severity}`}>
      <button type="button" className="simple-problem-head" onClick={() => setOpen((v) => !v)}>
        <span className="simple-problem-icon">{icon}</span>
        <span className="simple-problem-text">
          <strong>{problem.title}</strong>
          {!open ? <span className="simple-problem-teaser">Tap to read more</span> : null}
        </span>
        <ChevronRight size={18} className={open ? "open" : ""} />
      </button>
      {open ? <p className="simple-problem-body">{problem.detail}</p> : null}
    </article>
  );
}

function PathFold({ path }) {
  if (!path) return null;
  return (
    <details className="simple-path-fold">
      <summary>Show location on PC</summary>
      <code>{path}</code>
    </details>
  );
}

function OverviewTab({ verdict, problems, review, formatGmtPlus3 }) {
  const activity = review.last_computer_activity ?? {};
  return (
    <>
      <section className={`simple-hero simple-hero--${verdict.tone}`}>
        <div className="simple-hero-main">
          <span className="simple-hero-emoji" aria-hidden>
            {verdict.emoji}
          </span>
          <div>
            <p className="simple-hero-eyebrow">What we think</p>
            <h3>{verdict.label}</h3>
            <p>{verdict.blurb}</p>
          </div>
        </div>
        <div className="simple-hero-score" aria-label={`Overall concern level ${verdict.combined} out of 100`}>
          <strong>{verdict.combined}</strong>
          <span>concern level</span>
          <small>0 = calm · 100 = very worried</small>
        </div>
      </section>

      <section className="simple-stats-row">
        <SimpleStat label="Warning signs" value={problems.length} hint="Read the list below" />
        <SimpleStat label="Things that happened" value={activity.event_count ?? 0} hint="With a time" />
        <SimpleStat label="Programs run" value={review.execution_activity?.event_count ?? 0} hint="Found on PC" />
        <SimpleStat label="Word matches" value={review.string_detection?.hit_count ?? 0} hint="In logs & files" />
      </section>

      <section className="simple-panel">
        <header className="simple-panel-head">
          <ListChecks size={22} />
          <div>
            <h4>What stood out</h4>
            <p>The main things a reviewer should know, in plain words.</p>
          </div>
        </header>
        {problems.length ? (
          <div className="simple-problem-list">
            {problems.slice(0, 12).map((problem) => (
              <ProblemCard key={problem.id} problem={problem} />
            ))}
          </div>
        ) : (
          <div className="simple-empty">
            <CheckCircle2 size={28} />
            <p>Nothing scary jumped out on this scan.</p>
          </div>
        )}
      </section>

      <section className="simple-panel simple-panel--tips">
        <header className="simple-panel-head">
          <Sparkles size={22} />
          <div>
            <h4>Quick guide</h4>
          </div>
        </header>
        <ul className="simple-tips">
          <li>
            <strong>Summary</strong> — start here for the big picture.
          </li>
          <li>
            <strong>Last activity</strong> — what the PC did recently, in time order.
          </li>
          <li>
            <strong>Download history</strong> — files downloaded in Chrome, Edge, Brave, or Firefox.
          </li>
          <li>
            <strong>Programs run</strong> — apps and files that were executed.
          </li>
          <li>
            <strong>Program list</strong> — executables we found on disk.
          </li>
          <li>
            <strong>Word matches</strong> — cheat or cleanup words inside files and history.
          </li>
        </ul>
        {activity.boot_time ? (
          <p className="muted small-note">PC last turned on: {formatGmtPlus3(activity.boot_time)}</p>
        ) : null}
      </section>
    </>
  );
}

function ActivityTab({ review, activity, activityEventSummary, formatGmtPlus3 }) {
  const block = review.last_computer_activity ?? {};
  let events = block.events ?? [];
  if (!events.length && (activity?.events ?? []).length) {
    events = (activity.events ?? [])
      .filter((e) => e.occurred_at)
      .map((e) => ({
        occurred_at: e.occurred_at,
        summary: activityEventSummary(e),
        path: e.path,
      }));
  }
  const downloads = review.download_history?.items ?? [];
  for (const dl of downloads) {
    const when = dl.started_at || dl.ended_at;
    if (!when) continue;
    events.push({
      occurred_at: when,
      summary: `A file was downloaded in ${dl.browser || "a browser"}: ${dl.file_name || "a file"}.`,
      path: dl.target_path || dl.url,
    });
  }
  events.sort((a, b) => new Date(b.occurred_at) - new Date(a.occurred_at));

  return (
    <section className="simple-panel">
      <header className="simple-panel-head">
        <Clock3 size={22} />
        <div>
          <h4>Last computer activity</h4>
          <p>What this PC did lately. Newest first (MM/DD/YY, GMT+3).</p>
        </div>
      </header>
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
      {events.length ? (
        <ul className="simple-timeline">
          {events.map((event, index) => (
            <li key={`${event.path}-${event.occurred_at}-${index}`}>
              <time>{formatGmtPlus3(event.occurred_at)}</time>
              <p>{event.summary || "Activity recorded"}</p>
              {event.gap_human ? (
                <p className="muted">
                  Recycle Bin was emptied <strong>{event.gap_human}</strong> after this delete
                  {event.cleanup_at_display || event.cleanup_at
                    ? ` (${event.cleanup_at_display || formatGmtPlus3(event.cleanup_at)})`
                    : ""}
                  .
                </p>
              ) : null}
              <PathFold path={event.path} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No timed activity on this report. Try a new scan with the latest app.</p>
      )}
    </section>
  );
}

function DownloadsTab({ review, formatGmtPlus3 }) {
  const block = review.download_history ?? {};
  const items = block.items ?? [];
  const [onlyFlagged, setOnlyFlagged] = useState(false);
  const shown = onlyFlagged ? items.filter((i) => i.suspicious) : items;

  return (
    <section className="simple-panel">
      <header className="simple-panel-head">
        <FileDown size={22} />
        <div>
          <h4>Browser download history</h4>
          <p>Files downloaded through Chrome, Edge, Brave, or Firefox έΑΦ like the browserέΑβs own download list.</p>
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
              <time>{row.started_at ? formatGmtPlus3(row.started_at) : "Time unknown"}</time>
              <p>
                <strong>{row.file_name || "Download"}</strong> έΑΦ via {row.browser || "browser"}
                {row.state ? ` (${row.state})` : ""}
              </p>
              {row.matched_labels?.length ? (
                <p className="muted">Matched: {row.matched_labels.join(", ")}</p>
              ) : null}
              {row.url ? (
                <details className="simple-path-fold">
                  <summary>Show download page link</summary>
                  <code>{row.url}</code>
                </details>
              ) : null}
              <PathFold path={row.target_path} />
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
        {block.suspicious_count ?? 0} flagged ┬╖ {block.event_count ?? 0} total runs traced
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
                <strong>{row.name || "Program"}</strong> έΑΦ {row.summary}
              </p>
              <PathFold path={row.path} />
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
                <strong>{row.name || "File"}</strong>
                {row.labels?.length ? (
                  <span className="simple-tag">{row.labels.slice(0, 3).join(", ")}</span>
                ) : null}
                <p className="muted">
                  {row.file_exists === false ? "Removed from disk · " : ""}
                  {row.sources?.includes("removed_artifact")
                    ? "Recovered from system traces after Recycle Bin cleanup · "
                    : ""}
                  Last seen {row.last_seen ? formatGmtPlus3(row.last_seen) : "unknown"}
                </p>
              </div>
              <PathFold path={row.path} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No programs in this filter. Try showing all found.</p>
      )}
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
              <p className="simple-string-snippet">έΑε{row.snippet}έΑζ</p>
              <p className="muted">
                Matched: {(row.matched_terms ?? []).slice(0, 6).join(", ") || "keywords"}
                {row.occurred_at ? ` ┬╖ ${formatGmtPlus3(row.occurred_at)}` : ""}
              </p>
              <PathFold path={row.file_path} />
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
  onExpertMode,
  onDownload,
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
    <div className="simple-results">
      <nav className="simple-tabs" aria-label="Result sections">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={tab === id ? "active" : ""}
            onClick={() => setTab(id)}
          >
            <Icon size={17} />
            {label}
          </button>
        ))}
      </nav>

      {tab === "overview" ? (
        <OverviewTab verdict={verdict} problems={problems} review={review} formatGmtPlus3={formatGmtPlus3} />
      ) : null}
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

      <footer className="simple-footer">
        <button type="button" className="simple-expert-btn" onClick={onExpertMode}>
          Advanced reviewer view
        </button>
        <button type="button" className="download-button" onClick={onDownload}>
          <Download size={15} /> Save full report
        </button>
      </footer>
    </div>
  );
}
