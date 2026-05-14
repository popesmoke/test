import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  BookOpen,
  Boxes,
  ChevronUp,
  Clock3,
  Clipboard,
  Cpu,
  Database,
  Download,
  FileText,
  Fingerprint,
  Gauge,
  Gamepad2,
  GitBranch,
  KeyRound,
  Lock,
  LogOut,
  MemoryStick,
  RefreshCw,
  ScanSearch,
  Shield,
  Terminal,
  Trash2,
} from "lucide-react";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL || "https://test-v7a8.onrender.com";
const BRAND_LOGO = "/assets/dangerouscity-logo.png";

function authHeaders(token) {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

function Login({ onLogin }) {
  const [email, setEmail] = useState("dng@email.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        setError("Login failed. Check the email and password.");
        return;
      }
      const data = await response.json();
      onLogin(data.token);
    } catch (error) {
      setError(`Could not reach backend at ${API_URL}`);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="login-logo-wrap">
          <img src={BRAND_LOGO} alt="DangerousCity" className="login-logo" />
        </div>
        <div className="brand-row">
          <div>
            <h1>DangerousCity</h1>
            <p>Reviewer dashboard</p>
          </div>
        </div>
        <form onSubmit={submit} className="form-stack">
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          {error && <p className="error">{error}</p>}
          <button className="primary" type="submit">
            <Lock size={18} /> Sign in
          </button>
        </form>
      </section>
    </main>
  );
}

function SessionList({ sessions, selectedId, onSelect, onDelete }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src={BRAND_LOGO} alt="" />
        <div>
          <h2>DangerousCity</h2>
          <span>PIN Sessions</span>
        </div>
      </div>
      <div className="session-list">
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`session-row-wrap ${selectedId === session.id ? "active" : ""}`}
          >
            <button type="button" className="session-row" onClick={() => onSelect(session.id)}>
              <span className="pin">{session.pin}</span>
              <span className={`status ${session.status}`}>{session.status}</span>
              <small>{formatGmtPlus3(session.created_at)}</small>
            </button>
            <button
              type="button"
              className="session-delete"
              title="Delete this session"
              aria-label={`Delete session ${session.pin}`}
              onClick={(event) => {
                event.stopPropagation();
                onDelete(session);
              }}
            >
              <Trash2 size={18} />
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}

function TerminalBlock({ children, query = "" }) {
  const text = String(children || "No relevant data found.");
  const filtered = query.trim()
    ? text
        .split("\n")
        .filter((line) => line.toLowerCase().includes(query.trim().toLowerCase()))
        .join("\n") || "No keyword matches in this section."
    : text;
  return <pre className="terminal">{filtered}</pre>;
}

function asJson(value) {
  return JSON.stringify(value ?? {}, (_, nextValue) => {
    if (typeof nextValue === "string" && isIsoDateString(nextValue)) {
      return formatGmtPlus3(nextValue);
    }
    return nextValue;
  }, 2);
}

function lines(items, mapper) {
  if (!items || items.length === 0) return "";
  return items.map(mapper).filter(Boolean).join("\n");
}

function countItems(value) {
  if (Array.isArray(value)) return value.length;
  return 0;
}

function parseMaybeJson(value) {
  if (!value || typeof value !== "string") return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function textHasSignal(value) {
  return typeof value === "string" && value.trim() && value.trim() !== "[]" && !value.toLowerCase().startsWith("unavailable");
}

function isIsoDateString(value) {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value) && !Number.isNaN(new Date(normalizeIsoDateString(value)).getTime());
}

function normalizeIsoDateString(value) {
  return String(value).replace(/\.(\d{3})\d+/, ".$1");
}

function dateMs(value) {
  if (!value) return null;
  const ms = new Date(normalizeIsoDateString(value)).getTime();
  return Number.isNaN(ms) ? null : ms;
}

function formatGmtPlus3(value) {
  if (!value) return "unknown";
  const date = new Date(normalizeIsoDateString(value));
  if (Number.isNaN(date.getTime())) return String(value);
  const formatted = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Etc/GMT-3",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
  return `${formatted.replace(",", "")} GMT+3`;
}

function isScanWindowAccess(report, value) {
  const accessMs = dateMs(value);
  const endMs = dateMs(report.generated_at);
  if (accessMs === null || endMs === null) return false;
  const startMs = dateMs(report.scan_started_at) ?? endMs - 30 * 60 * 1000;
  return accessMs >= startMs && accessMs <= endMs + 2 * 60 * 1000;
}

function openedEntry(report, item) {
  if (item.accessed) {
    if (isScanWindowAccess(report, item.accessed)) {
      return { filteredScanAccess: true };
    }
    return {
      openedAt: item.accessed,
      source: "last opened",
      filteredScanAccess: false,
    };
  }
  return {
    openedAt: null,
    source: "opened time unavailable",
    filteredScanAccess: false,
  };
}

