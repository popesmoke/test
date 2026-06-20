import { normalizeIsoDateString } from "./dateFormat.js";

const HIGH_CONFIDENCE_SOURCES = new Set([
  "bam_execution",
  "dam_execution",
  "prefetch_last_run",
  "usn_delete",
  "recycle_bin",
  "recycle_metadata",
  "event_log",
  "security_audit_delete",
  "sysmon_file_delete",
  "userassist",
  "browser_download_start",
  "browser_download_end",
  "removed_executor_artifact",
]);

export const EXECUTION_TIMESTAMP_SOURCES = new Set([
  "bam_execution",
  "dam_execution",
  "userassist",
  "prefetch_last_run",
  "amcache_last_run",
]);

const FILE_METADATA_SOURCES = new Set([
  "file_mtime",
  "file_atime",
  "prefetch_mtime",
  "prefetch_file_mtime",
  "designated_mtime",
  "recent_mtime",
  "shortcut_mtime",
  "pca_store_key_mtime",
  "recorded",
]);

const SOURCE_ALIASES = {
  bam_registry: "bam_execution",
  prefetch_mtime: "prefetch_last_run",
  prefetch_execution: "prefetch_last_run",
  runtime_cache: "prefetch_last_run",
};

function normalizeSource(source) {
  if (!source) return null;
  const key = String(source).trim().toLowerCase();
  return SOURCE_ALIASES[key] || key;
}

function dateMs(value) {
  if (!value) return null;
  const ms = new Date(normalizeIsoDateString(value)).getTime();
  return Number.isNaN(ms) ? null : ms;
}

export function isScanWindowTimestamp(report, value, source = null) {
  const src = normalizeSource(source);
  if (src && HIGH_CONFIDENCE_SOURCES.has(src)) {
    // Execution sources still drop scan-window noise — timestamps during collection are unreliable.
    if (src && EXECUTION_TIMESTAMP_SOURCES.has(src)) {
      // fall through to window check
    } else {
      return false;
    }
  }
  const eventMs = dateMs(value);
  const endMs = dateMs(report?.generated_at);
  const startMs = dateMs(report?.scan_started_at) ?? (endMs != null ? endMs - 45 * 60 * 1000 : null);
  if (eventMs == null || endMs == null || startMs == null) return false;
  const bufferMs = 3 * 60 * 1000;
  return eventMs >= startMs - bufferMs && eventMs <= endMs + bufferMs;
}

export function sanitizeEventTimestamp(report, value, source = null) {
  if (!value) return null;
  const src = normalizeSource(source);
  if (src && EXECUTION_TIMESTAMP_SOURCES.has(src)) {
    return sanitizeExecutionTimestamp(report, value, src);
  }
  if (src && FILE_METADATA_SOURCES.has(src)) {
    if (isScanWindowTimestamp(report, value, src)) return null;
    return value;
  }
  if (isScanWindowTimestamp(report, value, source)) return null;
  return value;
}

export function sanitizeExecutionTimestamp(report, value, source = null) {
  if (!value) return null;
  const src = normalizeSource(source);
  if (!src || !EXECUTION_TIMESTAMP_SOURCES.has(src)) return null;
  if (isScanWindowTimestamp(report, value, src)) return null;
  return value;
}

export function formatActivityTime(report, value, source = null) {
  return sanitizeEventTimestamp(report, value, source);
}
