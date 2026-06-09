import { normalizeIsoDateString } from "./dateFormat.js";

const HIGH_CONFIDENCE_SOURCES = new Set([
  "bam_execution",
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

function dateMs(value) {
  if (!value) return null;
  const ms = new Date(normalizeIsoDateString(value)).getTime();
  return Number.isNaN(ms) ? null : ms;
}

export function isScanWindowTimestamp(report, value, source = null) {
  if (source && HIGH_CONFIDENCE_SOURCES.has(source)) return false;
  const eventMs = dateMs(value);
  const endMs = dateMs(report?.generated_at);
  const startMs = dateMs(report?.scan_started_at) ?? (endMs != null ? endMs - 45 * 60 * 1000 : null);
  if (eventMs == null || endMs == null || startMs == null) return false;
  const bufferMs = 3 * 60 * 1000;
  return eventMs >= startMs - bufferMs && eventMs <= endMs + bufferMs;
}

export function sanitizeEventTimestamp(report, value, source = null) {
  if (!value) return null;
  if (isScanWindowTimestamp(report, value, source)) return null;
  return value;
}

export function formatActivityTime(report, value, source = null) {
  const safe = sanitizeEventTimestamp(report, value, source);
  return safe ?? null;
}