function buildSuspicionSummary(report) {
  const sec = report.security_integrity_signals ?? {};
  const executor = sec.roblox_executor_indicators ?? {};
  const fileHits = executor.file_hits ?? [];
  const logHits = executor.traceback_or_log_hits ?? [];
  const prefetchHits = sec.prefetch_health?.indicator_hits ?? [];
  const designatedHits = sec.designated_folder_suspicious_files?.hits ?? [];
  const designatedExecutorHits = designatedHits.filter((item) => (item.executor_name_hits ?? []).length);
  const designatedWeirdHits = designatedHits.filter(
    (item) => !(item.executor_name_hits ?? []).length && (item.name_anomaly_reasons ?? []).length,
  );
  const recentMatched = (sec.recent_items?.items ?? []).filter((item) => item.matched_indicator_names?.length);
  const defenderText = `${sec.defender?.settings ?? ""}\n${sec.defender?.protection_history ?? ""}`;
  const clearingText = sec.deletion_and_log_clearing_signals?.raw_sample ?? "";
  const userAssistText = sec.userassist?.raw_sample ?? "";
  const bamText = sec.bam?.raw_sample ?? "";

  const reasons = [];
  let score = 0;

  if (fileHits.length) {
    const points = Math.min(35, fileHits.length * 7);
    score += points;
    reasons.push({
      label: "Executor file indicators",
      points,
      detail: `${fileHits.length} file or folder path matched known executor names.`,
    });
  }
  if (recentMatched.length) {
    const points = Math.min(20, recentMatched.length * 6);
    score += points;
    reasons.push({
      label: "Recent opened files",
      points,
      detail: `${recentMatched.length} recent item matched suspicious names.`,
    });
  }
  if (prefetchHits.length) {
    const points = Math.min(20, prefetchHits.length * 8);
    score += points;
    reasons.push({
      label: "Prefetch execution traces",
      points,
      detail: `${prefetchHits.length} Prefetch artifact matched a checked executor name.`,
    });
  }
  if (logHits.length) {
    const points = Math.min(15, logHits.length * 5);
    score += points;
    reasons.push({
      label: "Crash or log matches",
      points,
      detail: `${logHits.length} log file contained traceback or executor keywords.`,
    });
  }
  if (designatedExecutorHits.length) {
    const points = Math.min(28, designatedExecutorHits.length * 7);
    score += points;
    reasons.push({
      label: "Profile folder executor filenames",
      points,
      detail: `${designatedExecutorHits.length} file(s) in Downloads/Desktop/Documents matched a checked executor name (selected extensions).`,
    });
  }
  if (designatedWeirdHits.length) {
    const points = Math.min(14, designatedWeirdHits.length * 2);
    score += points;
    reasons.push({
      label: "Profile folder odd filenames",
      points,
      detail: `${designatedWeirdHits.length} file(s) had unusual name patterns under Downloads/Desktop/Documents (selected extensions).`,
    });
  }
  if (textHasSignal(userAssistText) && /executor|loader|bootstrapper|inject|bypass|cleaner|roblox/i.test(userAssistText)) {
    score += 8;
    reasons.push({
      label: "UserAssist activity",
      points: 8,
      detail: "UserAssist contained activity names matching reviewed keywords.",
    });
  }
  if (textHasSignal(bamText) && /executor|loader|inject|roblox|solara|wave|xeno|synapse/i.test(bamText)) {
    score += 7;
    reasons.push({
      label: "BAM activity",
      points: 7,
      detail: "BAM registry output included paths matching reviewed keywords.",
    });
  }
  if (/exclusion|DisableRealtimeMonitoring|threat|detected|quarantine/i.test(defenderText)) {
    score += 8;
    reasons.push({
      label: "Defender signal",
      points: 8,
      detail: "Windows Defender settings or history had security-relevant entries.",
    });
  }
  if (textHasSignal(clearingText) && !/^\s*\[\s*\]\s*$/.test(clearingText)) {
    score += 7;
    reasons.push({
      label: "Deletion or log clearing",
      points: 7,
      detail: "Event log or deletion-clearing signals were present for reviewer triage.",
    });
  }

  if (!reasons.length) {
    reasons.push({
      label: "No matched indicators",
      points: 0,
      detail:
        "The dashboard did not find executor, recent-file, profile-folder, Prefetch, crash-log, Defender, or clearing indicators in this report.",
    });
  }

  const openedCandidates = [
    ...recentMatched.map((item) => ({
      name: item.name,
      path: item.folder,
      matched: item.matched_indicator_names ?? [],
      ...openedEntry(report, item),
    })),
    ...fileHits.slice(0, 25).map((item) => ({
      name: item.path?.split(/[\\/]/).pop() ?? item.path,
      path: item.path,
      matched: item.matched_names ?? [],
      ...openedEntry(report, item),
    })),
  ].filter((item) => item.name || item.path);

  const openedFiles = openedCandidates
    .filter((item) => item.openedAt && !item.filteredScanAccess)
    .sort((a, b) => (dateMs(b.openedAt) ?? 0) - (dateMs(a.openedAt) ?? 0));
  const scanAccessFiltered = openedCandidates.filter((item) => item.filteredScanAccess).length;

  return {
    score: Math.min(100, score),
    reasons,
    openedFiles,
    scanAccessFiltered,
    counts: {
      fileHits: countItems(fileHits),
      recentMatched: countItems(recentMatched),
      prefetchHits: countItems(prefetchHits),
      logHits: countItems(logHits),
      defenderEntries: countItems(parseMaybeJson(sec.defender?.protection_history)),
    },
  };
}

