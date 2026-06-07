import React, { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
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
  History,
  KeyRound,
  LogOut,
  MessageCircle,
  MemoryStick,
  RefreshCw,
  ScanSearch,
  Shield,
  Terminal,
  Trash2,
} from "lucide-react";
import "./styles.css";
import { SimpleResults } from "./SimpleResults.jsx";

const API_URL = import.meta.env.VITE_API_URL || "https://virello-secure.onrender.com";
const BRAND_LOGO = "/assets/virello-scanner-logo.png";
const BRAND_NAME = "Virello Scanner";
const DISCORD_INVITE_URL = import.meta.env.VITE_DISCORD_INVITE_URL || "https://discord.gg/wPZXKaPyWY";
const GMT_PLUS3_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Etc/GMT-3",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

function authHeaders(token) {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

const DISCORD_ERROR_MESSAGES = {
  discord_auth_failed: "Discord login failed. Please try again.",
  invalid_state: "Discord login expired. Please try again.",
  missing_code: "Discord did not return a login code. Please try again.",
};

async function startDiscordLogin() {
  const returnTo = `${window.location.origin}${window.location.pathname}`;
  const response = await fetch(
    `${API_URL}/auth/discord/start?return_to=${encodeURIComponent(returnTo)}`,
  );
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.url) {
    throw new Error(data.detail || "Could not start Discord login.");
  }
  window.location.assign(data.url);
}

