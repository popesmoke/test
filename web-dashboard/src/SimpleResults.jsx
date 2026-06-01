import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Download,
  HelpCircle,
  ListChecks,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

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

function simpleVerdict(score, bypassRisk) {
  const combined = Math.min(100, Math.round(score * 0.75 + (bypassRisk || 0) * 0.35));
  if (combined >= 70) return { ...VERDICT_META.bad, combined };
  if (combined >= 35) return { ...VERDICT_META.watch, combined };
  return { ...VERDICT_META.clean, combined };
}

function friendlyReason(label, detail) {
  const map = {
    "Known executor binary hash": "A file matched a known cheat program fingerprint.",
    "Roblox integrity signals": "Something around Roblox looked wrong while checking the game and its files.",
    "Executor / cheat path matches": "A file name or folder looked like a cheat or loader.",
    "Executor / cheat-tagged recent files": "A recently touched file looked like a cheat or loader.",
    "Prefetch execution traces": "The PC recently ran a program that matched our watch list.",
    "Profile folder hits": "A suspicious file sat in Downloads, Desktop, or Documents.",
    "Cheat-like filename hints": "A file name looked like a common cheat label.",
    "Weird filename pattern": "A file name looked randomly generated or disguised.",
    "Persistence entry": "Something was set to start automatically with Windows.",
    "Cross-source stem match": "The same program name showed up in more than one place.",
    "BAM activity": "The PC recently ran a program that matched our watch list.",
    "Defender signal": "Windows security settings or history looked unusual.",
    "Deletion or log clearing": "Signs appeared that logs or traces may have been cleaned up.",
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
      kind: "cover",
    });
  }

  for (const reason of summary.reasons ?? []) {
    if (!reason.points) continue;
    problems.push({
      id: `score-${reason.label}`,
      severity: reason.points >= 20 ? "high" : reason.points >= 10 ? "medium" : "low",
      title: friendlyReason(reason.label, reason.detail),
      detail: reason.detail,
      kind: "match",
    });
  }

  const seen = new Set();
  return problems.filter((p) => {
    const key = p.title;
    if (seen.has(key)) return false;
    seen.add(key);
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

export function SimpleResults({
  detail,
  report,
  summary,
  activity,
  activityEventSummary,
  formatGmtPlus3,
  onExpertMode,
  onDownload,
}) {
  const sec = report.security_integrity_signals ?? {};
  const bypass = sec.bypass_resilience ?? {};
  const verdict = useMemo(
    () => simpleVerdict(summary.score, bypass.risk_score ?? 0),
    [summary.score, bypass.risk_score],
  );
  const problems = useMemo(() => buildSimpleProblems(report, summary), [report, summary]);
  const events = (activity.events ?? []).filter((e) => e.occurred_at).slice(0, 12);

  return (
    <div className="simple-results">
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
        <SimpleStat label="Warning signs" value={problems.length} hint="Things worth reading" />
        <SimpleStat
          label="Recent activity"
          value={activity.recent_execution_count ?? 0}
          hint="Last few days"
        />
        <SimpleStat label="Files removed" value={activity.recent_deletion_count ?? 0} hint="Last week" />
        <SimpleStat label="Match score" value={summary.score} hint="Technical tally" />
      </section>

      <section className="simple-panel">
        <header className="simple-panel-head">
          <ListChecks size={22} />
          <div>
            <h4>What stood out</h4>
            <p>Short list in plain words. No need to know Windows jargon.</p>
          </div>
        </header>
        {problems.length ? (
          <div className="simple-problem-list">
            {problems.slice(0, 10).map((problem) => (
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

      <section className="simple-panel">
        <header className="simple-panel-head">
          <Clock3 size={22} />
          <div>
            <h4>What happened recently</h4>
            <p>Newest things first. Times are GMT+3.</p>
          </div>
        </header>
        {events.length ? (
          <ul className="simple-timeline">
            {events.map((event, index) => (
              <li key={`${event.path}-${event.kind}-${index}`}>
                <time>{formatGmtPlus3(event.occurred_at)}</time>
                <p>{activityEventSummary(event)}</p>
                <details className="simple-path-fold">
                  <summary>Show file path</summary>
                  <code>{event.path}</code>
                </details>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No timed activity rows on this report yet.</p>
        )}
      </section>

      <section className="simple-panel simple-panel--tips">
        <header className="simple-panel-head">
          <Sparkles size={22} />
          <div>
            <h4>How to read this</h4>
          </div>
        </header>
        <ul className="simple-tips">
          <li>
            <strong>Green-ish</strong> — nothing big matched. Still not a 100% guarantee someone is clean.
          </li>
          <li>
            <strong>Yellow</strong> — a few clues. Ask questions and look at the list above.
          </li>
          <li>
            <strong>Red</strong> — many clues. Treat this as high priority.
          </li>
        </ul>
      </section>

      <footer className="simple-footer">
        <button type="button" className="simple-expert-btn" onClick={onExpertMode}>
          Open advanced reviewer view
        </button>
        <button type="button" className="download-button" onClick={onDownload}>
          <Download size={15} /> Save full report
        </button>
      </footer>
    </div>
  );
}