function Card({ icon: Icon, title, children }) {
  return (
    <article className="result-card">
      <header className="card-title">
        <span className="icon-box"><Icon size={20} /></span>
        <h3>{title}</h3>
        <ChevronUp size={18} className="chevron" />
      </header>
      {children}
    </article>
  );
}

function StarterSection({ report }) {
  const summary = buildSuspicionSummary(report);
  const band = summary.score >= 70 ? "High" : summary.score >= 35 ? "Medium" : "Low";

  return (
    <>
      <Card icon={Gauge} title="Suspicion Score">
        <div className="score-panel">
          <div className="score-ring" aria-label={`Suspicion score ${summary.score} out of 100`}>
            <strong>{summary.score}</strong>
            <span>/100</span>
          </div>
          <div>
            <p className="score-band">{band} suspicion</p>
            <p className="muted">Score is based on matched file names, recent opened items, Prefetch hits, crash/log text, registry activity, Defender signals, and deletion or clearing signals.</p>
          </div>
        </div>
        <div className="signal-grid">
          <span>File hits <strong>{summary.counts.fileHits}</strong></span>
          <span>Recent matches <strong>{summary.counts.recentMatched}</strong></span>
          <span>Prefetch hits <strong>{summary.counts.prefetchHits}</strong></span>
          <span>Log hits <strong>{summary.counts.logHits}</strong></span>
        </div>
      </Card>
      <Card icon={AlertTriangle} title="Why It Scored This Way">
        <div className="reason-list">
          {summary.reasons.map((reason) => (
            <div className="reason-row" key={reason.label}>
              <span>{reason.points > 0 ? `+${reason.points}` : "0"}</span>
              <div>
                <strong>{reason.label}</strong>
                <p>{reason.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>
      <Card icon={Clock3} title="Last Opened Files in GMT+3">
        {summary.openedFiles.length ? (
          <div className="opened-file-list">
            {summary.openedFiles.slice(0, 30).map((item, index) => (
              <div className="opened-file-row" key={`${item.path}-${index}`}>
                <div>
                  <strong>{item.name}</strong>
                  <p>{item.path}</p>
                  <small>{(item.matched ?? []).join(", ") || "matched scan signal"}</small>
                </div>
                <time>{formatGmtPlus3(item.openedAt)}</time>
                <span>{item.source}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">
            No user-opened file time was found in this report.
            {summary.scanAccessFiltered ? ` ${summary.scanAccessFiltered} access time(s) were hidden because they happened during the scanner run.` : ""}
          </p>
        )}
      </Card>
    </>
  );
}

function RobloxSection({ report, query }) {
  const roblox = report.application_diagnostics?.roblox ?? {};
  const logs = roblox.logs ?? [];
  const accounts = [];
  for (const log of logs) {
    const signals = log.signals ?? {};
    for (const username of signals.usernames ?? []) {
      accounts.push({ label: username, detail: `Found in ${log.name}` });
    }
    for (const userId of signals.user_ids ?? []) {
      accounts.push({ label: `User ID ${userId}`, detail: `https://www.roblox.com/users/${userId}/profile` });
    }
  }

  return (
    <>
      <Card icon={Gamepad2} title="Roblox Accounts">
        <div className="account-list">
          {accounts.length === 0 ? (
            <p className="muted">No Roblox account identifiers found in approved logs.</p>
          ) : (
            accounts.slice(0, 40).map((account, index) => (
              <div className="account-row" key={`${account.label}-${index}`}>
                <div className="avatar">{account.label.slice(0, 1).toUpperCase()}</div>
                <div>
                  <strong>{account.label}</strong>
                  <span>{account.detail}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
      <Card icon={Gamepad2} title="Roblox Logs">
        <TerminalBlock query={query}>
          {lines(logs, (log) => {
            const signals = log.signals ?? {};
            const opened = openedEntry(report, log);
            return [
              `Log Name: ${log.name}`,
              `Date Modified: ${formatGmtPlus3(log.modified)}`,
              `Date Opened: ${opened.openedAt && opened.source === "last opened" ? formatGmtPlus3(opened.openedAt) : "not shown because the access time happened during the scanner run or was unavailable"}`,
              `Usernames: ${(signals.usernames ?? []).join(", ") || "none"}`,
              `User IDs: ${(signals.user_ids ?? []).join(", ") || "none"}`,
              `Place IDs: ${(signals.place_ids ?? []).join(", ") || "none"}`,
              `LoadClientSettings: ${(signals.load_client_settings ?? []).length} line(s)`,
              "------------------------------------------------------------",
            ].join("\n");
          })}
        </TerminalBlock>
      </Card>
    </>
  );
}

function SystemSection({ report, query }) {
  const system = report.system_overview ?? {};
  const perf = report.performance_environment ?? {};
  const sec = report.security_integrity_signals ?? {};
  return (
    <>
      <Card icon={Cpu} title="System Overview">
        <TerminalBlock query={query}>
          {[
            `OS: ${system.os ?? "unknown"}`,
            `Hardware Model: ${system.hardware?.hardware_model ?? system.machine ?? "unknown"}`,
            `Architecture: ${system.machine ?? "unknown"}`,
            `CPU Cores: ${system.cpu_count_physical ?? "unknown"} physical / ${system.cpu_count_logical ?? "unknown"} logical`,
            `Boot Time: ${formatGmtPlus3(perf.boot_time)}`,
            `Hashed Hostname: ${system.hostname_hash ?? "unknown"}`,
            `Hashed Hardware UUID: ${system.hardware?.uuid_hash ?? "unknown"}`,
          ].join("\n")}
        </TerminalBlock>
      </Card>
      <Card icon={Cpu} title="Services">
        <TerminalBlock query={query}>{sec.services?.raw}</TerminalBlock>
      </Card>
      <Card icon={Trash2} title="Recycle Bin">
        <TerminalBlock query={query}>{asJson(perf.trash)}</TerminalBlock>
      </Card>
      <Card icon={Terminal} title="Shell History">
        <TerminalBlock query={query}>{asJson(sec.command_history_keyword_hits)}</TerminalBlock>
      </Card>
    </>
  );
}

function BypassSection({ report, query }) {
  const sec = report.security_integrity_signals ?? {};
  return (
    <>
      <Card icon={Shield} title="Bypass Detection">
        <TerminalBlock query={query}>
          {[
            "Event Log / USN / Clearing Signals:",
            asJson(sec.deletion_and_log_clearing_signals),
            "",
            "Amcache Integrity:",
            asJson(sec.amcache),
            "",
            "Prefetch Health:",
            asJson(sec.prefetch_health),
            "",
            "Shellbag Signal:",
            asJson(sec.shellbag_clear_signal),
          ].join("\n")}
        </TerminalBlock>
      </Card>
      <Card icon={Shield} title="Log Keyword Hits">
        <TerminalBlock query={query}>{asJson(sec.roblox_executor_indicators?.traceback_or_log_hits)}</TerminalBlock>
      </Card>
    </>
  );
}

function RegistrySection({ report, query }) {
  const sec = report.security_integrity_signals ?? {};
  const perf = report.performance_environment ?? {};
  return (
    <>
      <Card icon={Database} title="Registry Activity">
        <TerminalBlock query={query}>
          {[
            "BAM Registry Entries:",
            asJson(sec.bam),
            "",
            "UserAssist Execution Evidence:",
            asJson(sec.userassist),
            "",
            "Shellbag Registry Signal:",
            asJson(sec.shellbag_clear_signal),
          ].join("\n")}
        </TerminalBlock>
      </Card>
      <Card icon={FileText} title="Execution Artifacts">
        <TerminalBlock query={query}>
          {[
            `Report Date: ${formatGmtPlus3(report.generated_at)}`,
            `Amcache Modified: ${formatGmtPlus3(sec.amcache?.modified)}`,
            `Prefetch Newest Modified: ${formatGmtPlus3(sec.prefetch_health?.newest_modified)}`,
            "",
            "Installed Applications:",
            asJson(perf.installed_applications),
          ].join("\n")}
        </TerminalBlock>
      </Card>
    </>
  );
}

function FileAnalysisSection({ report, query }) {
  const sec = report.security_integrity_signals ?? {};
  return (
    <>
      <Card icon={ScanSearch} title="Execution Artifacts">
        <TerminalBlock query={query}>
          {[
            "Keyword Scan",
            `Report Date: ${formatGmtPlus3(report.generated_at)}`,
            "============================================================",
            asJson(sec.roblox_executor_indicators?.file_hits),
            "",
            "Prefetch Indicator Hits:",
            asJson(sec.prefetch_health?.indicator_hits),
            "",
            "Downloads / Desktop / Documents (exe, dll, txt, json, log, bat, ps1):",
            asJson(sec.designated_folder_suspicious_files),
          ].join("\n")}
        </TerminalBlock>
      </Card>
      <Card icon={ScanSearch} title="File Verification">
        <TerminalBlock query={query}>Unsigned binary verification is not enabled in this prototype. Use indicator hits and Defender history for triage.</TerminalBlock>
      </Card>
    </>
  );
}

function SuspiciousFilesSection({ report, query }) {
  const sec = report.security_integrity_signals ?? {};
  return (
    <Card icon={ScanSearch} title="Suspicious Files">
      <TerminalBlock query={query}>
        {[
          "Recent files with matched keywords:",
          asJson((sec.recent_items?.items ?? []).filter((item) => item.matched_indicator_names?.length)),
          "",
          "Defender Integrity:",
          asJson(sec.defender),
        ].join("\n")}
      </TerminalBlock>
    </Card>
  );
}

function CrashLogsSection({ report, query }) {
  const hits = report.security_integrity_signals?.roblox_executor_indicators?.traceback_or_log_hits ?? [];
  return (
    <Card icon={Terminal} title="Crash Logs">
      <TerminalBlock query={query}>{hits.length ? asJson(hits) : "No crash logs detected."}</TerminalBlock>
    </Card>
  );
}

function DeletionsSection({ report, query }) {
  const sec = report.security_integrity_signals ?? {};
  const trash = report.performance_environment?.trash ?? {};
  return (
    <Card icon={Trash2} title="File Deletions">
      <TerminalBlock query={query}>
        {[
          `Report Date: ${formatGmtPlus3(report.generated_at)}`,
          "",
          "Recently Deleted Files From Recycle Bin Metadata:",
          asJson(trash.items ?? trash),
          "",
          "Deleted / Clearing Signals:",
          asJson(sec.deletion_and_log_clearing_signals),
          "",
          "Structured deletion evidence (USN multi-volume, Security 4660/4663, Sysmon 23):",
          asJson(sec.deletion_and_log_clearing_signals?.deleted_file_evidence),
          "",
          "USN Delete Sample (text):",
          sec.deletion_and_log_clearing_signals?.usn_delete_sample || "No USN delete sample available.",
          "",
          "Roblox Log Summary:",
          asJson(report.application_diagnostics?.roblox),
        ].join("\n")}
      </TerminalBlock>
    </Card>
  );
}

function MemorySection({ report, query }) {
  const processes = report.process_overview?.items ?? [];
  const robloxProcesses = processes.filter((proc) => (proc.name ?? "").toLowerCase().includes("roblox"));
  return (
    <>
      <Card icon={MemoryStick} title="Process Snapshot">
        <TerminalBlock query={query}>
          {robloxProcesses.length ? asJson(robloxProcesses) : "[OK] Roblox Memory: No running Roblox process found"}
        </TerminalBlock>
      </Card>
    </>
  );
}

function forensicSeverityClass(severity) {
  const s = String(severity ?? "").toLowerCase();
  if (s === "critical" || s === "high") return "forensic-sev forensic-sev-high";
  if (s === "medium") return "forensic-sev forensic-sev-medium";
  return "forensic-sev forensic-sev-low";
}

function ForensicFindingsSection({ report, query }) {
  const fa = report.security_integrity_signals?.forensic_analysis;
  if (!fa || fa.available === false) {
    return (
      <Card icon={Fingerprint} title="Forensic findings">
        <p className="muted">
          No forensic analysis bundle on this report. Scans from older desktop builds, or non-Windows hosts, will not
          include this section.
        </p>
      </Card>
    );
  }
  const flat = [...(fa.detections_flat ?? [])];
  const q = query.trim().toLowerCase();
  const filtered = q
    ? flat.filter((d) =>
        [d.reason, d.file_path, d.artifact_source, d.severity, JSON.stringify(d.correlated_evidence ?? [])]
          .join(" ")
          .toLowerCase()
          .includes(q),
      )
    : flat;
  const counts = Object.fromEntries(
    Object.entries(fa.detections ?? {}).map(([key, value]) => [key, Array.isArray(value) ? value.length : 0]),
  );
  return (
    <>
      <Card icon={Fingerprint} title="Forensic engine">
        <p className="muted">
          Engine <code className="inline-code">{fa.engine_version ?? "unknown"}</code>. Flattened list:{" "}
          <strong>{filtered.length}</strong> of <strong>{flat.length}</strong> (search applies here).
        </p>
      </Card>
      <Card icon={Fingerprint} title="Findings">
        <div className="forensic-findings">
          {filtered.length === 0 ? (
            <p className="muted">No findings match the current search.</p>
          ) : (
            filtered.slice(0, 150).map((d, index) => (
              <details className="forensic-finding" key={`${d.file_path ?? d.reason}-${index}`}>
                <summary className="forensic-finding-summary">
                  <span className={forensicSeverityClass(d.severity)}>{d.severity ?? "?"}</span>
                  <span className="forensic-risk">risk {d.risk_score ?? 0}</span>
                  <span className="forensic-reason">{d.reason ?? ""}</span>
                </summary>
                <div className="forensic-finding-body">
                  <p>
                    <strong>Source:</strong> {d.artifact_source ?? "—"}
                  </p>
                  <p>
                    <strong>Path:</strong> {d.file_path || "—"}
                  </p>
                  <p>
                    <strong>Confidence:</strong> {d.confidence ?? "—"}
                  </p>
                  <p>
                    <strong>SHA256:</strong>{" "}
                    <code className="inline-code">{d.sha256 || "—"}</code>
                  </p>
                  <p>
                    <strong>Signature:</strong> {d.signature_status ?? "—"}
                  </p>
                  <p>
                    <strong>Entropy:</strong>{" "}
                    {d.entropy_score != null && typeof d.entropy_score === "number" ? d.entropy_score.toFixed(2) : "—"}
                  </p>
                  <p>
                    <strong>YARA:</strong> {(d.yara_matches ?? []).join(", ") || "—"}
                  </p>
                  <pre className="terminal terminal--compact">
                    {asJson({ timestamps: d.timestamps, correlated_evidence: d.correlated_evidence })}
                  </pre>
                </div>
              </details>
            ))
          )}
        </div>
      </Card>
      <Card icon={Fingerprint} title="Counts by category">
        <TerminalBlock query={query}>{asJson(counts)}</TerminalBlock>
      </Card>
    </>
  );
}

function ForensicCorrelationSection({ report, query }) {
  const fa = report.security_integrity_signals?.forensic_analysis;
  const uc = fa?.unified_correlation ?? {};
  if (!fa || fa.available === false) {
    return (
      <Card icon={GitBranch} title="Correlation">
        <p className="muted">No unified correlation data for this report.</p>
      </Card>
    );
  }
  return (
    <>
      <Card icon={GitBranch} title="Cross-artifact summary">
        <TerminalBlock query={query}>{asJson(uc.cross_artifact_summary)}</TerminalBlock>
      </Card>
      <Card icon={GitBranch} title="Execution chains">
        <TerminalBlock query={query}>{asJson(uc.execution_chains ?? [])}</TerminalBlock>
      </Card>
      <Card icon={Clock3} title="Unified timeline (sample)">
        <TerminalBlock query={query}>{asJson((uc.timeline ?? []).slice(0, 200))}</TerminalBlock>
      </Card>
    </>
  );
}

function ForensicArtifactsSection({ report, query }) {
  const fa = report.security_integrity_signals?.forensic_analysis;
  if (!fa || fa.available === false) {
    return (
      <Card icon={Boxes} title="Artifact detail">
        <p className="muted">No structured forensic artifacts for this report.</p>
      </Card>
    );
  }
  const usnRows = (fa.usn_file_lifecycle_rows ?? []).slice(0, 100);
  return (
    <>
      <Card icon={Boxes} title="Structured BAM">
        <TerminalBlock query={query}>{asJson(fa.bam_structured)}</TerminalBlock>
      </Card>
      <Card icon={Boxes} title="PCA executed (store)">
        <TerminalBlock query={query}>{asJson(fa.pca_executed)}</TerminalBlock>
      </Card>
      <Card icon={Boxes} title="Browser SQLite probe">
        <TerminalBlock query={query}>{asJson(fa.sqlite)}</TerminalBlock>
      </Card>
      <Card icon={Boxes} title="USN lifecycle rows (parsed sample)">
        <TerminalBlock query={query}>{asJson(usnRows)}</TerminalBlock>
      </Card>
      <Card icon={Boxes} title="USN enriched sample meta">
        <TerminalBlock query={query}>{asJson(fa.usn_enriched_sample)}</TerminalBlock>
      </Card>
    </>
  );
}

function TutorialSection() {
  return (
    <>
      <Card icon={BookOpen} title="Reading a session (quick path)">
        <ol className="tutorial-steps">
          <li>
            Start on <strong>Suspicion Score</strong> for the rolled-up number and the reasons list. That view tells you
            which indicator families fired (executors, Prefetch, recent files, logs, Defender, clearing signals, and
            others).
          </li>
          <li>
            Open <strong>Forensics</strong> (also labeled <em>Evidence review</em>) for individual findings: severity,
            risk score, file path, signature, entropy, and correlated evidence. High severity with recent timestamps is
            worth prioritizing.
          </li>
          <li>
            Use <strong>Correlation</strong> (<em>Cross-source timeline</em>) to see whether separate artifacts line up in
            time—for example the same binary name appearing under BAM, Prefetch, and profile folders around the same
            window.
          </li>
          <li>
            Use <strong>Artifacts</strong> (<em>Structured OS traces</em>) for raw structured tables (BAM, PCA store, USN
            samples). This is where you confirm <em>whether</em> something ran or touched disk, not just that a string
            matched.
          </li>
          <li>
            Cross-check <strong>Roblox</strong>, <strong>Bypass Detection</strong>, <strong>Deletions</strong>, and{" "}
            <strong>Crash Logs</strong> for client-side narratives (errors, injectors named in traces, log clearing, or
            tampering hints).
          </li>
        </ol>
      </Card>
      <Card icon={BookOpen} title="Spotting recent cheating (practical signs)">
        <div className="tutorial-prose">
          <p>
            This dashboard does not prove intent; it surfaces <strong>technical indicators</strong> that often appear
            when third-party tooling interacted with the game or the OS. Treat every item as a lead to verify with your
            own policy and context.
          </p>
          <p>
            <strong>Recency without relying on a single field:</strong> compare timestamps on forensic findings, USN
            rows, Prefetch hits, and &quot;recent opened&quot; style lists against the scan window. Activity that clusters
            <em>just before</em> the player joined your review, or during the session window, is more interesting than
            old installer residue.
          </p>
          <p>
            <strong>Executor-style footprints:</strong> look for matching names across layers—disk path, BAM execution
            residue, Prefetch for the same stem, crash logs mentioning inject or executor frameworks, and downloads or
            desktop drops with suspicious filenames. One weak match can be noise; the same story repeated across
            artifacts is stronger.
          </p>
          <p>
            <strong>Evasion or cleanup:</strong> spikes on deletion or log-clearing signals, Defender exclusions, or
            &quot;missing file but Prefetch still present&quot; patterns deserve a closer read in Correlation and
            Artifacts before you close the case as clean.
          </p>
          <p className="muted">
            Always combine automated signals with gameplay evidence, eyewitness reports, and your organization&apos;s
            standards. When in doubt, run a fresh PIN session after a clean reboot and compare to a baseline.
          </p>
        </div>
      </Card>
    </>
  );
}

const resultSections = [
  { id: "starter", label: "Suspicion Score", icon: Gauge, component: StarterSection },
  { id: "tutorial", label: "Tutorial", icon: BookOpen, component: TutorialSection },
  {
    id: "forensic-findings",
    label: "Forensics",
    altLabel: "Evidence review",
    icon: Fingerprint,
    component: ForensicFindingsSection,
  },
  {
    id: "forensic-corr",
    label: "Correlation",
    altLabel: "Cross-source timeline",
    icon: GitBranch,
    component: ForensicCorrelationSection,
  },
  {
    id: "forensic-artifacts",
    label: "Artifacts",
    altLabel: "Structured OS traces",
    icon: Boxes,
    component: ForensicArtifactsSection,
  },
  { id: "roblox", label: "Roblox", icon: Gamepad2, component: RobloxSection },
  { id: "system", label: "System", icon: Cpu, component: SystemSection },
  { id: "bypass", label: "Bypass Detection", icon: Shield, component: BypassSection },
  { id: "registry", label: "Registry", icon: Database, component: RegistrySection },
  { id: "file-analysis", label: "File Analysis", icon: ScanSearch, component: FileAnalysisSection },
  { id: "suspicious", label: "Suspicious Files", icon: ScanSearch, component: SuspiciousFilesSection },
  { id: "crash", label: "Crash Logs", icon: Terminal, component: CrashLogsSection },
  { id: "deletions", label: "Deletions", icon: Trash2, component: DeletionsSection },
  { id: "memory", label: "Memory", icon: MemoryStick, component: MemorySection },
];

function Results({ detail }) {
  const [sectionId, setSectionId] = useState("starter");
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!detail?.id) {
      return;
    }
    setSectionId("starter");
    setQuery("");
  }, [detail?.id]);

  const report = detail?.report ?? {};
  const summary = buildSuspicionSummary(report);
  const activeSection = resultSections.find((section) => section.id === sectionId) ?? resultSections[0];
  const ActiveComponent = activeSection.component;
  const showSectionContent = detail.status === "completed" || sectionId === "tutorial";

  if (!detail) {
    return <section className="empty-state">Select or generate a PIN session.</section>;
  }

  return (
    <section className="scan-results">
      <aside className="results-nav">
        <button className="back-link">← My Pins</button>
        <h2>Scan results</h2>
        <p>
          {detail.completed_at
            ? `Submitted ${formatGmtPlus3(detail.completed_at)}`
            : "Waiting for the desktop client to submit results."}
        </p>
        <button className="download-button" onClick={() => downloadReport(detail)}>
          <Download size={15} /> Download report
        </button>
        <nav>
          {resultSections.map((section) => {
            const Icon = section.icon;
            return (
              <button
                key={section.id}
                className={sectionId === section.id ? "active" : ""}
                onClick={() => setSectionId(section.id)}
                type="button"
              >
                <Icon size={18} className="nav-tab-icon" />
                <span className="nav-tab-labels">
                  <span className="nav-tab-primary">{section.label}</span>
                  {"altLabel" in section && section.altLabel ? (
                    <span className="nav-tab-alt">{section.altLabel}</span>
                  ) : null}
                </span>
              </button>
            );
          })}
        </nav>
      </aside>
      <div className="result-content">
        <div className="result-header">
        <div>
          <p className="eyebrow">Session PIN</p>
          <h2>{detail.pin}</h2>
        </div>
        <div className="header-badges">
          {detail.status === "completed" && <span className="score-badge">Suspicion {summary.score}/100</span>}
          <span className={`status large ${detail.status}`}>{detail.status}</span>
        </div>
        </div>
        {!showSectionContent ? (
          <div className="empty-state">Waiting for the desktop client to submit results.</div>
        ) : (
          <>
            {sectionId !== "tutorial" ? (
              <input
                className="section-search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={`Search ${activeSection.label} keywords...`}
              />
            ) : null}
            <ActiveComponent report={report} query={query} />
          </>
        )}
      </div>
    </section>
  );
}

function downloadReport(detail) {
  const blob = new Blob([JSON.stringify(detail, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `scan-${detail.pin}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function Dashboard({ token, onLogout }) {
  const [sessions, setSessions] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const detailFetchSeq = useRef(0);

  const loadSessions = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/sessions`, { headers: authHeaders(token) });
      if (response.status === 401) {
        localStorage.removeItem("checkerToken");
        window.location.reload();
        return;
      }
      if (!response.ok) {
        throw new Error(`Session load failed: ${response.status}`);
      }
      const data = await response.json();
      setError("");
      setSessions(data);
      setSelectedId((prev) => {
        if (prev != null && data.some((s) => s.id === prev)) {
          return prev;
        }
        return data[0]?.id ?? null;
      });
    } catch (caught) {
      setError(`Could not load sessions from ${API_URL}. ${caught.message}`);
    }
  }, [token]);

  async function deleteSession(session) {
    if (
      !window.confirm(
        `Delete session PIN ${session.pin}? The scan record will be removed from the dashboard.`,
      )
    ) {
      return;
    }
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}`, {
        method: "DELETE",
        headers: authHeaders(token),
      });
      if (response.status === 401) {
        localStorage.removeItem("checkerToken");
        window.location.reload();
        return;
      }
      if (!response.ok) {
        throw new Error(`Delete failed: ${response.status}`);
      }
      setMessage(`Deleted session ${session.pin}`);
      await loadSessions();
    } catch (caught) {
      setError(caught.message);
    }
  }

  async function createPin() {
    try {
      const response = await fetch(`${API_URL}/sessions`, { method: "POST", headers: authHeaders(token) });
      if (!response.ok) {
        throw new Error(`PIN creation failed: ${response.status}`);
      }
      const data = await response.json();
      setMessage(`Generated PIN ${data.pin}`);
      setSelectedId(data.id);
      await navigator.clipboard?.writeText(data.pin).catch(() => {});
      await loadSessions();
    } catch (caught) {
      setError(caught.message);
    }
  }

  useEffect(() => {
    loadSessions();
    const timer = setInterval(loadSessions, 5000);
    return () => clearInterval(timer);
  }, [loadSessions]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }

    setDetail((prev) => (prev && prev.id === selectedId ? prev : null));

    const controller = new AbortController();
    const seq = ++detailFetchSeq.current;

    fetch(`${API_URL}/sessions/${selectedId}`, {
      headers: authHeaders(token),
      signal: controller.signal,
    })
      .then((response) => {
        if (response.status === 401) {
          localStorage.removeItem("checkerToken");
          window.location.reload();
          return null;
        }
        if (response.status === 404) {
          setDetail(null);
          void loadSessions();
          return null;
        }
        if (!response.ok) {
          throw new Error(`Result load failed: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        if (data == null) {
          return;
        }
        if (seq !== detailFetchSeq.current) {
          return;
        }
        setDetail(data);
      })
      .catch((caught) => {
        if (caught.name === "AbortError") {
          return;
        }
        if (seq !== detailFetchSeq.current) {
          return;
        }
        setError(caught.message);
        setDetail(null);
      });

    return () => controller.abort();
  }, [selectedId, sessions, token, loadSessions]);

  const selectedPin = useMemo(() => sessions.find((session) => session.id === selectedId)?.pin, [sessions, selectedId]);

  return (
    <main className="dashboard">
      <header className="topbar">
        <div className="topbar-brand">
          <img src={BRAND_LOGO} alt="" />
          <div>
            <p className="eyebrow">DangerousCity Reborn V2</p>
            <h1>Reviewer Dashboard</h1>
          </div>
        </div>
        <div className="actions">
          {selectedPin && (
            <button onClick={() => navigator.clipboard?.writeText(selectedPin)}>
              <Clipboard size={18} /> Copy PIN
            </button>
          )}
          <button onClick={loadSessions}>
            <RefreshCw size={18} /> Refresh
          </button>
          <button className="primary" onClick={createPin}>
            <KeyRound size={18} /> Generate New PIN
          </button>
          <button type="button" onClick={onLogout}>
            <LogOut size={18} /> Log out
          </button>
        </div>
      </header>
      {message && <div className="notice">{message}</div>}
      {error && <div className="error-banner">{error}</div>}
      <div className="layout">
        <SessionList
          sessions={sessions}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onDelete={deleteSession}
        />
        <Results detail={detail} />
      </div>
    </main>
  );
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("checkerToken") ?? "");
  function login(nextToken) {
    localStorage.setItem("checkerToken", nextToken);
    setToken(nextToken);
  }
  function logout() {
    localStorage.removeItem("checkerToken");
    setToken("");
  }
  return token ? <Dashboard token={token} onLogout={logout} /> : <Login onLogin={login} />;
}

try {
  createRoot(document.getElementById("root")).render(<App />);
} catch (error) {
  document.body.innerHTML = `<main class="login-shell"><section class="login-panel"><h1>Dashboard Error</h1><p class="error">${error.message}</p></section></main>`;
}
