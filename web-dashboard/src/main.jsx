import React, { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import "./desk.css";
import { formatDisplayDate, normalizeIsoDateString } from "./dateFormat.js";
import { sanitizeEventTimestamp } from "./activityTime.js";
import { privacyPath, privacyAccountLabel, redactProfilePrefix, publicFindingLabels } from "./resultPrivacy.js";
import { AdminPanel } from "./AdminPanel.jsx";
import { defenderHasActionableSignal, defenderSummary } from "./defenderSignals.js";
import { exportReportPdf } from "./exportReportPdf.js";
import { SessionReview } from "./SessionReview.jsx";
import { SimpleResults } from "./SimpleResults.jsx";
import { TutorialGuide } from "./TutorialGuide.jsx";
import { AppRouter } from "./App.jsx";
import { API_URL, BRAND_FULL, BRAND_LOGO, DISCORD_INVITE_URL } from "./config/brand.js";
import { authHeaders, DISCORD_ERROR_MESSAGES, startDiscordLogin } from "./lib/auth.js";
import { consumeAuthCallback } from "./lib/authCallback.js";
import { MaterialIcon, renderIcon } from "./components/MaterialIcon.jsx";
import { ConfirmModal } from "./components/ConfirmModal.jsx";
import { EXPERT_NAV_GROUPS } from "./dashboardNav.js";
import { reviewerSafeText, sortBySuspicion } from "./reviewerCopy.js";

const AUTH_CALLBACK = consumeAuthCallback();

const BRAND_NAME = BRAND_FULL;

function formatSessionStatus(status) {
  if (status === "expired") return "expired";
  if (status === "pending") return "pending";
  if (status === "completed") return "completed";
  return status || "unknown";
}

function CaseRail({ sessions, selectedId, flashPinId, onSelect, onDelete, onNewPin }) {
  return (
    <aside className="ws-case-rail" aria-label="Case files">
      <div className="ws-case-rail__head">
        <h2 className="ws-case-rail__title">Cases</h2>
        <button type="button" className="ws-case-rail__new btn btn--primary btn--sm" onClick={onNewPin} title="New case">
          <MaterialIcon name="add" size={14} />
        </button>
      </div>
      <div className="ws-case-rail__list" role="tablist">
        {sessions.length === 0 ? (
          <p className="ws-case-rail__empty">Create a PIN to start your first scan.</p>
        ) : (
          sessions.map((session) => {
            const active = selectedId === session.id;
            const status = formatSessionStatus(session.status);
            return (
              <div
                key={session.id}
                className={`ws-case-item ${active ? "ws-case-item--active" : ""} ${flashPinId === session.id ? "ws-case-item--flash" : ""}`}
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={active}
                  className="ws-case-item__open"
                  onClick={() => onSelect(session.id)}
                >
                  <span className={`ws-case-item__bar ws-case-item__bar--${status}`} />
                  <span className="ws-case-item__body">
                    <span className="ws-case-item__pin">{session.pin}</span>
                    <span className="ws-case-item__status">{status}</span>
                  </span>
                </button>
                <button
                  type="button"
                  className="ws-case-item__del"
                  aria-label={`Delete case ${session.pin}`}
                  onClick={() => onDelete(session)}
                >
                  <MaterialIcon name="close" size={14} />
                </button>
              </div>
            );
          })
        )}
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

function dateMs(value) {
  if (!value) return null;
  const ms = new Date(normalizeIsoDateString(value)).getTime();
  return Number.isNaN(ms) ? null : ms;
}

function formatGmtPlus3(value) {
  return formatDisplayDate(value);
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
  const safeModified = sanitizeEventTimestamp(report, modified, "file_mtime");
  const safeAccessed = sanitizeEventTimestamp(report, accessed, "file_atime");
  if (!safeModified && !safeAccessed) {
    return {
      displayAt: null,
      accessedAt: null,
      modifiedAt: null,
      source: "timestamps unavailable",
      filteredScanAccess: Boolean(modified || accessed),
    };
  }
  return {
    displayAt: safeModified ?? safeAccessed,
    accessedAt: safeAccessed,
    modifiedAt: safeModified,
    source: safeModified ? "mtime" : "atime",
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
      if (source === "browser_history_domain") {
        return sum + 2 * recencyFactor(item.display_at ?? item.modified, report);
      }
      if (source === "browser_download") {
        return sum + 5 * recencyFactor(item.display_at ?? item.modified, report);
      }
      const clientConfidence = Number(item.confidence);
      const confidenceBoost = Number.isFinite(clientConfidence) ? 0.65 + clientConfidence * 0.55 : 1;
      const sourceBoost =
        source === "prefetch_execution" || source === "bam_execution" || source === "dam_execution" ? 1.25 : 1;
      const base = deleted ? 18 : 14;
      return sum + base * sourceBoost * confidenceBoost * recencyFactor(item.display_at ?? item.modified, report);
    }, 0);
    let points = Math.min(65, Math.round(weighted));
    const detectedExecutors = Object.keys(sec.executor_artifact_evidence?.by_executor ?? {});
    if (detectedExecutors.length > 0) {
      points = Math.max(points, Math.min(62, 38 + detectedExecutors.length * 10));
    }
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
  if (defenderHasActionableSignal(sec.defender)) {
    const view = defenderSummary(sec.defender);
    const points = view.quarantineCount > 0 ? 12 : view.userExclusions.length ? 6 : 8;
    score += points;
    reasons.push({
      label: "Defender signal",
      points,
      detail:
        view.quarantineCount > 0
          ? `${view.quarantineCount} quarantine/threat detection(s) and ${view.threatCount} Defender threat record(s).`
          : view.userExclusions.length
            ? `Defender has ${view.userExclusions.length} exclusion(s) under user profile folders or real-time protection is off.`
            : "Windows Defender settings or threat history looked unusual.",
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

  const evidenceVerdict = sec.evidence_verdict;
  if (evidenceVerdict?.available) {
    const clientScore = Number(evidenceVerdict.score) || 0;
    score = clientScore;
    reasons.unshift({
      label: "Unified evidence verdict",
      points: clientScore,
      detail: [
        `Verdict: ${evidenceVerdict.verdict ?? "unknown"}.`,
        evidenceVerdict.high_confidence_hit_count != null
          ? `${evidenceVerdict.high_confidence_hit_count} high-confidence artifact hit(s).`
          : null,
        evidenceVerdict.runtime_signal_count
          ? `${evidenceVerdict.runtime_signal_count} Roblox runtime provenance signal(s).`
          : null,
        evidenceVerdict.scan_complete === false ? "Scan ended incomplete. Treat as inconclusive." : null,
        ...(evidenceVerdict.runtime_reasons ?? []),
      ]
        .filter(Boolean)
        .join(" "),
    });
  }

  return {
    score: Math.min(100, score),
    reasons,
    openedFiles,
    scanAccessFiltered,
    evidenceVerdict: evidenceVerdict?.available ? evidenceVerdict : null,
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

function Card({ icon, title, children }) {
  return (
    <section className="ws-module">
      <header className="ws-module__head">
        {icon ? <span className="ws-module__glyph">{renderIcon(icon, 16)}</span> : null}
        <h3>{title}</h3>
      </header>
      <div className="ws-module__body">{children}</div>
    </section>
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
    if (pfStem === stem && (row.last_run_utc || row.modified)) {
      add("prefetch_last_run", row.last_run_utc || row.modified);
    }
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
    "prefetch_last_run",
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

function sanitizeTimelineEvents(report, events) {
  return (events ?? []).map((event) => {
    const source = event.timestamp_source || event.kind || event.category;
    const safeAt = sanitizeEventTimestamp(report, event.occurred_at, source);
    if (!safeAt) {
      return { ...event, occurred_at: null, time_unknown: true };
    }
    return { ...event, occurred_at: safeAt };
  });
}

function userActivityFromReport(report) {
  const bundled = report.security_integrity_signals?.user_activity_timeline;
  if (bundled?.available) {
    const events = sanitizeTimelineEvents(report, bundled.events);
    const withTs = events.filter((e) => e.occurred_at);
    const byCategory = events.reduce((acc, e) => {
      const cat = e.category || "other";
      acc[cat] = (acc[cat] || 0) + 1;
      return acc;
    }, {});
    return {
      ...bundled,
      events,
      event_count: events.length,
      timestamped_event_count: withTs.length,
      missing_timestamp_count: events.length - withTs.length,
      by_category: byCategory,
    };
  }
  return buildClientSideUserActivity(report);
}

function buildClientSideUserActivity(report) {
  const sec = report.security_integrity_signals ?? {};
  const trash = report.performance_environment?.trash ?? {};
  const events = [];
  for (const item of trash.items ?? []) {
    const path = item.original_path || item.name || item.location || "";
    const rawAt = item.display_at || item.deleted_at || item.modified || null;
    const tsSource = item.timestamp_source || (item.deleted_at ? "recycle_metadata" : "file_mtime");
    const occurredAt = sanitizeEventTimestamp(report, rawAt, tsSource);
    events.push({
      category: "deletions",
      kind: item.original_path ? "recycle_bin" : "recycle_bin_artifact",
      label: item.original_path ? "Deleted to Recycle Bin" : "Recycle Bin item",
      path,
      occurred_at: occurredAt,
      time_unknown: Boolean(rawAt && !occurredAt),
      timestamp_source: tsSource,
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
  const sorted = sortBySuspicion(filtered);

  return (
    <>
      <Card icon="history" title="Activity timeline">
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
        {sorted.length ? (
          <div className="executor-event-list activity-event-list">
            {sorted.slice(0, 80).map((event, index) => (
              <div className="executor-event-row activity-event-row" key={`${event.path}-${event.kind}-${index}`}>
                <div>
                  <span className={`recency-pill ${event.recency ?? "unknown"}`}>
                    {(event.recency ?? "unknown").replace(/_/g, " ")}
                  </span>
                  <span className="activity-category-pill">{ACTIVITY_CATEGORY_LABELS[event.category] ?? event.category}</span>
                  <p className="plain-summary">{activityEventSummary(event)}</p>
                  {event.path ? <p className="executor-event-path">{event.path}</p> : null}
                </div>
                <div className="activity-time-col">
                  <time>{event.occurred_at ? formatGmtPlus3(event.occurred_at) : "—"}</time>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No events match this filter.</p>
        )}
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
    <Card icon="document_search" title="Executor activity (recent first)">
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
      <Card icon="speed" title="Suspicion Score">
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
      <Card icon="warning" title="Why It Scored This Way">
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
      <Card icon="schedule" title="Tracked files (modified + OS access, MM/DD/YY)">
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

function robloxHeadshotUrl(account) {
  if (account.headshot_url) return account.headshot_url;
  if (!account.user_id) return null;
  return `https://www.roblox.com/headshot-thumbnail/image?userId=${encodeURIComponent(account.user_id)}&width=150&height=150&format=png`;
}

function collectRobloxAccounts(roblox) {
  const byId = new Map();

  const mergeAccount = (account, sourceLabel) => {
    const userId = account?.user_id ? String(account.user_id) : "";
    if (!userId) return;
    const existing = byId.get(userId) ?? {
      user_id: userId,
      username: null,
      headshot_url: null,
      sources: [],
      authenticated: false,
    };
    if (account.username) existing.username = account.username;
    if (account.headshot_url) existing.headshot_url = account.headshot_url;
    if (account.authenticated) existing.authenticated = true;
    const sources = account.sources?.length ? account.sources : sourceLabel ? [sourceLabel] : [];
    if (sources.length) {
      existing.sources = [...new Set([...existing.sources, ...sources])];
    }
    byId.set(userId, existing);
  };

  for (const account of roblox.accounts ?? []) {
    mergeAccount(account);
  }

  for (const userId of roblox.aggregate_user_ids ?? []) {
    mergeAccount({ user_id: String(userId), sources: ["Scan summary"] });
  }

  for (const artifact of roblox.browser_scan?.artifacts ?? []) {
    for (const userId of artifact.user_ids ?? []) {
      mergeAccount(
        {
          user_id: String(userId),
          username: artifact.session_username,
          authenticated: Boolean(artifact.authenticated),
          sources: artifact.sources,
        },
        `Browser: ${artifact.browser ?? "unknown"}`,
      );
    }
    if (artifact.session_user_id) {
      mergeAccount({
        user_id: String(artifact.session_user_id),
        username: artifact.session_username,
        authenticated: Boolean(artifact.authenticated),
        sources: artifact.sources,
      });
    }
  }

  return [...byId.values()].sort((left, right) => {
    const leftId = Number(left.user_id);
    const rightId = Number(right.user_id);
    if (Number.isFinite(leftId) && Number.isFinite(rightId)) return leftId - rightId;
    return String(left.user_id).localeCompare(String(right.user_id));
  });
}

function robloxDisplayName(account) {
  if (account.username) return account.username;
  return privacyAccountLabel(account);
}

function RobloxAccountsCard({ report, token }) {
  const roblox = report.application_diagnostics?.roblox ?? {};
  const baseAccounts = useMemo(() => collectRobloxAccounts(roblox), [roblox]);
  const [profiles, setProfiles] = useState({});

  useEffect(() => {
    const userIds = baseAccounts.map((account) => account.user_id);
    if (!token || !userIds.length) {
      setProfiles({});
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`${API_URL}/roblox/profiles`, {
          method: "POST",
          headers: authHeaders(token),
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
  }, [baseAccounts, token]);

  const accounts = useMemo(
    () =>
      baseAccounts.map((account) => {
        const resolved = profiles[account.user_id] ?? {};
        return {
          ...account,
          username: account.username || resolved.username || null,
          headshot_url: account.headshot_url || resolved.headshot_url || null,
        };
      }),
    [baseAccounts, profiles],
  );

  return (
    <Card icon="sports_esports" title="Roblox accounts">
      {accounts.length === 0 ? (
        <p className="ws-empty-note">No Roblox accounts were found on this device.</p>
      ) : (
        <div className="ws-account-grid">
          {accounts.slice(0, 24).map((account) => {
            const displayName = robloxDisplayName(account);
            const profileUrl = `https://www.roblox.com/users/${encodeURIComponent(account.user_id)}/profile`;
            const avatar = robloxHeadshotUrl(account);
            return (
              <a
                key={account.user_id}
                href={profileUrl}
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
                  <span className="ws-account-card__link">roblox.com/users/{account.user_id}</span>
                </span>
              </a>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function discordAvatarUrl(account) {
  const userId = String(account.user_id || "");
  if (!userId) return null;
  const hash = account.avatar_hash;
  if (hash) {
    return `https://cdn.discordapp.com/avatars/${userId}/${hash}.png?size=128`;
  }
  const avatarIndex = (BigInt(userId) >> 22n) % 6n;
  return `https://cdn.discordapp.com/embed/avatars/${avatarIndex}.png`;
}

function DiscordAccountsCard({ report }) {
  const accounts = report.application_diagnostics?.discord?.accounts ?? [];

  return (
    <Card icon="forum" title="Discord accounts">
      {accounts.length === 0 ? (
        <p className="ws-empty-note">No Discord accounts found.</p>
      ) : (
        <div className="ws-account-grid">
          {accounts.slice(0, 24).map((account) => {
            const userId = String(account.user_id || "");
            const displayName = account.display_name || `User ${userId}`;
            const avatar = account.avatar_url || discordAvatarUrl(account);
            return (
              <div key={userId} className="ws-account-card" style={{ cursor: "default" }}>
                {avatar ? (
                  <img src={avatar} alt="" className="ws-account-card__avatar" loading="lazy" />
                ) : (
                  <span className="ws-account-card__avatar" aria-hidden />
                )}
                <span className="ws-account-card__body">
                  <span className="ws-account-card__name">{displayName}</span>
                  <span className="ws-account-card__link">ID {userId}</span>
                </span>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function AccountsSection({ report, token }) {
  return (
    <>
      <RobloxAccountsCard report={report} token={token} />
      <DiscordAccountsCard report={report} />
    </>
  );
}

function RobloxSection({ report, query, token }) {
  return <AccountsSection report={report} token={token} />;
}

function SecuritySection({ report, query }) {
  const sec = report.security_integrity_signals ?? {};
  const defenderView = defenderSummary(sec.defender);
  const securityEvents = sec.windows_security_events?.events ?? [];
  const psEvents = sec.powershell_operational_events?.events ?? [];
  const serviceEvents = sec.windows_service_change_events?.events ?? [];
  const q = query.trim().toLowerCase();

  function eventMatches(item) {
    if (!q) return true;
    return [item.Message, item.Id, item.ProviderName, item.ThreatName, item.ProcessName]
      .join(" ")
      .toLowerCase()
      .includes(q);
  }

  return (
    <>
      <Card icon="shield" title="Windows Defender status">
        {defenderView.available ? (
          <>
            <div className={`verdict-pill verdict-pill--${defenderView.tone}`}>{defenderView.statusLabel}</div>
            <div className="security-kv-grid">
              <div>
                <span className="muted">Real-time protection</span>
                <strong>{defenderView.realtimeEnabled ? "On" : "Off"}</strong>
              </div>
              <div>
                <span className="muted">Tamper protection</span>
                <strong>{defenderView.tamperProtected === false ? "Off" : defenderView.tamperProtected ? "On" : "Unknown"}</strong>
              </div>
              <div>
                <span className="muted">Threat records</span>
                <strong>{defenderView.threatCount}</strong>
              </div>
              <div>
                <span className="muted">Quarantine signals</span>
                <strong>{defenderView.quarantineCount}</strong>
              </div>
            </div>
            {defenderView.userExclusions.length ? (
              <p className="muted panel-intro">
                User-profile exclusions: {defenderView.userExclusions.slice(0, 4).join("; ")}
              </p>
            ) : null}
          </>
        ) : (
          <p className="muted">{defenderView.detail}</p>
        )}
      </Card>
      <Card icon="shield" title="Quarantine & threat history">
        {(defenderView.quarantine ?? []).filter(eventMatches).length ? (
          <div className="evidence-list">
            {defenderView.quarantine.filter(eventMatches).slice(0, 30).map((item, index) => (
              <div className="evidence-row evidence-row--static" key={`q-${index}`}>
                <div className="evidence-row-main">
                  <strong className="evidence-row-title">{item.ThreatName || "Threat"}</strong>
                  <p className="evidence-row-path">{item.ProcessName || (item.Resources ?? []).join?.(", ") || "—"}</p>
                </div>
                <time className="evidence-row-time">
                  {item.DetectionTime || item.InitialDetectionTime || "—"}
                </time>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No quarantine or threat-detection rows in this scan.</p>
        )}
        <details className="raw-fold">
          <summary>View raw Defender JSON</summary>
          <TerminalBlock query={query}>{asJson(sec.defender)}</TerminalBlock>
        </details>
      </Card>
      <Card icon="terminal" title="Security event log (14 days)">
        {securityEvents.filter(eventMatches).length ? (
          <div className="evidence-list">
            {securityEvents.filter(eventMatches).slice(0, 25).map((item, index) => (
              <div className="evidence-row evidence-row--static" key={`sec-${index}`}>
                <div className="evidence-row-main">
                  <strong className="evidence-row-title">Event {item.Id}</strong>
                  <p className="evidence-row-path">{(item.Message || "").slice(0, 280)}</p>
                </div>
                <time className="evidence-row-time">{item.TimeCreated || "—"}</time>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No tracked Security log events (log may be disabled or empty).</p>
        )}
      </Card>
      <Card icon="terminal" title="PowerShell operational log">
        {psEvents.filter(eventMatches).length ? (
          <div className="evidence-list">
            {psEvents.filter(eventMatches).slice(0, 20).map((item, index) => (
              <div className="evidence-row evidence-row--static" key={`ps-${index}`}>
                <div className="evidence-row-main">
                  <strong className="evidence-row-title">Event {item.Id}</strong>
                  <p className="evidence-row-path">{(item.Message || "").slice(0, 280)}</p>
                </div>
                <time className="evidence-row-time">{item.TimeCreated || "—"}</time>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No PowerShell operational events in the last 14 days.</p>
        )}
      </Card>
      <Card icon="memory" title="Service install & state changes">
        {serviceEvents.filter(eventMatches).length ? (
          <div className="evidence-list">
            {serviceEvents.filter(eventMatches).slice(0, 25).map((item, index) => (
              <div className="evidence-row evidence-row--static" key={`svc-${index}`}>
                <div className="evidence-row-main">
                  <strong className="evidence-row-title">Event {item.Id}</strong>
                  <p className="evidence-row-path">{(item.Message || "").slice(0, 280)}</p>
                </div>
                <time className="evidence-row-time">{item.TimeCreated || "—"}</time>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No service install/state change events captured.</p>
        )}
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
      <Card icon="memory" title="System Overview">
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
      <Card icon="memory" title="Services">
        <TerminalBlock query={query}>{sec.services?.raw}</TerminalBlock>
      </Card>
      <Card icon="delete" title="Recycle Bin">
        <TerminalBlock query={query}>{asJson(perf.trash)}</TerminalBlock>
      </Card>
      <Card icon="terminal" title="Shell History">
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
                    <strong className="evidence-row-title">
                      {publicFindingLabels(hit.matched ?? []).join(", ") || "Suspicious activity"}
                    </strong>
                    <p className="evidence-row-path">{redactProfilePrefix(hit.line)}</p>
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
  const bypass = sec.bypass_resilience ?? {};
  const findings = bypass.findings ?? [];
  const logHits = sec.roblox_executor_indicators?.traceback_or_log_hits ?? [];
  const q = query.trim().toLowerCase();

  const filteredFindings = findings.filter((row) => {
    if (!q) return true;
    return [row.title, row.detail, row.severity].join(" ").toLowerCase().includes(q);
  });

  const severityRank = { critical: 0, high: 1, medium: 2, low: 3 };
  const sortedFindings = [...filteredFindings].sort(
    (a, b) => (severityRank[a.severity] ?? 9) - (severityRank[b.severity] ?? 9),
  );

  const filteredLogHits = logHits.filter((hit) => {
    if (!q) return true;
    return JSON.stringify(hit).toLowerCase().includes(q);
  });

  return (
    <>
      <Card icon="shield" title="Cover-up signs">
        {sortedFindings.length ? (
          <div className="evidence-list">
            {sortedFindings.map((row, index) => (
              <div
                className={`evidence-row evidence-row--static ws-finding ws-finding--${row.severity || "medium"}`}
                key={`${row.title}-${index}`}
              >
                <div className="evidence-row-main">
                  <strong className="evidence-row-title">{row.title}</strong>
                  <p className="evidence-row-path">{row.detail}</p>
                </div>
                <span className={`ws-tag ws-tag--${row.severity === "high" || row.severity === "critical" ? "bad" : "warn"}`}>
                  {row.severity || "medium"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No cover-up or anti-forensics signals were flagged on this scan.</p>
        )}
        {bypass.risk_score != null ? (
          <p className="muted panel-intro">Cover-up risk score: {bypass.risk_score}/100</p>
        ) : null}
      </Card>
      {filteredLogHits.length ? (
        <Card icon="search" title="Keyword matches in logs">
          <div className="evidence-list">
            {filteredLogHits.slice(0, 20).map((hit, index) => (
              <div className="evidence-row evidence-row--static" key={`log-hit-${index}`}>
                <div className="evidence-row-main">
                  <strong className="evidence-row-title">{privacyPath(hit.path || hit.file || "Log file")}</strong>
                  <p className="evidence-row-path">
                    {(hit.matched_lines ?? hit.matches ?? []).slice(0, 2).map((line) => redactProfilePrefix(String(line))).join(" · ") ||
                      "Suspicious text pattern"}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </>
  );
}

function RegistrySection({ report, query }) {
  const sec = report.security_integrity_signals ?? {};
  const review = report.scan_review ?? {};
  const execution = review.execution_activity ?? {};
  const items = execution.items ?? [];
  const bamItems = (sec.bam?.items ?? sec.bam_structured?.items ?? []).filter(
    (row) => row.last_execution_utc || row.normalized_path,
  );
  const q = query.trim().toLowerCase();

  const shownExecution = items
    .filter((row) => {
      if (!q) return true;
      return [row.name, row.path, row.summary].join(" ").toLowerCase().includes(q);
    })
    .sort((a, b) => {
      if (a.suspicious !== b.suspicious) return a.suspicious ? -1 : 1;
      const aMs = a.occurred_at ? new Date(a.occurred_at).getTime() : 0;
      const bMs = b.occurred_at ? new Date(b.occurred_at).getTime() : 0;
      return bMs - aMs;
    });

  const shownBam = bamItems
    .filter((row) => {
      if (!q) return true;
      return [row.normalized_path, ...(row.executor_name_hits ?? [])].join(" ").toLowerCase().includes(q);
    })
    .filter((row) => (row.executor_name_hits ?? []).length || row.cheat_filename_hints?.length)
    .slice(0, 30);

  return (
    <>
      <Card icon="play_arrow" title="Execution activity">
        {shownExecution.length ? (
          <div className="evidence-list">
            {shownExecution.slice(0, 35).map((row, index) => (
              <div
                className={`evidence-row evidence-row--static ${row.suspicious ? "ws-finding--high" : ""}`}
                key={`exec-${row.path}-${index}`}
              >
                <div className="evidence-row-main">
                  <strong className="evidence-row-title">{row.name || row.file_name || "Program"}</strong>
                  <p className="evidence-row-path">{row.summary || privacyPath(row.path)}</p>
                </div>
                <time className="evidence-row-time">
                  {row.occurred_at ? formatGmtPlus3(row.occurred_at) : "Time unknown"}
                </time>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No execution traces were aggregated for this scan.</p>
        )}
      </Card>
      {shownBam.length ? (
        <Card icon="memory" title="Administrator activity log (BAM)">
          <p className="muted panel-intro">Programs recorded by Windows Background Activity Moderator — event time when available.</p>
          <div className="evidence-list">
            {shownBam.map((row, index) => (
              <div className="evidence-row evidence-row--static" key={`bam-${row.normalized_path}-${index}`}>
                <div className="evidence-row-main">
                  <strong className="evidence-row-title">
                    {(row.executor_name_hits ?? row.cheat_filename_hints ?? ["Program"]).join(", ")}
                  </strong>
                  <p className="evidence-row-path">{privacyPath(row.normalized_path || row.registry_path_value)}</p>
                </div>
                <time className="evidence-row-time">
                  {row.last_execution_utc ? formatGmtPlus3(row.last_execution_utc) : "Time unknown"}
                </time>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </>
  );
}

function FileAnalysisSection({ report, query }) {
  const sec = report.security_integrity_signals ?? {};
  const fileHits = sec.roblox_executor_indicators?.file_hits ?? [];
  const prefetchHits = sec.prefetch_health?.indicator_hits ?? [];
  const designated = sec.designated_folder_suspicious_files?.hits ?? [];
  const q = query.trim().toLowerCase();

  const rows = [...fileHits, ...prefetchHits, ...designated]
    .filter((row) => {
      if (!q) return true;
      return [row.path, row.name, ...(row.executor_name_hits ?? []), ...(row.matched_indicator_names ?? [])]
        .join(" ")
        .toLowerCase()
        .includes(q);
    })
    .sort((a, b) => {
      const aSusp = (a.executor_name_hits ?? a.matched_indicator_names ?? []).length ? 1 : 0;
      const bSusp = (b.executor_name_hits ?? b.matched_indicator_names ?? []).length ? 1 : 0;
      if (aSusp !== bSusp) return bSusp - aSusp;
      const aMs = new Date(a.modified || a.last_run || 0).getTime();
      const bMs = new Date(b.modified || b.last_run || 0).getTime();
      return bMs - aMs;
    });

  return (
    <Card icon="document_search" title="File traces">
      {rows.length ? (
        <div className="evidence-list">
          {rows.slice(0, 40).map((row, index) => (
            <div className="evidence-row evidence-row--static" key={`file-${row.path || row.name}-${index}`}>
              <div className="evidence-row-main">
                <strong className="evidence-row-title">
                  {(row.executor_name_hits ?? row.matched_indicator_names ?? ["File match"]).slice(0, 2).join(", ")}
                </strong>
                <p className="evidence-row-path">{privacyPath(row.path || row.name)}</p>
              </div>
              <time className="evidence-row-time">
                {row.modified || row.last_run ? formatGmtPlus3(row.modified || row.last_run) : "Time unknown"}
              </time>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">No flagged file traces on this scan.</p>
      )}
    </Card>
  );
}

function SuspiciousFilesSection({ report, query }) {
  const sec = report.security_integrity_signals ?? {};
  const recent = (sec.recent_items?.items ?? []).filter((item) => item.matched_indicator_names?.length);
  const q = query.trim().toLowerCase();
  const rows = recent.filter((row) => {
    if (!q) return true;
    return [row.path, ...(row.matched_indicator_names ?? [])].join(" ").toLowerCase().includes(q);
  });

  return (
    <Card icon="folder_off" title="Flagged files">
      {rows.length ? (
        <div className="evidence-list">
          {rows.slice(0, 40).map((row, index) => (
            <div className="evidence-row evidence-row--static" key={`recent-${row.path}-${index}`}>
              <div className="evidence-row-main">
                <strong className="evidence-row-title">{(row.matched_indicator_names ?? []).join(", ")}</strong>
                <p className="evidence-row-path">{privacyPath(row.path)}</p>
              </div>
              <time className="evidence-row-time">
                {row.modified ? formatGmtPlus3(row.modified) : "Time unknown"}
              </time>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">No recently touched files matched our watch lists.</p>
      )}
    </Card>
  );
}

function CrashLogsSection({ report, query }) {
  const hits = report.security_integrity_signals?.roblox_executor_indicators?.traceback_or_log_hits ?? [];
  return (
    <Card icon="terminal" title="Crash Logs">
      <TerminalBlock query={query}>{hits.length ? asJson(hits) : "No crash logs detected."}</TerminalBlock>
    </Card>
  );
}

const CLEANUP_TYPE_LABELS = {
  still_in_recycle_bin: "Still in Recycle Bin",
  recycle_bin_emptied: "Recycle Bin emptied",
  permanent_recycle_removal: "Permanent Recycle Bin removal",
  removed_without_logged_empty: "Removed without logged emptying",
  awaiting_cleanup: "Awaiting cleanup",
};

function DeletionsSection({ report, query }) {
  const sec = report.security_integrity_signals ?? {};
  const trash = report.performance_environment?.trash ?? {};
  const activity = userActivityFromReport(report);
  const cleanup = sec.deletion_cleanup_analysis ?? {};
  const deletionEvents = sortBySuspicion((activity.events ?? []).filter((e) => e.category === "deletions"));
  const cleanupRows = cleanup.correlations ?? [];
  const trashItems = (trash.items ?? []).filter((item) => item.original_path || item.name?.startsWith?.("$I"));

  return (
    <>
      <Card icon="schedule" title="Delete-to-cleanup timing">
        {(cleanupRows.length ? cleanupRows : deletionEvents).length ? (
          <div className="executor-event-list">
            {(cleanupRows.length ? cleanupRows : deletionEvents).slice(0, 40).map((row, index) => (
              <div className="executor-event-row" key={`cleanup-${row.path}-${index}`}>
                <div>
                  <span className={`recency-pill ${row.cleanup_type ?? row.recency ?? "unknown"}`}>
                    {CLEANUP_TYPE_LABELS[row.cleanup_type] ??
                      (row.recency ?? "unknown").replace?.(/_/g, " ") ??
                      "Deletion"}
                  </span>
                  <p className="plain-summary">{row.summary || activityEventSummary(row)}</p>
                  <p className="executor-event-path">{row.path}</p>
                  {row.gap_human ? (
                    <small className="muted">
                      Time between delete and cleanup: <strong>{row.gap_human}</strong>
                      {row.cleanup_at_display || row.cleanup_at
                        ? ` · cleanup logged ${row.cleanup_at_display || formatGmtPlus3(row.cleanup_at)}`
                        : ""}
                    </small>
                  ) : null}
                  {row.timestamp_source ? (
                    <small className="timestamp-source">
                      Time reference: {formatTimestampSourceWithHint(row.timestamp_source, row)}
                    </small>
                  ) : null}
                </div>
                <time>{row.deleted_at_display || (row.occurred_at ? formatGmtPlus3(row.occurred_at) : "No timestamp")}</time>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No delete-to-cleanup timing could be calculated for this scan.</p>
        )}
        {(cleanup.insights ?? [])
          .map((line) => reviewerSafeText(line))
          .filter(Boolean).length ? (
          <ul className="simple-tips">
            {cleanup.insights
              .map((line) => reviewerSafeText(line))
              .filter(Boolean)
              .map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        ) : null}
      </Card>

      <Card icon="delete" title="Deleted files">
        {deletionEvents.length ? (
          <div className="executor-event-list">
            {deletionEvents.slice(0, 40).map((event, index) => (
              <div className="executor-event-row" key={`del-${event.path}-${index}`}>
                <div>
                  <span className={`recency-pill ${event.recency ?? "unknown"}`}>
                    {(event.recency ?? "unknown").replace(/_/g, " ")}
                  </span>
                  <p className="plain-summary">{event.summary || activityEventSummary(event)}</p>
                  <p className="executor-event-path">{event.path}</p>
                  {event.gap_human ? (
                    <small className="muted">
                      Recycle Bin cleanup followed <strong>{event.gap_human}</strong> later.
                    </small>
                  ) : null}
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
                  <strong>{basenameOf(item.original_path || item.name) || "Deleted item"}</strong>
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
      <Card icon="delete" title="Deletion evidence">
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
      <Card icon="sd_card" title="Roblox integrity (live + offline)">
        <TerminalBlock query={query}>
          {runtime.available === false
            ? runtime.reason ?? "Roblox integrity scan not available on this host."
            : runtime.suspicious_modules?.length
              ? asJson(runtime)
              : "[OK] No suspicious Roblox integrity signals were found in available artifacts."}
        </TerminalBlock>
      </Card>
      <Card icon="sd_card" title="Persistence signals">
        <TerminalBlock query={query}>
          {persistence.available === false
            ? persistence.reason ?? "Persistence scan not available."
            : asJson(persistence)}
        </TerminalBlock>
      </Card>
      <Card icon="sd_card" title="Known binary fingerprint matches">
        <TerminalBlock query={query}>{asJson(shaBlocklist)}</TerminalBlock>
      </Card>
      <Card icon="sd_card" title="Process Snapshot">
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
      <Card icon="fingerprint" title="Evidence review">
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
      <Card icon="fingerprint" title="Evidence review">
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
                          ? `Review item for “${basenameOf(d.file_path)}”.`
                          : "Review item with no file path attached."}
                      </p>
                      <p className="evidence-row-path">{privacyPath(d.file_path) || "—"}</p>
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
                      <span>Assessment</span>
                      <strong>Suspicious activity indicator</strong>
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
    <Card icon="inventory_2" title="Compatibility trace programs">
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
                <p className="evidence-row-path">{privacyPath(item.normalized_path || item.raw) || "—"}</p>
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
      <Card icon="account_tree" title="Correlation">
        <p className="muted">No unified correlation data for this report.</p>
      </Card>
    );
  }

  return (
    <>
      <Card icon="account_tree" title="Cross-artifact summary">
        <details className="raw-fold">
          <summary>View summary JSON</summary>
          <TerminalBlock query={query}>{asJson(uc.cross_artifact_summary)}</TerminalBlock>
        </details>
      </Card>
      <Card icon="account_tree" title="Execution chains">
        <details className="raw-fold">
          <summary>View execution chains JSON</summary>
          <TerminalBlock query={query}>{asJson(uc.execution_chains ?? [])}</TerminalBlock>
        </details>
      </Card>
      <Card icon="schedule" title="Cross-source timeline">
        <p className="muted panel-intro">
          Merged Windows traces in plain language (newest first). Each row explains what happened; technical artifact
          names are expanded in the glossary above.
        </p>
        <div className="evidence-list">
          {timelineFiltered.slice(0, 80).map((row, index) => (
            <div className="evidence-row evidence-row--static" key={`tl-${row.artifact}-${index}`}>
              <div className="evidence-row-main">
                <p className="plain-summary">{timelineRowSummary(row)}</p>
                <p className="evidence-row-path">{privacyPath(row.path) || "—"}</p>
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
      <Card icon="inventory_2" title="Artifact detail">
        <p className="muted">No structured forensic artifacts for this report.</p>
      </Card>
    );
  }
  const usnRows = safeArray(fa.usn_file_lifecycle_rows).slice(0, 100);
  return (
    <>
      <Card icon="inventory_2" title="Structured execution traces">
        <details className="raw-fold">
          <summary>View execution trace JSON</summary>
          <TerminalBlock query={query}>{asJson(fa.bam_structured)}</TerminalBlock>
        </details>
      </Card>
      <Card icon="inventory_2" title="Browser SQLite probe">
        <details className="raw-fold">
          <summary>View browser SQLite JSON</summary>
          <TerminalBlock query={query}>{asJson(fa.sqlite)}</TerminalBlock>
        </details>
      </Card>
      <Card icon="inventory_2" title="File lifecycle sample">
        <details className="raw-fold">
          <summary>View lifecycle rows JSON</summary>
          <TerminalBlock query={query}>{asJson(usnRows)}</TerminalBlock>
        </details>
      </Card>
    </>
  );
}

const resultSections = [
  { id: "starter", label: "Scan summary", icon: "speed", component: StarterSection },
  { id: "user-activity", label: "Activity timeline", icon: "history", component: UserActivitySection },
  { id: "accounts", label: "Linked accounts", icon: "person", component: AccountsSection },
  {
    id: "forensic-findings",
    label: "Key findings",
    icon: "fingerprint",
    component: ForensicFindingsSection,
  },
  {
    id: "forensic-corr",
    label: "Cross-source timeline",
    icon: "account_tree",
    component: ForensicCorrelationSection,
  },
  {
    id: "forensic-artifacts",
    label: "OS traces",
    icon: "inventory_2",
    component: ForensicArtifactsSection,
  },
  { id: "roblox", label: "Roblox", icon: "sports_esports", component: RobloxSection },
  { id: "security", label: "Security & AV", icon: "shield", component: SecuritySection },
  { id: "system", label: "System info", icon: "memory", component: SystemSection },
  { id: "bypass", label: "Cover-up signs", icon: "gpp_maybe", component: BypassSection },
  { id: "registry", label: "Execution traces", icon: "database", component: RegistrySection },
  { id: "file-analysis", label: "File traces", icon: "document_search", component: FileAnalysisSection },
  { id: "suspicious", label: "Flagged files", icon: "folder_off", component: SuspiciousFilesSection },
  { id: "crash", label: "Crash logs", icon: "terminal", component: CrashLogsSection },
  { id: "deletions", label: "Deletions", icon: "delete", component: DeletionsSection },
  { id: "memory", label: "Memory", icon: "sd_card", component: MemorySection },
];
const resultSectionById = Object.fromEntries(resultSections.map((section) => [section.id, section]));

function expertGroupForSection(sectionId) {
  return EXPERT_NAV_GROUPS.find((group) => group.sectionIds.includes(sectionId)) ?? EXPERT_NAV_GROUPS[0];
}

function ExpertNavigator({ sectionId, onSectionChange, query, onQueryChange, activeLabel }) {
  const [activeGroupId, setActiveGroupId] = useState(() => expertGroupForSection(sectionId).id);
  const activeGroup = EXPERT_NAV_GROUPS.find((g) => g.id === activeGroupId) ?? EXPERT_NAV_GROUPS[0];

  useEffect(() => {
    const group = expertGroupForSection(sectionId);
    setActiveGroupId(group.id);
  }, [sectionId]);

  function selectGroup(group) {
    setActiveGroupId(group.id);
    if (!group.sectionIds.includes(sectionId)) {
      onSectionChange(group.sectionIds[0]);
    }
  }

  return (
    <div className="ws-workflow">
      <div className="ws-workflow__steps" role="tablist" aria-label="Review workflow">
        {EXPERT_NAV_GROUPS.map((group) => (
          <button
            key={group.id}
            type="button"
            role="tab"
            aria-selected={activeGroupId === group.id}
            className={`ws-workflow__step ${activeGroupId === group.id ? "ws-workflow__step--active" : ""}`}
            onClick={() => selectGroup(group)}
          >
            <span className="ws-workflow__step-num">{group.label.split("·")[0]?.trim()}</span>
            <span className="ws-workflow__step-label">{group.label.split("·").slice(1).join("·").trim() || group.label}</span>
          </button>
        ))}
      </div>
      <div className="ws-workflow__sections">
        {activeGroup.sectionIds.map((id) => {
          const section = resultSectionById[id];
          if (!section) return null;
          return (
            <button
              key={id}
              type="button"
              className={`ws-chip ${sectionId === id ? "ws-chip--active" : ""}`}
              onClick={() => onSectionChange(id)}
            >
              {section.label}
            </button>
          );
        })}
        <input
          className="ws-workflow__search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={`Filter ${activeLabel}…`}
          aria-label="Filter section content"
        />
      </div>
    </div>
  );
}

function WorkspaceInspector({
  detail,
  concernScore,
  expertMode,
  showSectionContent,
  onDownload,
  onPrint,
  onTutorial,
  onToggleMode,
  token,
  onSessionReviewSaved,
}) {
  return (
    <aside className="ws-inspector" aria-label="Case inspector">
      <div className="ws-inspector__block">
        <span className="ws-inspector__eyebrow">Active case</span>
        <div className="ws-inspector__pin">{detail.pin}</div>
        <dl className="ws-inspector__grid">
          <div className="ws-inspector__field">
            <dt>Status</dt>
            <dd>
              <span className={`ws-status-tag ws-status-tag--${formatSessionStatus(detail.status)}`}>
                {formatSessionStatus(detail.status)}
              </span>
            </dd>
          </div>
          {concernScore != null ? (
            <div className="ws-inspector__field">
              <dt>{expertMode ? "Suspicion score" : "Concern level"}</dt>
              <dd>
                <span className="ws-inspector__score">{concernScore}/100</span>
              </dd>
            </div>
          ) : null}
          <div className="ws-inspector__field">
            <dt>Submitted</dt>
            <dd>{detail.completed_at ? formatGmtPlus3(detail.completed_at) : "Awaiting scan"}</dd>
          </div>
        </dl>
        <div className="ws-inspector__actions">
          <button type="button" className="ws-icon-btn" onClick={onDownload} title="Download JSON">
            <MaterialIcon name="download" size={18} />
          </button>
          <button type="button" className="ws-icon-btn" onClick={onPrint} title="Print summary">
            <MaterialIcon name="print" size={18} />
          </button>
          <button type="button" className="ws-icon-btn" onClick={onTutorial} title="Tutorial">
            <MaterialIcon name="menu_book" size={18} />
          </button>
          {showSectionContent ? (
            <button
              type="button"
              className={`ws-inspector__mode ${expertMode ? "ws-inspector__mode--expert" : ""}`}
              onClick={onToggleMode}
            >
              {expertMode ? "← Simple overview" : "Advanced review →"}
            </button>
          ) : null}
        </div>
      </div>
      {showSectionContent ? (
        <div className="ws-inspector__block">
          <SessionReview
            detail={detail}
            apiUrl={API_URL}
            token={token}
            authHeaders={authHeaders}
            onSaved={onSessionReviewSaved}
            variant="inspector"
          />
        </div>
      ) : null}
    </aside>
  );
}

function Results({ detail, token, onSessionReviewSaved }) {
  const [sectionId, setSectionId] = useState("starter");
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [expertMode, setExpertMode] = useState(false);
  const [tutorialOpen, setTutorialOpen] = useState(false);

  useEffect(() => {
    if (!detail?.id) {
      return;
    }
    setSectionId("starter");
    setQuery("");
    setExpertMode(false);
    setTutorialOpen(false);
  }, [detail?.id]); // keep tutorialOpen reset on session change

  const report = detail?.report ?? {};
  // Large reports can make tab switches feel sluggish if recomputed on every render.
  const summary = useMemo(() => buildSuspicionSummary(report), [report]);
  const activity = useMemo(() => userActivityFromReport(report), [report]);
  const activeSection = resultSectionById[sectionId] ?? resultSections[0];
  const ActiveComponent = activeSection.component;
  if (!detail) {
    return (
      <div className="ws-main-area">
        <div className="ws-empty">
          <MaterialIcon name="description" size={36} />
          <h2>Select a case to begin</h2>
          <p>Choose a PIN from the case rail, or create a new one to start a scan.</p>
        </div>
      </div>
    );
  }
  const showSectionContent = detail.status === "completed";
  const concernScore =
    detail.status === "completed"
      ? expertMode
        ? summary.score
        : Math.min(
            100,
            summary.evidenceVerdict?.score ??
              Math.round(
                summary.score * 0.75 +
                  ((report.security_integrity_signals?.bypass_resilience?.risk_score ?? 0) * 0.35),
              ),
          )
      : null;

  return (
    <div className="ws-split">
      <div className="ws-canvas">
        {expertMode && showSectionContent ? (
          <ExpertNavigator
            sectionId={sectionId}
            onSectionChange={setSectionId}
            query={query}
            onQueryChange={setQuery}
            activeLabel={activeSection.label}
          />
        ) : null}
        <div className="ws-canvas__body">
          {!showSectionContent ? (
            <div className="ws-canvas__waiting">
              <MaterialIcon name="hourglass_top" size={24} />
              <p>Waiting for the desktop scanner to submit results for this case.</p>
            </div>
          ) : expertMode ? (
            <ActiveComponent report={report} query={deferredQuery} token={token} />
          ) : (
            <SimpleResults
              report={report}
              summary={summary}
              activity={activity}
              activityEventSummary={activityEventSummary}
              formatGmtPlus3={formatGmtPlus3}
              token={token}
              onExpertMode={() => setExpertMode(true)}
              onDownload={() => downloadReport(detail)}
              onPrintPdf={() => exportReportPdf({ detail, report, summary, brandName: BRAND_NAME })}
            />
          )}
        </div>
      </div>
      <WorkspaceInspector
        detail={detail}
        concernScore={concernScore}
        expertMode={expertMode}
        showSectionContent={showSectionContent}
        onDownload={() => downloadReport(detail)}
        onPrint={() => exportReportPdf({ detail, report, summary, brandName: BRAND_NAME })}
        onTutorial={() => setTutorialOpen(true)}
        onToggleMode={() => setExpertMode((value) => !value)}
        token={token}
        onSessionReviewSaved={onSessionReviewSaved}
      />
      <TutorialGuide open={tutorialOpen} onClose={() => setTutorialOpen(false)} brandName={BRAND_NAME} />
    </div>
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

export function Dashboard({ token, onLogout }) {
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [verifyBusy, setVerifyBusy] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [flashPinId, setFlashPinId] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const detailFetchSeq = useRef(0);

  const hasAccess = Boolean(profile?.has_access);
  const isSuperAdmin = Boolean(profile?.is_super_admin);
  const [showAdmin, setShowAdmin] = useState(false);

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

  function requestDeleteSession(session) {
    if (!hasAccess) return;
    setDeleteTarget(session);
  }

  async function confirmDeleteSession() {
    if (!deleteTarget || !hasAccess) return;
    setDeleteBusy(true);
    try {
      const response = await fetch(`${API_URL}/sessions/${deleteTarget.id}`, {
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
      setDeleteTarget(null);
      await loadSessions();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setDeleteBusy(false);
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
      setSelectedId(data.id);
      setFlashPinId(data.id);
      setTimeout(() => setFlashPinId((prev) => (prev === data.id ? null : prev)), 1600);
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

  useEffect(() => {
    if (!error) return undefined;
    const timer = setTimeout(() => setError(""), 8000);
    return () => clearTimeout(timer);
  }, [error]);

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
    <main className="ws-shell">
      <header className="ws-topbar">
        <div className="ws-topbar__brand">
          <img src={BRAND_LOGO} alt="" className="ws-topbar__logo" />
          <span className="ws-topbar__label">Analyst Console</span>
        </div>
        <div className="ws-topbar__spacer" />
        <div className="ws-topbar__user">
          {profile?.avatar_url ? <img src={profile.avatar_url} alt="" className="ws-topbar__avatar" /> : null}
          <span>{greetingName}</span>
        </div>
        <div className="ws-topbar__actions">
          <a className="ws-icon-btn" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer" title="Discord">
            <MaterialIcon name="forum" size={18} />
          </a>
          {hasAccess && selectedPin ? (
            <button type="button" className="ws-icon-btn" onClick={() => navigator.clipboard?.writeText(selectedPin)} title="Copy PIN">
              <MaterialIcon name="content_copy" size={18} />
            </button>
          ) : null}
          {hasAccess ? (
            <>
              {isSuperAdmin ? (
                <button
                  type="button"
                  className={`ws-icon-btn ${showAdmin ? "ws-icon-btn--active" : ""}`}
                  onClick={() => setShowAdmin((v) => !v)}
                  title={showAdmin ? "Back to cases" : "Admin"}
                >
                  <MaterialIcon name="admin_panel_settings" size={18} />
                </button>
              ) : null}
              <button type="button" className="ws-icon-btn" onClick={loadSessions} title="Refresh">
                <MaterialIcon name="refresh" size={18} />
              </button>
            </>
          ) : (
            <button type="button" className="btn btn--primary btn--sm" onClick={verifyAccess} disabled={verifyBusy}>
              {verifyBusy ? "Checking…" : "Verify access"}
            </button>
          )}
          <button type="button" className="ws-icon-btn" onClick={onLogout} title="Log out">
            <MaterialIcon name="logout" size={18} />
          </button>
        </div>
      </header>

      {!hasAccess ? (
        <section className="access-gate">
          <div className="access-gate-card">
            <MaterialIcon name="shield" size={32} />
            <div>
              <h2>Access not verified yet</h2>
              <p>
                Join our Discord server and get the <strong>Access</strong> role. Then click{" "}
                <strong>Verify access</strong> to unlock PIN generation and scan results.
              </p>
            </div>
            <div className="access-gate-actions">
              <a className="discord-invite inline-invite" href={DISCORD_INVITE_URL} target="_blank" rel="noreferrer">
                Open Discord server
              </a>
              <button className="btn btn--primary" type="button" onClick={verifyAccess} disabled={verifyBusy}>
                {verifyBusy ? "Checking Discord…" : "Verify access"}
              </button>
            </div>
          </div>
        </section>
      ) : null}

      {error ? <div className="error-banner workspace-toast" role="alert">{error}</div> : null}

      {isSuperAdmin && showAdmin ? (
        <AdminPanel apiUrl={API_URL} token={token} authHeaders={authHeaders} />
      ) : (
        <div className={`ws-frame ${hasAccess ? "" : "ws-frame--locked"}`}>
          {hasAccess ? (
            <CaseRail
              sessions={sessions}
              selectedId={selectedId}
              flashPinId={flashPinId}
              onSelect={setSelectedId}
              onDelete={requestDeleteSession}
              onNewPin={createPin}
            />
          ) : null}
          <Results
            detail={detail}
            token={token}
            onSessionReviewSaved={(row) => {
              setSessions((prev) => prev.map((s) => (s.id === row.id ? { ...s, ...row } : s)));
              setDetail((prev) => (prev && prev.id === row.id ? { ...prev, ...row } : prev));
            }}
          />
        </div>
      )}

      <ConfirmModal
        open={Boolean(deleteTarget)}
        title={`Delete PIN ${deleteTarget?.pin ?? ""}?`}
        message="This removes the scan record from your dashboard. The action cannot be undone."
        confirmLabel="Delete session"
        busy={deleteBusy}
        onCancel={() => {
          if (!deleteBusy) setDeleteTarget(null);
        }}
        onConfirm={confirmDeleteSession}
      />
    </main>
  );
}

function Root() {
  const [loginError, setLoginError] = useState(() => {
    if (AUTH_CALLBACK?.kind === "error") {
      return AUTH_CALLBACK.message;
    }
    const params = new URLSearchParams(window.location.search);
    const err = params.get("error");
    return err ? (DISCORD_ERROR_MESSAGES[err] || "Discord login failed. Please try again.") : "";
  });

  useEffect(() => {
    document.title = BRAND_FULL;
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const err = params.get("error");
    if (err) {
      setLoginError(DISCORD_ERROR_MESSAGES[err] || "Discord login failed. Please try again.");
      window.history.replaceState({}, document.title, "/login");
    }
  }, []);

  return <AppRouter loginError={loginError} />;
}

try {
  createRoot(document.getElementById("root")).render(<Root />);
} catch (error) {
  document.body.innerHTML = `<main class="auth-page"><section class="auth-card"><h1>Dashboard Error</h1><p class="error">${error.message}</p></section></main>`;
}