function Login({ loginError }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(loginError || "");

  useEffect(() => {
    setError(loginError || "");
  }, [loginError]);

  async function handleDiscordLogin() {
    setError("");
    setBusy(true);
    try {
      await startDiscordLogin();
    } catch (caught) {
      setError(caught.message || `Could not reach backend at ${API_URL}`);
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="login-logo-wrap">
          <img src={BRAND_LOGO} alt={BRAND_NAME} className="login-logo" />
        </div>
        <div className="brand-row">
          <div>
            <p>Sign in with Discord to check scan results in plain, simple language.</p>
          </div>
        </div>
        <div className="form-stack login-discord-stack">
          {error && <p className="error">{error}</p>}
          <p className="login-help">
            You need the <strong>Access</strong> role in our Discord server to use PIN sessions and scan results.
            If you do not have it yet, you can still sign in and see what to do next.
          </p>
          <a className="discord-invite" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
            Need access? Join the Discord server.
          </a>
          <button className="primary discord-login-button" type="button" onClick={handleDiscordLogin} disabled={busy}>
            <MessageCircle size={18} />
            {busy ? "Connecting to Discord..." : "Continue with Discord"}
          </button>
        </div>
      </section>
    </main>
  );
}

function formatSessionStatus(status) {
  if (status === "expired") return "expired";
  if (status === "pending") return "pending";
  if (status === "completed") return "completed";
  return status || "unknown";
}

function SessionList({ sessions, selectedId, onSelect, onDelete }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src={BRAND_LOGO} alt="" />
        <div>
          <h2>{BRAND_NAME}</h2>
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
              <span className={`status ${formatSessionStatus(session.status)}`}>
                {formatSessionStatus(session.status)}
              </span>
              {session.status === "pending" && session.expires_at ? (
                <small className="session-expires">until {formatGmtPlus3(session.expires_at)}</small>
              ) : null}
              {session.status === "expired" && session.expires_at ? (
                <small className="session-expires">expired {formatGmtPlus3(session.expires_at)}</small>
              ) : null}
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

function safeArray(value) {
  return Array.isArray(value) ? value : [];
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
  const formatted = GMT_PLUS3_FORMATTER.format(date);
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
  const accessed = item.accessed ?? null;
  const modified = item.modified ?? null;
  if (accessed && isScanWindowAccess(report, accessed)) {
    return { filteredScanAccess: true };
  }
  if (!modified && !accessed) {
    return {
      displayAt: null,
      accessedAt: null,
      modifiedAt: null,
      source: "timestamps unavailable",
      filteredScanAccess: false,
    };
  }
  return {
    displayAt: modified ?? accessed,
    accessedAt: accessed,
    modifiedAt: modified,
    source: "mtime + atime",
    filteredScanAccess: false,
  };
}

function pathStemKey(pathValue) {
  if (!pathValue) return "";
  const base = String(pathValue).split(/[\\/]/).pop() ?? "";
  const dot = base.lastIndexOf(".");
  return (dot > 0 ? base.slice(0, dot) : base).toLowerCase();
}

function recencyFactor(timestamp, report) {
  const eventMs = dateMs(timestamp);
  const endMs = dateMs(report.generated_at) ?? dateMs(report.scan_started_at);
  if (eventMs === null || endMs === null) return 1;
  const hours = (endMs - eventMs) / 3_600_000;
  if (hours <= 24) return 1;
  if (hours <= 72) return 0.75;
  if (hours <= 168) return 0.5;
  return 0.35;
}

function isScoredPath(item) {
  return item?.path_allowlisted !== true;
}

function registerStem(stemMap, stem, source) {
  if (!stem || stem.length < 2) return;
  if (!stemMap.has(stem)) stemMap.set(stem, new Set());
  stemMap.get(stem).add(source);
}

function multiArtifactBonus(stemMap) {
  let bonus = 0;
  for (const sources of stemMap.values()) {
    if (sources.size >= 2) bonus += Math.min(10, sources.size * 3);
  }
  return Math.min(18, bonus);
}

function forensicScoreContribution(fa) {
  if (!fa || fa.available === false) return { points: 0, browserOnly: 0, diskBacked: 0 };
  const flat = safeArray(fa.detections_flat);
  let browserOnly = 0;
  let diskBacked = 0;
  for (const finding of flat) {
    if ((finding.reason ?? "").includes("Unified forensic pass completed")) continue;
    const risk = Number(finding.risk_score) || 0;
    if (risk <= 0) continue;
    const slice = Math.min(6, Math.ceil(risk / 18));
    if (finding.browser_only) {
      browserOnly += slice;
    } else {
      diskBacked += slice;
    }
  }
  return {
    points: Math.min(22, diskBacked) + Math.min(5, browserOnly),
    browserOnly,
    diskBacked,
  };
}

function buildSuspicionSummary(report) {
  const sec = report.security_integrity_signals ?? {};
  const executor = sec.roblox_executor_indicators ?? {};
  const fileHits = (executor.file_hits ?? []).filter(isScoredPath);
  const logHits = executor.traceback_or_log_hits ?? [];
  const prefetchHits = sec.prefetch_health?.indicator_hits ?? [];
  const designatedHits = (sec.designated_folder_suspicious_files?.hits ?? []).filter(isScoredPath);
  const shaHits = sec.executor_sha256_blocklist?.hits ?? [];
  const persistenceSuspicious = (sec.persistence_signals?.suspicious_entries ?? []).filter(isScoredPath);
  const runtimeModules = sec.roblox_runtime_integrity?.suspicious_modules ?? [];
  const designatedExecutorHits = designatedHits.filter((item) => (item.executor_name_hits ?? []).length);
  const designatedCheatOnlyHits = designatedHits.filter(
    (item) =>
      (item.cheat_filename_hints ?? []).length &&
      !(item.executor_name_hits ?? []).length &&
      !(item.name_anomaly_reasons ?? []).length,
  );
  const designatedWeirdHits = designatedHits.filter(
    (item) => !(item.executor_name_hits ?? []).length && (item.name_anomaly_reasons ?? []).length,
  );
  const removedArtifactHits = designatedHits.filter((item) => item.removed_artifact);
  const recycleSuspicious = (report.performance_environment?.trash?.items ?? []).filter(
    (item) => item.suspicious_recycle_item && item.original_path,
  );
  const recentMatched = (sec.recent_items?.items ?? []).filter(
    (item) =>
      (item.matched_indicator_names?.length ?? 0) > 0 || (item.matched_cheat_filename_hints?.length ?? 0) > 0,
  );
  const defenderText = `${sec.defender?.settings ?? ""}\n${sec.defender?.protection_history ?? ""}`;
  const clearingText = sec.deletion_and_log_clearing_signals?.raw_sample ?? "";
  const userAssistText = sec.userassist?.raw_sample ?? "";
  const bamText = sec.bam?.raw_sample ?? "";
  const bypass = sec.bypass_resilience ?? {};
  const artifactEvidence = sec.executor_artifact_evidence?.hits ?? [];

  const stemMap = new Map();
  for (const item of fileHits) registerStem(stemMap, pathStemKey(item.path), "file");
  for (const item of prefetchHits) registerStem(stemMap, pathStemKey(item.name ?? item.path), "prefetch");
  for (const item of designatedExecutorHits) registerStem(stemMap, pathStemKey(item.path), "profile");
  for (const item of removedArtifactHits) registerStem(stemMap, pathStemKey(item.path), "removed");
  for (const item of artifactEvidence) registerStem(stemMap, pathStemKey(item.path), String(item.artifact_source ?? "artifact"));
  for (const item of runtimeModules) registerStem(stemMap, pathStemKey(item.module_path), "runtime");

  const reasons = [];
  let score = 0;

  if (shaHits.length) {
    const points = Math.min(40, shaHits.length * 20);
    score += points;
    reasons.push({
      label: "Known executor binary hash",
      points,
      detail: `${shaHits.length} file(s) matched a verified SHA256 blocklist entry.`,
    });
  }

  if (artifactEvidence.length) {
    const deletedCount = artifactEvidence.filter(
      (item) => item.file_exists === false || item.removed_artifact,
    ).length;
    const weighted = artifactEvidence.reduce((sum, item) => {
      const deleted = item.file_exists === false || item.removed_artifact;
      const source = String(item.artifact_source ?? "");
      const sourceBoost =
        source === "prefetch_execution" || source === "bam_execution" || source === "dam_execution" ? 1.15 : 1;
      const base = deleted ? 13 : 10;
      return sum + base * sourceBoost * recencyFactor(item.display_at ?? item.modified, report);
    }, 0);
    const points = Math.min(50, Math.round(weighted));
    if (points > 0) {
      score += points;
      const executors = [
        ...new Set(
          artifactEvidence.flatMap((item) => item.executor_name_hits ?? []).filter(Boolean),
        ),
      ].slice(0, 6);
      reasons.push({
        label: "Executor artifact evidence",
        points,
        detail: `${artifactEvidence.length} trace(s) from ${(sec.executor_artifact_evidence?.sources_used ?? []).join(", ") || "Windows artifacts"}${executors.length ? ` (${executors.join(", ")})` : ""}${deletedCount ? `; ${deletedCount} refer to paths no longer on disk.` : "."}`,
      });
    }
  }

  if (runtimeModules.length) {
    const liveCount = runtimeModules.filter((item) => item.scan_mode === "live").length;
    const offlineCount = runtimeModules.length - liveCount;
    const points = Math.min(35, runtimeModules.length * 10);
    score += points;
    reasons.push({
      label: "Roblox integrity signals",
      points,
      detail:
        liveCount && offlineCount
          ? `${liveCount} live module hit(s) with Roblox open and ${offlineCount} offline artifact hit(s) from logs, BAM, Prefetch, or folders.`
          : liveCount
            ? `${liveCount} suspicious module(s) in a live Roblox process.`
            : `${offlineCount} offline Roblox-related signal(s) from logs or disk (game did not need to be running).`,
    });
  }

  if (fileHits.length) {
    const weighted = fileHits.reduce((sum, item) => sum + 7 * recencyFactor(item.modified, report), 0);
    const points = Math.min(35, Math.round(weighted));
    if (points > 0) {
      score += points;
      reasons.push({
        label: "Executor / cheat path matches",
        points,
        detail: `${fileHits.length} non-allowlisted path(s); points weighted by recency of file modified time.`,
      });
    }
  }
  if (recentMatched.length) {
    const weighted = recentMatched.reduce(
      (sum, item) => sum + 6 * recencyFactor(item.modified ?? item.accessed, report),
      0,
    );
    const points = Math.min(20, Math.round(weighted));
    if (points > 0) {
      score += points;
      reasons.push({
        label: "Executor / cheat-tagged recent files",
        points,
        detail: `${recentMatched.length} recent item(s); points weighted toward activity in the last 72 hours.`,
      });
    }
  }
  if (prefetchHits.length) {
    const weighted = prefetchHits.reduce(
      (sum, item) => sum + 8 * recencyFactor(item.modified, report),
      0,
    );
    const points = Math.min(20, Math.round(weighted));
    if (points > 0) {
      score += points;
      reasons.push({
        label: "Prefetch execution traces",
        points,
        detail: `${prefetchHits.length} Prefetch artifact(s) matched a checked executor name.`,
      });
    }
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
    const weighted = designatedExecutorHits.reduce(
      (sum, item) => sum + 7 * recencyFactor(item.modified, report),
      0,
    );
    const points = Math.min(28, Math.round(weighted));
    if (points > 0) {
      score += points;
      reasons.push({
        label: "Profile folder executor filenames",
        points,
        detail: `${designatedExecutorHits.length} file(s) in Downloads/Desktop/Documents matched a checked executor name.`,
      });
    }
  }
  if (designatedCheatOnlyHits.length) {
    const points = Math.min(12, designatedCheatOnlyHits.length * 4);
    score += points;
    reasons.push({
      label: "Profile folder cheat-like filenames",
      points,
      detail: `${designatedCheatOnlyHits.length} file(s) had cheat/hack-style filename hints (lower weight than executor-name hits).`,
    });
  }
  if (designatedWeirdHits.length) {
    const points = Math.min(6, designatedWeirdHits.length);
    if (points > 0) {
      score += points;
      reasons.push({
        label: "Profile folder odd filenames",
        points,
        detail: `${designatedWeirdHits.length} file(s) had unusual name patterns (low weight; verify manually).`,
      });
    }
  }
  if (removedArtifactHits.length) {
    const weighted = removedArtifactHits.reduce((sum, item) => {
      const hasExecutor = (item.executor_name_hits ?? []).length > 0;
      const hasCheat = (item.cheat_filename_hints ?? []).length > 0;
      const base = hasExecutor ? 11 : hasCheat ? 8 : 6;
      return sum + base * recencyFactor(item.display_at ?? item.modified, report);
    }, 0);
    const points = Math.min(42, Math.round(weighted));
    if (points > 0) {
      score += points;
      reasons.push({
        label: "Deleted cheat/executor traces recovered",
        points,
        detail: `${removedArtifactHits.length} path(s) were deleted or removed from the Recycle Bin but recovered from BAM, USN, Prefetch, downloads, or other Windows artifacts.`,
      });
    }
  }
  if (recycleSuspicious.length) {
    const points = Math.min(18, recycleSuspicious.length * 6);
    score += points;
    reasons.push({
      label: "Suspicious Recycle Bin items",
      points,
      detail: `${recycleSuspicious.length} item(s) in the Recycle Bin matched executor or cheat path rules (original path preserved in $I metadata).`,
    });
  }
  if (persistenceSuspicious.length) {
    const points = Math.min(22, persistenceSuspicious.length * 6);
    score += points;
    reasons.push({
      label: "Persistence mechanisms",
      points,
      detail: `${persistenceSuspicious.length} Run key, startup, task, or shortcut entry matched executor/cheat patterns.`,
    });
  }

  const forensic = forensicScoreContribution(sec.forensic_analysis);
  if (forensic.points > 0) {
    score += forensic.points;
    reasons.push({
      label: "Forensic engine findings",
      points: forensic.points,
      detail: `Disk-backed forensic signals contributed up to ${forensic.diskBacked} pts; browser-only history hits capped at ${Math.min(5, forensic.browserOnly)} pts.`,
    });
  }

  const artifactBonus = multiArtifactBonus(stemMap);
  if (artifactBonus > 0) {
    score += artifactBonus;
    reasons.push({
      label: "Cross-artifact agreement",
      points: artifactBonus,
      detail: "The same program stem appeared in multiple independent sources (disk, Prefetch, profile, or runtime).",
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
  if (bypass.available && (bypass.findings?.length ?? 0) > 0) {
    const points = Math.min(32, Math.round((bypass.risk_score ?? 0) * 0.4));
    if (points > 0) {
      score += points;
      reasons.push({
        label: "Bypass / cover-up signals",
        points,
        detail: `${bypass.finding_count ?? bypass.findings.length} anti-tamper check(s) fired (registry, defender, ghosts, WMI, downloads, correlation).`,
      });
    }
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
      matched: [
        ...(item.matched_indicator_names ?? []),
        ...(item.matched_cheat_filename_hints ?? []).map((h) => `cheat:${h}`),
      ],
      ...openedEntry(report, item),
    })),
    ...fileHits.slice(0, 25).map((item) => ({
      name: item.path?.split(/[\\/]/).pop() ?? item.path,
      path: item.path,
      matched: [
        ...(item.matched_names ?? []),
        ...(item.cheat_filename_hints ?? []).map((h) => `cheat:${h}`),
      ],
      ...openedEntry(report, item),
    })),
  ].filter((item) => item.name || item.path);

  const openedFiles = openedCandidates
    .filter((item) => item.displayAt && !item.filteredScanAccess)
    .sort((a, b) => (dateMs(b.displayAt) ?? 0) - (dateMs(a.displayAt) ?? 0));
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
      shaBlocklistHits: countItems(shaHits),
      persistenceHits: countItems(persistenceSuspicious),
      runtimeModules: countItems(runtimeModules),
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

const EXECUTOR_VERDICT_LABELS = {
  likely_recent_executor_activity: "Likely recent executor use or download",
  possible_executor_activity: "Possible executor-related activity",
  no_matched_executor_activity: "No matched executor activity",
};

const EXECUTOR_KIND_LABELS = {
  sha256_blocklist: "Known binary hash",
  recent_file: "Recent file name match",
  prefetch_execution: "Prefetch execution",
  profile_folder: "Profile folder file",
  filesystem_indicator: "Filesystem scan",
  bam_execution: "BAM execution record",
  persistence: "Startup / persistence",
};

const ACTIVITY_CATEGORY_LABELS = {
  deletions: "Deletions",
  execution: "Execution",
  files: "Files",
  persistence: "Persistence",
  commands: "Commands",
  roblox: "Roblox",
  browser: "Browser",
  filesystem: "Filesystem",
};

const ACTIVITY_KIND_LABELS = {
  recycle_bin: "Recycle Bin delete",
  recycle_bin_artifact: "Recycle Bin item",
  security_audit_delete: "Security audit delete",
  sysmon_file_delete: "Sysmon file delete",
  usn_journal: "USN journal",
  bam_execution: "BAM execution",
  userassist: "UserAssist launch",
  pca_compat: "PCA compatibility",
  prefetch: "Prefetch",
  prefetch_indicator: "Prefetch indicator",
  recent_download: "Recent download",
  profile_folder: "Profile folder",
  filesystem_scan: "Filesystem scan",
  sha256_blocklist: "SHA256 blocklist",
  persistence: "Persistence",
  shell_history: "Shell history",
  roblox_log: "Roblox log",
  browser_history: "Browser history",
  browser_download: "Browser download",
};

function explainTimestampSource(source) {
  if (!source) return "";
  return "Timestamp inferred from available system metadata in this scan.";
}

function activityEventSummary(event) {
  if (event?.summary) return event.summary;
  const name = basenameOf(event?.path || "") || "a file";
  const quoted = name ? `“${name}”` : "a file";
  const byKind = {
    recycle_bin: `The user deleted ${quoted} and Windows moved it to the Recycle Bin.`,
    recycle_bin_artifact: `Recycle Bin still holds metadata for ${quoted}.`,
    security_audit_delete: `A system log recorded delete-related activity for ${quoted}.`,
    sysmon_file_delete: `A system trace indicates ${quoted} was deleted.`,
    usn_journal: `Windows logged a filesystem change for ${quoted}.`,
    bam_execution: `A system execution trace was recorded for ${quoted}.`,
    userassist: `A user-launch trace was recorded for ${quoted}.`,
    pca_compat: `A compatibility trace was recorded for ${quoted}.`,
    prefetch: `A system runtime trace was recorded for ${quoted}.`,
    prefetch_indicator: `A runtime trace for ${quoted} matched a reviewed signal.`,
    recent_download: `A file in Downloads or Desktop matched review keywords: ${quoted}.`,
    profile_folder: `A profile-folder file matched review keywords: ${quoted}.`,
    filesystem_scan: `A filesystem scan flagged ${quoted} for review.`,
    sha256_blocklist: `The hash of ${quoted} matches a known executor.`,
    persistence: `Startup or persistence data references ${quoted}.`,
    shell_history: "A PowerShell history line matched reviewed keywords.",
    roblox_log: `Roblox log activity involved ${quoted}.`,
    browser_history: `Browser history included a visit related to ${quoted}.`,
    browser_download: `A file was downloaded in the browser: ${quoted}.`,
    removed_executor_artifact: `Evidence remains for ${quoted} even though it was removed from disk and the Recycle Bin.`,
  };
  let summary = byKind[event?.kind] || `${ACTIVITY_KIND_LABELS[event?.kind] ?? event?.kind ?? "Activity"} involving ${quoted}.`;
  const label = String(event?.label || "").trim();
  if (label && !["GUI launch", "keyword", "Compatibility Assistant", "Prefetch trace"].includes(label)) {
    summary += ` Matched: ${label}.`;
  }
  return summary;
}

function executorEventSummary(event) {
  if (event?.summary) return event.summary;
  const name = basenameOf(event?.path || "") || "a file";
  const quoted = name ? `“${name}”` : "a file";
  const byKind = {
    sha256_blocklist: `Known executor hash match for ${quoted}.`,
    recent_file: `Recent file ${quoted} matched a reviewed executor or cheat name.`,
    prefetch_execution: `A runtime trace shows ${quoted} ran and matched a reviewed name.`,
    profile_folder: `Profile folder file ${quoted} matched review rules.`,
    filesystem_indicator: `Filesystem scan flagged ${quoted}.`,
    bam_execution: `A system execution trace was recorded for ${quoted} with a name match.`,
    persistence: `Startup or persistence references ${quoted}.`,
  };
  let summary = byKind[event?.kind] || `Executor-related activity involving ${quoted}.`;
  const label = String(event?.label || "").trim();
  if (label) summary += ` Matched: ${label}.`;
  return summary;
}

function timelineRowSummary(row) {
  if (row?.summary) return row.summary;
  const name = basenameOf(row?.path || "") || "a file";
  const quoted = name ? `“${name}”` : "a file";
  return `System activity record involving ${quoted}.`;
}

function artifactFriendlyLabel(artifact) {
  if (!artifact) return "System trace";
  return "System trace";
}

function openedFilePlainSummary(item) {
  const name = item.name || basenameOf(item.path) || "this file";
  const matched = (item.matched ?? []).join(", ");
  const parts = [
    `The file “${name}” was last changed on disk at the time shown (modified time).`,
  ];
  if (item.accessedAt && !item.filteredScanAccess) {
    parts.push(
      "Windows also recorded OS-level read access at the secondary time — any program (game, antivirus, search) can update that, so it is not proof the user opened it in Explorer.",
    );
  } else if (item.filteredScanAccess) {
    parts.push(`Access time during the scan window was hidden because ${BRAND_NAME} touched the file.`);
  }
  if (matched) parts.push(`Matched review signals: ${matched}.`);
  return parts.join(" ");
}

function pathKey(path) {
  return String(path || "").replace(/\//g, "\\").toLowerCase();
}

function basenameOf(path) {
  const key = pathKey(path);
  const slash = key.lastIndexOf("\\");
  return slash >= 0 ? key.slice(slash + 1) : key;
}

function pathsRelate(left, right) {
  const a = pathKey(left);
  const b = pathKey(right);
  if (!a || !b) return false;
  if (a === b || a.endsWith(b) || b.endsWith(a)) return true;
  const base = basenameOf(a);
  return Boolean(base) && base === basenameOf(b);
}

function enrichPcaItemFromReport(report, item) {
  if (!item) return item;
  if (item.display_at) return item;
  const sec = report.security_integrity_signals ?? {};
  const fa = sec.forensic_analysis ?? {};
  const perf = report.performance_environment ?? {};
  const norm = item.normalized_path || item.raw || "";
  const stem = basenameOf(norm).replace(/\.[^.]+$/, "").toUpperCase();
  const correlated = { ...(item.correlated_timestamps || {}) };
  const add = (source, ts) => {
    if (ts && !correlated[source]) correlated[source] = ts;
  };

  const bamItems = [
    ...(fa.bam_structured?.items ?? []),
    ...(sec.bam?.items ?? []),
  ];
  for (const row of bamItems) {
    const bp = row.normalized_path || row.registry_path_value;
    if (pathsRelate(norm, bp) && row.last_execution_utc) add("bam_execution", row.last_execution_utc);
  }

  for (const row of perf.prefetch?.items ?? []) {
    const name = String(row.name || "");
    const pfStem = name.replace(/-[0-9A-F]{8}\.pf$/i, "").replace(/\.pf$/i, "").toUpperCase();
    if (pfStem === stem && row.modified) add("prefetch_mtime", row.modified);
  }

  for (const row of fa.usn_file_lifecycle_rows ?? []) {
    const ts = row.display_at || row.timestamp_utc;
    if (!ts) continue;
    if (pathsRelate(norm, row.path) || basenameOf(norm) === basenameOf(row.raw || row.path)) {
      const isDelete = (row.reasons ?? []).some((r) => String(r).includes("DELETE"));
      add(isDelete ? "usn_delete" : "usn_journal", ts);
    }
  }

  for (const row of perf.trash?.items ?? []) {
    const ts = row.display_at || row.deleted_at || row.modified;
    if (pathsRelate(norm, row.original_path) && ts) add("recycle_bin", ts);
  }

  for (const row of sec.designated_folder_suspicious_files?.hits ?? []) {
    if (pathsRelate(norm, row.path) && row.modified) add("designated_mtime", row.modified);
  }

  for (const row of sec.recent_items?.items ?? []) {
    const combined = row.folder && row.name ? `${row.folder}\\${row.name}` : row.name || row.folder;
    if (pathsRelate(norm, combined) && row.modified) add("recent_mtime", row.modified);
  }

  for (const row of sec.userassist?.items ?? []) {
    if (pathsRelate(norm, row.path) && row.last_run_utc) add("userassist", row.last_run_utc);
  }

  for (const hit of sec.command_history_keyword_hits?.hits ?? []) {
    const ts = hit.occurred_at || hit.history_file_modified_utc;
    const line = hit.line || "";
    if (!ts) continue;
    if (pathsRelate(norm, line) || line.toLowerCase().includes(basenameOf(norm).toLowerCase())) {
      add("powershell_history", ts);
    }
  }

  const order = [
    "bam_execution",
    "prefetch_mtime",
    "usn_delete",
    "powershell_history",
    "recycle_bin",
    "designated_mtime",
    "recent_mtime",
    "userassist",
    "usn_journal",
  ];
  let displayAt = null;
  let timestampSource = null;
  for (const key of order) {
    if (correlated[key]) {
      displayAt = correlated[key];
      timestampSource = key;
      break;
    }
  }

  return {
    ...item,
    correlated_timestamps: Object.keys(correlated).length ? correlated : item.correlated_timestamps,
    display_at: displayAt,
    timestamp_source: timestampSource,
  };
}

function enrichedPcaItems(report) {
  const items = safeArray(report.security_integrity_signals?.forensic_analysis?.pca_executed?.items);
  return items.map((item) => enrichPcaItemFromReport(report, item));
}

const EMPTY_PATH_TIMESTAMP = { display_at: null, timestamp_source: null, correlated: {} };

function resolvePathTimestampFromReport(report, path, pcaItems = null) {
  if (!path) return EMPTY_PATH_TIMESTAMP;
  const sec = report.security_integrity_signals ?? {};
  const fa = sec.forensic_analysis ?? {};
  const perf = report.performance_environment ?? {};
  const correlated = {};
  const add = (source, ts) => {
    if (ts && !correlated[source]) correlated[source] = ts;
  };

  const pcaList = pcaItems ?? enrichedPcaItems(report);
  const pca = pcaList.find((item) => pathsRelate(path, item.normalized_path || item.raw));
  if (pca?.display_at) {
    return {
      display_at: pca.display_at,
      timestamp_source: pca.timestamp_source,
      correlated: pca.correlated_timestamps || {},
    };
  }

  for (const row of [...(fa.bam_structured?.items ?? []), ...(sec.bam?.items ?? [])]) {
    const bp = row.normalized_path || row.registry_path_value;
    if (pathsRelate(path, bp) && row.last_execution_utc) add("bam_execution", row.last_execution_utc);
  }
  for (const row of perf.prefetch?.items ?? []) {
    const name = String(row.name || "");
    const stem = name.replace(/-[0-9A-F]{8}\.pf$/i, "").replace(/\.pf$/i, "").toUpperCase();
    if (stem === basenameOf(path).replace(/\.[^.]+$/, "").toUpperCase() && row.modified) {
      add("prefetch_mtime", row.modified);
    }
  }
  for (const hit of sec.command_history_keyword_hits?.hits ?? []) {
    const ts = hit.occurred_at || hit.history_file_modified_utc;
    const line = hit.line || "";
    if (!ts) continue;
    if (pathsRelate(path, line) || line.toLowerCase().includes(basenameOf(path).toLowerCase())) {
      add("powershell_history", ts);
    }
  }

  const order = ["bam_execution", "prefetch_mtime", "powershell_history", "usn_delete", "recycle_bin"];
  for (const key of order) {
    if (correlated[key]) {
      return { display_at: correlated[key], timestamp_source: key, correlated };
    }
  }
  return EMPTY_PATH_TIMESTAMP;
}

function findingMatchesQuery(d, q) {
  const base = [d.reason || "", d.file_path || "", d.artifact_source || "", d.severity || ""]
    .join(" ")
    .toLowerCase();
  if (base.includes(q)) return true;
  for (const entry of safeArray(d.correlated_evidence)) {
    if (JSON.stringify(entry).toLowerCase().includes(q)) return true;
  }
  return false;
}

function findingResolvedTime(report, finding) {
  const direct = finding.timestamps?.display_at;
  if (direct && direct !== "null" && direct !== "None" && String(direct).trim()) return direct;
  const resolved = resolvePathTimestampFromReport(report, finding.file_path || "");
  return resolved.display_at ?? null;
}

function findingTimestampSource(report, finding) {
  const direct = finding.timestamps?.timestamp_source;
  if (direct && String(direct).trim()) return direct;
  return resolvePathTimestampFromReport(report, finding.file_path || "").timestamp_source;
}

function userActivityFromReport(report) {
  const bundled = report.security_integrity_signals?.user_activity_timeline;
  if (bundled?.available) {
    return bundled;
  }
  return buildClientSideUserActivity(report);
}

function buildClientSideUserActivity(report) {
  const sec = report.security_integrity_signals ?? {};
  const trash = report.performance_environment?.trash ?? {};
  const events = [];
  for (const item of trash.items ?? []) {
    const path = item.original_path || item.name || item.location || "";
    events.push({
      category: "deletions",
      kind: item.original_path ? "recycle_bin" : "recycle_bin_artifact",
      label: item.original_path ? "Deleted to Recycle Bin" : "Recycle Bin item",
      path,
      occurred_at: item.display_at || item.deleted_at || item.modified || null,
      timestamp_source: item.timestamp_source || (item.deleted_at ? "recycle_metadata" : "file_mtime"),
      recency: recencyBucket(item.display_at || item.deleted_at || item.modified, report),
      detail: item.original_path
        ? `Legacy report — re-scan with the latest ${BRAND_NAME} for full deletion timeline.`
        : "Recycle Bin artifact without parsed $I metadata.",
    });
  }
  for (const item of sec.bam?.items ?? []) {
    if (!item.normalized_path) continue;
    events.push({
      category: "execution",
      kind: "bam_execution",
      label: "Program executed",
      path: item.normalized_path,
      occurred_at: item.last_execution_utc || null,
      timestamp_source: "bam_registry",
      recency: recencyBucket(item.last_execution_utc, report),
      detail: "BAM execution record from legacy report fields.",
    });
  }
  events.sort((a, b) => dateMs(b.occurred_at) - dateMs(a.occurred_at));
  const withTs = events.filter((e) => e.occurred_at);
  return {
    available: true,
    event_count: events.length,
    timestamped_event_count: withTs.length,
    missing_timestamp_count: events.length - withTs.length,
    recent_deletion_count: events.filter((e) => e.category === "deletions" && ["last_24h", "last_72h", "last_7d"].includes(e.recency)).length,
    recent_execution_count: events.filter((e) => e.category === "execution" && ["last_24h", "last_72h"].includes(e.recency)).length,
    by_category: events.reduce((acc, e) => {
      acc[e.category] = (acc[e.category] || 0) + 1;
      return acc;
    }, {}),
    by_recency: events.reduce((acc, e) => {
      acc[e.recency || "unknown"] = (acc[e.recency || "unknown"] || 0) + 1;
      return acc;
    }, {}),
    insights: [
      events.length
        ? `Partial timeline built from legacy report data. Install the latest ${BRAND_NAME} for UserAssist, USN, and browser history timestamps.`
        : "No activity timeline on this report — re-scan with the latest desktop client.",
    ],
    events: events.slice(0, 120),
    note: "Legacy report fallback.",
  };
}

function formatTimestampSource(source) {
  if (!source) return "";
  return String(source).replace(/_/g, " ");
}

function formatTimestampSourceWithHint(source, event) {
  const label = formatTimestampSource(source);
  const explanation = event?.source_explanation || explainTimestampSource(source);
  return explanation ? `${label} — ${explanation}` : label;
}

function UserActivitySection({ report, query }) {
  const activity = userActivityFromReport(report);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const q = query.trim().toLowerCase();
  const filtered = (activity.events ?? []).filter((event) => {
    if (categoryFilter !== "all" && event.category !== categoryFilter) return false;
    if (!q) return true;
    return [event.label, event.path, event.detail, event.kind, event.category, event.timestamp_source]
      .join(" ")
      .toLowerCase()
      .includes(q);
  });
  const categories = Object.keys(activity.by_category ?? {});

  return (
    <>
      <Card icon={History} title="User activity timeline">
        <div className="activity-analytics">
          <div className="activity-stat-grid">
            <div className="activity-stat">
              <strong>{activity.event_count ?? 0}</strong>
              <span>Total events</span>
            </div>
            <div className="activity-stat">
              <strong>{activity.timestamped_event_count ?? 0}</strong>
              <span>With timestamps</span>
            </div>
            <div className="activity-stat">
              <strong>{activity.recent_deletion_count ?? 0}</strong>
              <span>Deletions (7d)</span>
            </div>
            <div className="activity-stat">
              <strong>{activity.recent_execution_count ?? 0}</strong>
              <span>Executions (72h)</span>
            </div>
          </div>
          {(activity.insights ?? []).length ? (
            <div className="activity-insights">
              <strong>Insights</strong>
              <ul>
                {activity.insights.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <p className="muted activity-note">
            Every row shows when the action happened (GMT+3). Deleted items use Recycle Bin $I metadata first, then
            metadata or data-file fallbacks — so null timestamps are resolved when any OS trace remains.
          </p>
        </div>
        <div className="activity-filters">
          <button
            type="button"
            className={categoryFilter === "all" ? "active" : ""}
            onClick={() => setCategoryFilter("all")}
          >
            All ({activity.event_count ?? 0})
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              className={categoryFilter === cat ? "active" : ""}
              onClick={() => setCategoryFilter(cat)}
            >
              {ACTIVITY_CATEGORY_LABELS[cat] ?? cat} ({activity.by_category[cat]})
            </button>
          ))}
        </div>
        {filtered.length ? (
          <div className="executor-event-list activity-event-list">
            {filtered.slice(0, 80).map((event, index) => (
              <div className="executor-event-row activity-event-row" key={`${event.path}-${event.kind}-${index}`}>
                <div>
                  <span className={`recency-pill ${event.recency ?? "unknown"}`}>
                    {(event.recency ?? "unknown").replace(/_/g, " ")}
                  </span>
                  <span className="activity-category-pill">{ACTIVITY_CATEGORY_LABELS[event.category] ?? event.category}</span>
                  <p className="plain-summary">{activityEventSummary(event)}</p>
                  <p className="executor-event-path">{event.path}</p>
                  <small className="muted">{event.detail}</small>
                  {event.timestamp_source ? (
                    <small className="timestamp-source">
                      Time reference: {formatTimestampSourceWithHint(event.timestamp_source, event)}
                    </small>
                  ) : null}
                </div>
                <div className="activity-time-col">
                  <time>{event.occurred_at ? formatGmtPlus3(event.occurred_at) : "No timestamp"}</time>
                  {!event.occurred_at ? <span className="time-label muted">needs re-scan or Admin</span> : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No activity events match the current filter.</p>
        )}
        {activity.note ? <p className="muted small-note">{activity.note}</p> : null}
      </Card>
    </>
  );
}

function executorActivityFromReport(report) {
  const sec = report.security_integrity_signals ?? {};
  const bundled = sec.executor_activity_summary;
  if (bundled?.available) {
    return bundled;
  }
  return buildClientSideExecutorActivity(report);
}

function buildClientSideExecutorActivity(report) {
  const summary = buildSuspicionSummary(report);
  const events = summary.openedFiles.slice(0, 40).map((item) => ({
    kind: "filesystem_indicator",
    label: (item.matched ?? []).join(", ") || "matched",
    path: item.path,
    occurred_at: item.displayAt,
    recency: recencyBucket(item.displayAt, report),
    detail: `Derived from legacy report fields (re-scan with the latest ${BRAND_NAME} for full timeline).`,
  }));
  return {
    available: true,
    verdict: events.length ? "possible_executor_activity" : "no_matched_executor_activity",
    event_count: events.length,
    recent_event_count: events.filter((e) => e.recency === "last_24h" || e.recency === "last_72h").length,
    hash_hit_count: 0,
    events,
    note: `Legacy report; install the latest ${BRAND_NAME} build for hash and BAM correlation.`,
  };
}

function recencyBucket(timestamp, report) {
  const factor = recencyFactor(timestamp, report);
  if (factor >= 1) return "last_24h";
  if (factor >= 0.75) return "last_72h";
  if (factor >= 0.5) return "last_7d";
  return "older";
}

function ExecutorActivityCard({ report }) {
  const activity = executorActivityFromReport(report);
  const verdictLabel = EXECUTOR_VERDICT_LABELS[activity.verdict] ?? activity.verdict ?? "Unknown";
  const verdictClass =
    activity.verdict === "likely_recent_executor_activity"
      ? "high"
      : activity.verdict === "possible_executor_activity"
        ? "medium"
        : "low";

  return (
    <Card icon={ScanSearch} title="Executor activity (recent first)">
      <div className="executor-activity-panel">
        <div className={`executor-verdict ${verdictClass}`}>
          <strong>{verdictLabel}</strong>
          <span>
            {activity.recent_event_count ?? 0} event(s) in the last {activity.recent_window_hours ?? 72}h
            {(activity.hash_hit_count ?? 0) > 0 ? ` · ${activity.hash_hit_count} hash match(es)` : ""}
          </span>
        </div>
        <p className="muted executor-activity-note">
          One place for downloads, execution traces, renamed binaries (SHA256), Prefetch, and BAM — no need to search
          other tabs for executor signals.
        </p>
        {activity.events?.length ? (
          <div className="executor-event-list">
            {activity.events.slice(0, 25).map((event, index) => (
              <div className="executor-event-row" key={`${event.path}-${event.kind}-${index}`}>
                <div>
                  <span className={`recency-pill ${event.recency ?? "unknown"}`}>
                    {(event.recency ?? "unknown").replace(/_/g, " ")}
                  </span>
                  <span className="activity-category-pill">{EXECUTOR_KIND_LABELS[event.kind] ?? event.kind}</span>
                  <p className="plain-summary">{executorEventSummary(event)}</p>
                  <p className="executor-event-path">{event.path}</p>
                  <small className="muted">{event.detail}</small>
                </div>
                <time>{event.occurred_at ? formatGmtPlus3(event.occurred_at) : "—"}</time>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No executor, cheat-hint, or known-hash activity was aggregated for this session.</p>
        )}
        {activity.note ? <p className="muted small-note">{activity.note}</p> : null}
      </div>
    </Card>
  );
}

function StarterSection({ report }) {
  const summary = buildSuspicionSummary(report);
  const band = summary.score >= 70 ? "High" : summary.score >= 35 ? "Medium" : "Low";

  return (
    <>
      <ExecutorActivityCard report={report} />
      <Card icon={Gauge} title="Suspicion Score">
        <div className="score-panel">
          <div className="score-ring" aria-label={`Suspicion score ${summary.score} out of 100`}>
            <strong>{summary.score}</strong>
            <span>/100</span>
          </div>
          <div>
            <p className="score-band">{band} suspicion</p>
            <p className="muted">Score is based on executor or cheat-like filename matches, profile-folder scans, Prefetch hits, crash/log text, registry activity, Defender signals, and deletion or clearing signals.</p>
          </div>
        </div>
        <div className="signal-grid">
          <span>File hits <strong>{summary.counts.fileHits}</strong></span>
          <span>Recent matches <strong>{summary.counts.recentMatched}</strong></span>
          <span>Prefetch hits <strong>{summary.counts.prefetchHits}</strong></span>
          <span>Runtime modules <strong>{summary.counts.runtimeModules}</strong></span>
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
      <Card icon={Clock3} title="Tracked files (modified + OS access, GMT+3)">
        <p className="muted opened-files-intro">
          Primary time is <strong>file modified (mtime)</strong> — when the file last changed on disk. Secondary line is{" "}
          <strong>OS last access (atime)</strong>; Windows updates this when <em>any</em> program reads the file (games,
          antivirus, search), so it is <em>not</em> reliable as &quot;you opened it in Explorer&quot;.
        </p>
        {summary.openedFiles.length ? (
          <div className="opened-file-list">
            {summary.openedFiles.slice(0, 30).map((item, index) => (
              <div className="opened-file-row" key={`${item.path}-${index}`}>
                <div>
                  <p className="plain-summary">{openedFilePlainSummary(item)}</p>
                  <p className="executor-event-path">{item.path}</p>
                </div>
                <div className="opened-file-times">
                  <time>{formatGmtPlus3(item.displayAt)}</time>
                  <span className="time-label">modified</span>
                  {item.accessedAt ? (
                    <>
                      <time className="secondary-time">{formatGmtPlus3(item.accessedAt)}</time>
                      <span className="time-label muted">OS access</span>
                    </>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">
            No matching executor or cheat-hint files with usable timestamps were listed in this report.
            {summary.scanAccessFiltered
              ? ` ${summary.scanAccessFiltered} OS access time(s) were hidden because they fell during the ${BRAND_NAME} run.`
              : ""}
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
              `Date Opened: ${
                opened.displayAt && !opened.filteredScanAccess
                  ? `mtime ${formatGmtPlus3(opened.displayAt)}` +
                    (opened.accessedAt ? `; atime ${formatGmtPlus3(opened.accessedAt)}` : "")
                  : `not shown because OS access fell during the ${BRAND_NAME} run or timestamps were unavailable`
              }`,
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
        <p className="muted panel-intro">
          PowerShell PSReadLine does not store per-command UTC. The time shown is when the history file was last
          updated — usually when recent commands (low &quot;lines from end&quot;) were entered.
        </p>
        {(sec.command_history_keyword_hits?.hits ?? []).length ? (
          <div className="evidence-list">
            {(sec.command_history_keyword_hits.hits ?? [])
              .filter((hit) => {
                const q = query.trim().toLowerCase();
                if (!q) return true;
                return [hit.line, hit.matched, hit.path].join(" ").toLowerCase().includes(q);
              })
              .slice(0, 40)
              .map((hit, index) => (
                <div className="evidence-row evidence-row--static" key={`sh-${index}`}>
                  <div className="evidence-row-main">
                    <strong className="evidence-row-title">{(hit.matched ?? []).join(", ") || "keyword"}</strong>
                    <p className="evidence-row-path">{hit.line}</p>
                    <small className="evidence-row-meta">
                      {hit.lines_from_end != null ? `${hit.lines_from_end} line(s) from end of history` : "history match"}
                    </small>
                  </div>
                  <time className="evidence-row-time">
                    {hit.occurred_at || hit.history_file_modified_utc
                      ? formatGmtPlus3(hit.occurred_at || hit.history_file_modified_utc)
                      : "No timestamp"}
                  </time>
                </div>
              ))}
          </div>
        ) : (
          <p className="muted">No matching shell history lines.</p>
        )}
        <details className="raw-fold">
          <summary>View raw shell history JSON</summary>
          <TerminalBlock query={query}>{asJson(sec.command_history_keyword_hits)}</TerminalBlock>
        </details>
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
            "Detected file indicators:",
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
  const activity = userActivityFromReport(report);
  const deletionEvents = (activity.events ?? []).filter((e) => e.category === "deletions");
  const trashItems = (trash.items ?? []).filter((item) => item.original_path || item.name?.startsWith?.("$I"));

  return (
    <>
      <Card icon={Trash2} title="Deleted files (resolved timestamps)">
        <p className="muted opened-files-intro">
          Times are shown in <strong>GMT+3</strong>. When Recycle Bin $I metadata is missing or zeroed, {BRAND_NAME} falls
          back to metadata file mtime or companion $R data file mtime so reviewers still see an approximate delete window.
        </p>
        {deletionEvents.length ? (
          <div className="executor-event-list">
            {deletionEvents.slice(0, 40).map((event, index) => (
              <div className="executor-event-row" key={`del-${event.path}-${index}`}>
                <div>
                  <span className={`recency-pill ${event.recency ?? "unknown"}`}>
                    {(event.recency ?? "unknown").replace(/_/g, " ")}
                  </span>
                  <p className="plain-summary">{activityEventSummary(event)}</p>
                  <p className="executor-event-path">{event.path}</p>
                  <small className="muted">{event.detail}</small>
                  {event.timestamp_source ? (
                    <small className="timestamp-source">
                      Time reference: {formatTimestampSourceWithHint(event.timestamp_source, event)}
                    </small>
                  ) : null}
                </div>
                <time>{event.occurred_at ? formatGmtPlus3(event.occurred_at) : "No timestamp"}</time>
              </div>
            ))}
          </div>
        ) : trashItems.length ? (
          <div className="executor-event-list">
            {trashItems.slice(0, 30).map((item, index) => (
              <div className="executor-event-row" key={`trash-${item.name}-${index}`}>
                <div>
                  <strong>{item.original_path || item.name}</strong>
                  <p className="executor-event-path">{item.location}</p>
                  {item.timestamp_source ? (
                    <small className="timestamp-source">Source: {formatTimestampSource(item.timestamp_source)}</small>
                  ) : null}
                </div>
                <time>
                  {formatGmtPlus3(item.display_at || item.deleted_at || item.modified)}
                </time>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No deleted-file evidence with timestamps was collected.</p>
        )}
      </Card>
      <Card icon={Trash2} title="Deletion evidence">
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
            "Structured deletion evidence:",
            asJson(sec.deletion_and_log_clearing_signals?.deleted_file_evidence),
          ].join("\n")}
        </TerminalBlock>
      </Card>
    </>
  );
}

function MemorySection({ report, query }) {
  const processes = report.process_overview?.items ?? [];
  const robloxProcesses = processes.filter((proc) => (proc.name ?? "").toLowerCase().includes("roblox"));
  const runtime = report.security_integrity_signals?.roblox_runtime_integrity ?? {};
  const persistence = report.security_integrity_signals?.persistence_signals ?? {};
  const shaBlocklist = report.security_integrity_signals?.executor_sha256_blocklist ?? {};
  return (
    <>
      <Card icon={MemoryStick} title="Roblox integrity (live + offline)">
        <TerminalBlock query={query}>
          {runtime.available === false
            ? runtime.reason ?? "Roblox integrity scan not available on this host."
            : runtime.suspicious_modules?.length
              ? asJson(runtime)
              : "[OK] No suspicious Roblox integrity signals were found in available artifacts."}
        </TerminalBlock>
      </Card>
      <Card icon={MemoryStick} title="Persistence signals">
        <TerminalBlock query={query}>
          {persistence.available === false
            ? persistence.reason ?? "Persistence scan not available."
            : asJson(persistence)}
        </TerminalBlock>
      </Card>
      <Card icon={MemoryStick} title="Known binary fingerprint matches">
        <TerminalBlock query={query}>{asJson(shaBlocklist)}</TerminalBlock>
      </Card>
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
  const q = query.trim().toLowerCase();
  const pcaItems = useMemo(() => enrichedPcaItems(report), [report]);
  const resolvePathTimestampCached = useMemo(() => {
    const cache = new Map();
    return (path) => {
      const key = pathKey(path);
      if (!key) return EMPTY_PATH_TIMESTAMP;
      if (!cache.has(key)) {
        cache.set(key, resolvePathTimestampFromReport(report, path, pcaItems));
      }
      return cache.get(key);
    };
  }, [report, pcaItems]);
  const flat = useMemo(
    () =>
      safeArray(fa?.detections_flat).filter(
        (d) => d && typeof d === "object" && !(d.reason ?? "").includes("Unified forensic pass completed"),
      ),
    [fa?.detections_flat],
  );
  const filtered = useMemo(
    () => (q ? flat.filter((d) => findingMatchesQuery(d, q)) : flat),
    [q, flat],
  );
  const highCount = useMemo(
    () => filtered.filter((d) => ["critical", "high"].includes(String(d.severity ?? "").toLowerCase())).length,
    [filtered],
  );
  const withTime = useMemo(
    () =>
      filtered.filter((d) => {
        const direct = d.timestamps?.display_at;
        if (direct && direct !== "null" && direct !== "None" && String(direct).trim()) return true;
        return Boolean(resolvePathTimestampCached(d.file_path || "").display_at);
      }).length,
    [filtered, resolvePathTimestampCached],
  );
  const missingPca = useMemo(
    () => pcaItems.filter((i) => !i.file_exists && !i.display_at).length,
    [pcaItems],
  );
  const visibleFindings = useMemo(
    () =>
      filtered.slice(0, 40).map((d) => {
        const directWhen = d.timestamps?.display_at;
        const hasDirectWhen =
          directWhen && directWhen !== "null" && directWhen !== "None" && String(directWhen).trim();
        const directSrc = d.timestamps?.timestamp_source;
        const resolved = resolvePathTimestampCached(d.file_path || "");
        const when = hasDirectWhen ? directWhen : resolved.display_at ?? null;
        const src = directSrc && String(directSrc).trim() ? directSrc : resolved.timestamp_source;
        const correlated =
          (d.timestamps?.correlated && Object.keys(d.timestamps.correlated).length ? d.timestamps.correlated : null) ||
          resolved.correlated;
        return { d, when, src, correlated };
      }),
    [filtered, resolvePathTimestampCached],
  );
  if (!fa || fa.available === false) {
    return (
      <Card icon={Fingerprint} title="Evidence review">
        <p className="muted">
          No forensic analysis bundle on this report. Scans from older desktop builds, or non-Windows hosts, will not
          include this section.
        </p>
      </Card>
    );
  }

  return (
    <>
      <div className="review-stats">
        <div className="review-stat">
          <strong>{filtered.length}</strong>
          <span>Findings</span>
        </div>
        <div className="review-stat review-stat--warn">
          <strong>{highCount}</strong>
          <span>High / critical</span>
        </div>
        <div className="review-stat">
          <strong>{withTime}</strong>
          <span>With timestamps</span>
        </div>
        <div className="review-stat">
          <strong>{missingPca}</strong>
          <span>Missing time</span>
        </div>
      </div>
      <Card icon={Fingerprint} title="Evidence review">
        <p className="muted panel-intro">
          Reviewer-first layout — expand a row for hash and signature detail. Times are GMT+3; deleted paths are
          cross-matched across available system traces when {BRAND_NAME} can.
          {filtered.length > 40 ? ` Showing the first 40 of ${filtered.length} findings (use search to narrow).` : ""}
        </p>
        <div className="evidence-list">
          {filtered.length === 0 ? (
            <p className="muted">No findings match the current search.</p>
          ) : (
            visibleFindings.map(({ d, when, src, correlated }, index) => {
              return (
                <details className="evidence-row" key={`${d.file_path ?? d.reason}-${index}`}>
                  <summary className="evidence-row-summary">
                    <span className={forensicSeverityClass(d.severity)}>{d.severity ?? "?"}</span>
                    <div className="evidence-row-main">
                      <strong className="evidence-row-title">{d.reason ?? "Finding"}</strong>
                      <p className="plain-summary evidence-plain-summary">
                        {d.file_path
                          ? `Review item for “${basenameOf(d.file_path)}” at the path below.`
                          : "Review item with no file path attached."}
                      </p>
                      <p className="evidence-row-path">{d.file_path || "—"}</p>
                      <small className="evidence-row-meta">
                        {d.artifact_source ?? "—"} · risk {d.risk_score ?? 0}
                        {src ? ` · ${formatTimestampSource(src)}` : ""}
                      </small>
                    </div>
                    <time className="evidence-row-time">
                      {when ? formatGmtPlus3(when) : "No timestamp"}
                    </time>
                  </summary>
                  <div className="evidence-row-body">
                    <div className="evidence-detail-grid">
                      <span>Confidence</span>
                      <strong>{d.confidence ?? "—"}</strong>
                      <span>Signature</span>
                      <strong>{d.signature_status ?? "—"}</strong>
                      <span>SHA256</span>
                      <strong className="mono">{d.sha256 || "—"}</strong>
                      <span>Entropy</span>
                      <strong>
                        {d.entropy_score != null && typeof d.entropy_score === "number"
                          ? d.entropy_score.toFixed(2)
                          : "—"}
                      </strong>
                    </div>
                    {correlated && Object.keys(correlated).length ? (
                      <p className="muted small-note">
                        Linked times:{" "}
                        {Object.entries(correlated)
                          .map(([k, v]) => `${formatTimestampSource(k)} ${formatGmtPlus3(v)}`)
                          .join(" · ")}
                      </p>
                    ) : null}
                    {safeArray(d.correlated_evidence).length ? (
                      <details className="raw-fold">
                        <summary>Technical detail</summary>
                        <pre className="terminal terminal--compact">
                          {asJson({
                            timestamps: {
                              display_at: when,
                              timestamp_source: src,
                              correlated,
                            },
                            correlated_evidence: safeArray(d.correlated_evidence),
                          })}
                        </pre>
                      </details>
                    ) : null}
                  </div>
                </details>
              );
            })
          )}
        </div>
      </Card>
      <PcaExecutedCard report={report} query={query} />
    </>
  );
}

function PcaExecutedCard({ report, query }) {
  const items = useMemo(
    () => enrichedPcaItems(report).filter((item) => item.normalized_path || item.raw),
    [report],
  );
  const q = query.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      q
        ? items.filter((item) =>
            [item.normalized_path, item.raw, item.timestamp_source, JSON.stringify(item.correlated_timestamps ?? {})]
              .join(" ")
              .toLowerCase()
              .includes(q),
          )
        : items,
    [q, items],
  );
  const missing = useMemo(() => filtered.filter((item) => !item.file_exists && !item.display_at), [filtered]);

  return (
    <Card icon={Boxes} title="Compatibility trace programs">
      <p className="muted panel-intro">
        Programs Windows Compatibility Assistant recorded. Deleted files show the best available time from linked
        artifacts — not raw null fields.
      </p>
      {missing.length ? (
        <p className="muted small-note">{missing.length} deleted path(s) still have no correlated time.</p>
      ) : null}
      <div className="evidence-list">
        {filtered.length === 0 ? (
          <p className="muted">No compatibility records match the current search.</p>
        ) : (
          filtered.slice(0, 50).map((item, index) => (
            <div className="evidence-row evidence-row--static" key={`pca-${item.normalized_path}-${index}`}>
              <div className="evidence-row-main">
                <p className="plain-summary">
                  A compatibility-related system trace exists for{" "}
                  <strong>{basenameOf(item.normalized_path || item.raw)}</strong>.
                </p>
                <p className="evidence-row-path">{item.normalized_path || item.raw}</p>
                <small className="evidence-row-meta">
                  {item.file_exists ? "File still on disk" : "File no longer on disk"}
                  {item.timestamp_source
                    ? ` · ${formatTimestampSourceWithHint(item.timestamp_source)}`
                    : ""}
                </small>
                {item.correlated_timestamps ? (
                  <small className="timestamp-source">
                    Also linked to:{" "}
                    {Object.keys(item.correlated_timestamps)
                      .map((k) => formatTimestampSource(k))
                      .join(", ")}
                  </small>
                ) : null}
              </div>
              <time className="evidence-row-time">
                {item.display_at ? formatGmtPlus3(item.display_at) : "No timestamp"}
              </time>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

function ForensicCorrelationSection({ report, query }) {
  const fa = report.security_integrity_signals?.forensic_analysis;
  const uc = fa?.unified_correlation ?? {};
  const pcaEnriched = useMemo(() => enrichedPcaItems(report), [report]);
  const timeline = useMemo(() => {
    if (!fa || fa.available === false) return [];
    return safeArray(uc.timeline).map((row) => {
      if (row.artifact !== "pca_store" || row.timestamp) return row;
      const match = pcaEnriched.find((item) => pathsRelate(row.path || "", item.normalized_path || item.raw));
      if (match?.display_at) return { ...row, timestamp: match.display_at };
      return row;
    });
  }, [fa, uc.timeline, pcaEnriched]);
  const q = query.trim().toLowerCase();
  const timelineFiltered = useMemo(
    () =>
      q
        ? timeline.filter((row) =>
            [row.artifact, row.path, row.detail, row.timestamp].join(" ").toLowerCase().includes(q),
          )
        : timeline,
    [q, timeline],
  );

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
        <details className="raw-fold">
          <summary>View summary JSON</summary>
          <TerminalBlock query={query}>{asJson(uc.cross_artifact_summary)}</TerminalBlock>
        </details>
      </Card>
      <Card icon={GitBranch} title="Execution chains">
        <details className="raw-fold">
          <summary>View execution chains JSON</summary>
          <TerminalBlock query={query}>{asJson(uc.execution_chains ?? [])}</TerminalBlock>
        </details>
      </Card>
      <Card icon={Clock3} title="Cross-source timeline">
        <p className="muted panel-intro">
          Merged Windows traces in plain language (newest first). Each row explains what happened; technical artifact
          names are expanded in the glossary above.
        </p>
        <div className="evidence-list">
          {timelineFiltered.slice(0, 80).map((row, index) => (
            <div className="evidence-row evidence-row--static" key={`tl-${row.artifact}-${index}`}>
              <div className="evidence-row-main">
                <p className="plain-summary">{timelineRowSummary(row)}</p>
                <p className="evidence-row-path">{row.path || "—"}</p>
                <small className="evidence-row-meta">Trace type: {row.artifact_label || artifactFriendlyLabel(row.artifact)}</small>
              </div>
              <time className="evidence-row-time">
                {row.timestamp ? formatGmtPlus3(row.timestamp) : "No timestamp"}
              </time>
            </div>
          ))}
        </div>
        <details className="raw-fold">
          <summary>View raw timeline JSON</summary>
          <TerminalBlock query={query}>{asJson(timelineFiltered.slice(0, 200))}</TerminalBlock>
        </details>
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
  const usnRows = safeArray(fa.usn_file_lifecycle_rows).slice(0, 100);
  return (
    <>
      <Card icon={Boxes} title="Structured execution traces">
        <details className="raw-fold">
          <summary>View execution trace JSON</summary>
          <TerminalBlock query={query}>{asJson(fa.bam_structured)}</TerminalBlock>
        </details>
      </Card>
      <Card icon={Boxes} title="Browser SQLite probe">
        <details className="raw-fold">
          <summary>View browser SQLite JSON</summary>
          <TerminalBlock query={query}>{asJson(fa.sqlite)}</TerminalBlock>
        </details>
      </Card>
      <Card icon={Boxes} title="File lifecycle sample">
        <details className="raw-fold">
          <summary>View lifecycle rows JSON</summary>
          <TerminalBlock query={query}>{asJson(usnRows)}</TerminalBlock>
        </details>
      </Card>
    </>
  );
}

const resultSections = [
  { id: "starter", label: "Suspicion Score", icon: Gauge, component: StarterSection },
  { id: "user-activity", label: "User Activity", icon: History, component: UserActivitySection },
  {
    id: "forensic-findings",
    label: "Evidence",
    icon: Fingerprint,
    component: ForensicFindingsSection,
  },
  {
    id: "forensic-corr",
    label: "Cross-source timeline",
    icon: GitBranch,
    component: ForensicCorrelationSection,
  },
  {
    id: "forensic-artifacts",
    label: "Structured OS traces",
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
const resultSectionById = Object.fromEntries(resultSections.map((section) => [section.id, section]));

function Results({ detail }) {
  const [sectionId, setSectionId] = useState("starter");
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [expertMode, setExpertMode] = useState(false);

  useEffect(() => {
    if (!detail?.id) {
      return;
    }
    setSectionId("starter");
    setQuery("");
    setExpertMode(false);
  }, [detail?.id]);

  const report = detail?.report ?? {};
  // Large reports can make tab switches feel sluggish if recomputed on every render.
  const summary = useMemo(() => buildSuspicionSummary(report), [report]);
  const activity = useMemo(() => userActivityFromReport(report), [report]);
  const activeSection = resultSectionById[sectionId] ?? resultSections[0];
  const ActiveComponent = activeSection.component;
  if (!detail) {
    return <section className="empty-state">Select or generate a PIN session.</section>;
  }
  const showSectionContent = detail.status === "completed";

  return (
    <section className={`scan-results ${expertMode ? "scan-results--expert" : "scan-results--simple"}`}>
      <aside className="results-nav">
        {expertMode ? (
          <button className="back-link" type="button" onClick={() => setExpertMode(false)}>
            ← Simple view
          </button>
        ) : (
          <p className="back-link back-link--static">Easy results</p>
        )}
        <h2>{expertMode ? "Advanced review" : "Scan results"}</h2>
        <p>
          {detail.completed_at
            ? `Submitted ${formatGmtPlus3(detail.completed_at)}`
            : "Waiting for the desktop client to submit results."}
        </p>
        <button className="download-button" onClick={() => downloadReport(detail)}>
          <Download size={15} /> Download report
        </button>
        {expertMode ? (
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
                  </span>
                </button>
              );
            })}
          </nav>
        ) : (
          <p className="results-nav-hint">
            Use the tabs: Summary, Last activity, Download history, Programs run, Program list, Word matches.
          </p>
        )}
      </aside>
      <div className="result-content">
        <div className="result-header">
        <div>
          <p className="eyebrow">Session PIN</p>
          <h2>{detail.pin}</h2>
        </div>
        <div className="header-badges">
          {detail.status === "completed" && (
            <span className="score-badge">
              {expertMode ? `Suspicion ${summary.score}/100` : `Concern ${Math.min(100, Math.round(summary.score * 0.75 + ((report.security_integrity_signals?.bypass_resilience?.risk_score ?? 0) * 0.35)))}/100`}
            </span>
          )}
          <span className={`status large ${formatSessionStatus(detail.status)}`}>
            {formatSessionStatus(detail.status)}
          </span>
          {showSectionContent && !expertMode ? (
            <button type="button" className="text-button header-expert-link" onClick={() => setExpertMode(true)}>
              Advanced review
            </button>
          ) : null}
        </div>
        </div>
        {!showSectionContent ? (
          <div className="empty-state">Waiting for the desktop client to submit results.</div>
        ) : expertMode ? (
          <>
            <input
              className="section-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={`Search ${activeSection.label} keywords...`}
            />
            <ActiveComponent report={report} query={deferredQuery} />
          </>
        ) : (
          <SimpleResults
            report={report}
            summary={summary}
            activity={activity}
            activityEventSummary={activityEventSummary}
            formatGmtPlus3={formatGmtPlus3}
            onExpertMode={() => setExpertMode(true)}
            onDownload={() => downloadReport(detail)}
          />
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
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [verifyBusy, setVerifyBusy] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const detailFetchSeq = useRef(0);

  const hasAccess = Boolean(profile?.has_access);

  const loadProfile = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/auth/me`, { headers: authHeaders(token) });
      if (response.status === 401) {
        localStorage.removeItem("checkerToken");
        window.location.reload();
        return;
      }
      if (!response.ok) {
        throw new Error(`Profile load failed: ${response.status}`);
      }
      const data = await response.json();
      setProfile(data);
      setError("");
    } catch (caught) {
      setError(`Could not load your profile from ${API_URL}. ${caught.message}`);
    } finally {
      setProfileLoading(false);
    }
  }, [token]);

  async function verifyAccess() {
    setVerifyBusy(true);
    setError("");
    try {
      await startDiscordLogin();
    } catch (caught) {
      setError(caught.message);
      setVerifyBusy(false);
    }
  }

  const loadSessions = useCallback(async () => {
    if (!hasAccess) {
      setSessions([]);
      setSelectedId(null);
      setDetail(null);
      return;
    }
    try {
      const response = await fetch(`${API_URL}/sessions`, { headers: authHeaders(token) });
      if (response.status === 401) {
        localStorage.removeItem("checkerToken");
        window.location.reload();
        return;
      }
      if (response.status === 403) {
        setSessions([]);
        setSelectedId(null);
        setDetail(null);
        await loadProfile();
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
  }, [token, hasAccess, loadProfile]);

  async function deleteSession(session) {
    if (!hasAccess) {
      return;
    }
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
    if (!hasAccess) {
      return;
    }
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
    void loadProfile();
  }, [loadProfile]);

  useEffect(() => {
    if (profileLoading) {
      return;
    }
    void loadSessions();
    if (!hasAccess) {
      return;
    }
    const timer = setInterval(loadSessions, 5000);
    return () => clearInterval(timer);
  }, [loadSessions, profileLoading, hasAccess]);

  const selectedPin = useMemo(() => sessions.find((session) => session.id === selectedId)?.pin, [sessions, selectedId]);
  const selectedSessionStatus = useMemo(
    () => sessions.find((session) => session.id === selectedId)?.status,
    [sessions, selectedId],
  );

  useEffect(() => {
    if (!hasAccess || !selectedId) {
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
  }, [selectedId, selectedSessionStatus, token, loadSessions, hasAccess]);

  const greetingName = profile?.username || "there";

  return (
    <main className="dashboard">
      <header className="topbar">
        <div className="topbar-brand">
          <img src={BRAND_LOGO} alt="" />
          <div>
            <p className="eyebrow">{BRAND_NAME}</p>
            <h1>Hi, {greetingName}</h1>
            <p className="topbar-subtitle">
              {hasAccess
                ? "Welcome back. Generate a PIN, then review completed scans here."
                : "You are signed in, but dashboard tools stay locked until you have Access."}
            </p>
          </div>
        </div>
        <div className="topbar-user">
          {profile?.avatar_url ? (
            <img src={profile.avatar_url} alt="" className="topbar-avatar" />
          ) : null}
          <div className="actions">
          {hasAccess && selectedPin && (
            <button onClick={() => navigator.clipboard?.writeText(selectedPin)}>
              <Clipboard size={18} /> Copy PIN
            </button>
          )}
          {hasAccess ? (
            <>
              <button onClick={loadSessions}>
                <RefreshCw size={18} /> Refresh
              </button>
              <button className="primary" onClick={createPin}>
                <KeyRound size={18} /> Generate New PIN
              </button>
            </>
          ) : (
            <button className="primary" onClick={verifyAccess} disabled={verifyBusy}>
              <Shield size={18} /> {verifyBusy ? "Checking Discord..." : "Verify Access"}
            </button>
          )}
          <button type="button" onClick={onLogout}>
            <LogOut size={18} /> Log out
          </button>
          </div>
        </div>
      </header>
      {!hasAccess ? (
        <section className="access-gate">
          <div className="access-gate-card">
            <Shield size={28} />
            <div>
              <h2>Access not verified yet</h2>
              <p>
                Join our Discord server and get the <strong>Access</strong> role. After that, click{" "}
                <strong>Verify Access</strong> to unlock PIN generation and scan results.
              </p>
            </div>
            <div className="access-gate-actions">
              <a className="discord-invite inline-invite" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
                Open Discord server
              </a>
              <button className="primary" type="button" onClick={verifyAccess} disabled={verifyBusy}>
                {verifyBusy ? "Checking Discord..." : "Verify Access"}
              </button>
            </div>
          </div>
        </section>
      ) : null}
      {message && <div className="notice">{message}</div>}
      {error && <div className="error-banner">{error}</div>}
      <div className={`layout ${hasAccess ? "" : "layout-locked"}`}>
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
  const [loginError, setLoginError] = useState("");

  useEffect(() => {
    document.title = BRAND_NAME;
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const nextToken = params.get("token");
    const discordError = params.get("discord_error");
    if (!nextToken && !discordError) {
      return;
    }
    const cleanUrl = `${window.location.origin}${window.location.pathname}${window.location.hash}`;
    window.history.replaceState({}, document.title, cleanUrl);
    if (nextToken) {
      localStorage.setItem("checkerToken", nextToken);
      setToken(nextToken);
      setLoginError("");
      return;
    }
    setLoginError(DISCORD_ERROR_MESSAGES[discordError] || "Discord login failed. Please try again.");
  }, []);

  function logout() {
    localStorage.removeItem("checkerToken");
    setToken("");
  }
  return token ? <Dashboard token={token} onLogout={logout} /> : <Login loginError={loginError} />;
}

try {
  createRoot(document.getElementById("root")).render(<App />);
} catch (error) {
  document.body.innerHTML = `<main class="login-shell"><section class="login-panel"><h1>Dashboard Error</h1><p class="error">${error.message}</p></section></main>`;
}
