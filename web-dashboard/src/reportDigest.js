function pathBasename(path) {
  const key = String(path || "").replace(/\//g, "\\");
  const i = key.lastIndexOf("\\");
  return i >= 0 ? key.slice(i + 1) : key;
}

function tsMs(value) {
  if (!value) return 0;
  const ms = new Date(String(value).replace(/\.(\d{3})\d+/, ".$1")).getTime();
  return Number.isNaN(ms) ? 0 : ms;
}

const SYSTEM_NOISE_EXES = new Set([
  "powershell.exe",
  "pwsh.exe",
  "conhost.exe",
  "cmd.exe",
  "explorer.exe",
  "svchost.exe",
  "runtimebroker.exe",
  "dllhost.exe",
  "searchhost.exe",
  "sihost.exe",
  "taskhostw.exe",
  "dwm.exe",
  "fontdrvhost.exe",
  "audiodg.exe",
  "spoolsv.exe",
  "wudfhost.exe",
  "backgroundtaskhost.exe",
  "smartscreen.exe",
  "openwith.exe",
  "mmc.exe",
  "msiexec.exe",
  "setup.exe",
  "werfault.exe",
  "consent.exe",
  "msedge.exe",
  "chrome.exe",
  "firefox.exe",
  "brave.exe",
  "opera.exe",
  "vivaldi.exe",
  "ctfmon.exe",
  "python.exe",
  "pythonw.exe",
  "cursor.exe",
  "code.exe",
  "windowsterminal.exe",
  "nvidia overlay.exe",
  "nvcontainer.exe",
]);

const SYSTEM_PATH_MARKERS = [
  "\\windows\\system32\\",
  "\\windows\\syswow64\\",
  "\\windows\\systemapps\\",
  "\\program files\\",
  "\\program files (x86)\\",
  "\\windowsapps\\",
];

function isReviewNoisePath(path) {
  const low = String(path || "").toLowerCase().replace(/\//g, "\\");
  if (!low) return true;
  const base = pathBasename(low).toLowerCase();
  if (SYSTEM_NOISE_EXES.has(base)) return true;
  if (SYSTEM_PATH_MARKERS.some((marker) => low.includes(marker)) && base.endsWith(".exe")) return true;
  return false;
}

function hasExecutorLabels(labels) {
  return (labels ?? []).length > 0;
}

export function scanReviewFromReport(report) {
  const sec = report.security_integrity_signals ?? {};
  const bundled = sec.scan_review;
  const downloads = sec.browser_download_history;
  if (bundled?.available) {
    let merged = { ...bundled };
    if (downloads?.available && !bundled.download_history?.items?.length) {
      merged = { ...merged, download_history: downloads };
    }
    return enrichBundledScanReview(merged, report);
  }
  return buildClientScanReview(report);
}

function enrichBundledScanReview(bundled, report) {
  const fallback = buildClientScanReview(report);
  const events = [...(bundled.last_computer_activity?.events ?? [])];
  const seenEvents = new Set(events.map((e) => `${String(e.path || "").toLowerCase()}|${e.occurred_at || ""}`));

  for (const event of fallback.last_computer_activity?.events ?? []) {
    const isDeletion =
      event.category === "deletions" ||
      String(event.summary || "").includes("no longer on disk") ||
      String(event.summary || "").includes("Recycle Bin");
    if (!isDeletion || !event.path || !event.occurred_at || isReviewNoisePath(event.path)) continue;
    const key = `${String(event.path).toLowerCase()}|${event.occurred_at}`;
    if (seenEvents.has(key)) continue;
    seenEvents.add(key);
    events.push(event);
  }
  events.sort((a, b) => tsMs(b.occurred_at) - tsMs(a.occurred_at));

  const inventory = [...(bundled.executable_inventory?.items ?? [])].filter(
    (row) => !isReviewNoisePath(row.path) && (row.suspicious || (row.labels ?? []).length),
  );
  const seenInventory = new Set(inventory.map((row) => String(row.path || "").toLowerCase()));
  for (const row of fallback.executable_inventory?.items ?? []) {
    if (isReviewNoisePath(row.path) || !(row.labels ?? []).length) continue;
    const key = String(row.path || "").toLowerCase();
    if (seenInventory.has(key)) continue;
    seenInventory.add(key);
    inventory.push(row);
  }
  inventory.sort((a, b) => tsMs(b.last_seen) - tsMs(a.last_seen));

  return {
    ...bundled,
    last_computer_activity: {
      ...(bundled.last_computer_activity ?? {}),
      events: events.slice(0, 120),
      event_count: events.length,
    },
    executable_inventory: {
      ...(bundled.executable_inventory ?? {}),
      items: inventory.slice(0, 120),
      total_count: inventory.length,
      suspicious_count: inventory.filter((row) => row.suspicious).length,
    },
  };
}

function buildClientScanReview(report) {
  const sec = report.security_integrity_signals ?? {};
  const perf = report.performance_environment ?? {};
  const activity = sec.user_activity_timeline ?? {};
  const execSummary = sec.executor_activity_summary ?? {};

  const executionItems = (execSummary.events ?? []).map((e) => ({
    path: e.path,
    name: pathBasename(e.path),
    occurred_at: e.occurred_at,
    source: "matched_signal",
    summary: e.detail || "Matched a reviewed signal.",
    suspicious: true,
    recency: e.recency,
  }));

  for (const item of sec.bam?.items ?? []) {
    if (!item.normalized_path || item.path_allowlisted || isReviewNoisePath(item.normalized_path)) continue;
    const labels = [...(item.executor_name_hits ?? []), ...(item.cheat_filename_hints ?? [])];
    if (!labels.length) continue;
    executionItems.push({
      path: item.normalized_path,
      name: pathBasename(item.normalized_path),
      occurred_at: item.last_execution_utc,
      source: "execution_history",
      summary: "A program was run on this PC.",
      suspicious: true,
      recency: "unknown",
    });
  }

  executionItems.sort((a, b) => tsMs(b.occurred_at) - tsMs(a.occurred_at));

  const inventoryItems = [];
  const seen = new Set();
  const addInv = (path, source, lastSeen, suspicious, labels = [], extra = {}) => {
    if (!path || isReviewNoisePath(path) || !hasExecutorLabels(labels)) return;
    const key = String(path).toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    inventoryItems.push({
      path,
      name: pathBasename(path),
      sources: [source],
      labels,
      suspicious,
      last_seen: lastSeen,
      ...extra,
    });
  };

  for (const hit of sec.roblox_executor_indicators?.file_hits ?? []) {
    addInv(hit.path, "folder_scan", hit.modified, true, hit.matched_names ?? []);
  }
  for (const hit of sec.executor_artifact_evidence?.hits ?? []) {
    if (hit.path_allowlisted || isReviewNoisePath(hit.path)) continue;
    const labels = [
      ...(hit.executor_name_hits ?? []),
      ...(hit.cheat_filename_hints ?? []).map((label) => `cheat:${label}`),
    ];
    addInv(hit.path, hit.artifact_source ?? "executor_artifact", hit.display_at || hit.modified, true, labels, {
      file_exists: hit.file_exists,
    });
  }
  for (const hit of sec.designated_folder_suspicious_files?.hits ?? []) {
    const source = hit.removed_artifact ? "removed_artifact" : "folder_scan";
    const labels = [
      ...(hit.executor_name_hits ?? []),
      ...(hit.cheat_filename_hints ?? []).map((label) => `cheat:${label}`),
    ];
    addInv(hit.path, source, hit.display_at || hit.modified, true, labels, { file_exists: hit.file_exists });
  }
  for (const item of sec.bam?.items ?? []) {
    if (!item.normalized_path || item.path_allowlisted || isReviewNoisePath(item.normalized_path)) continue;
    const labels = [...(item.executor_name_hits ?? []), ...(item.cheat_filename_hints ?? [])];
    if (!labels.length) continue;
    addInv(item.normalized_path, "execution_history", item.last_execution_utc, true, labels, {
      file_exists: item.file_exists,
    });
  }

  inventoryItems.sort((a, b) => tsMs(b.last_seen) - tsMs(a.last_seen));

  const stringItems = (sec.command_history_keyword_hits?.hits ?? []).map((h) => ({
    source: "powershell_history",
    file_path: h.path,
    matched_terms: h.matched ?? [],
    matched_groups: ["command_history"],
    snippet: h.line,
    occurred_at: h.occurred_at || h.history_file_modified_utc,
  }));

  const trashItems = perf.trash?.items ?? [];
  const deletionEvents = [];
  const seenDeletion = new Set();
  const addDeletion = (occurredAt, path, summary) => {
    const key = `${String(path || "").toLowerCase()}|${occurredAt || ""}`;
    if (!occurredAt || !path || isReviewNoisePath(path) || seenDeletion.has(key)) return;
    seenDeletion.add(key);
    deletionEvents.push({
      occurred_at: occurredAt,
      category: "deletions",
      summary,
      path,
    });
  };
  const cleanupByPath = new Map(
    (sec.deletion_cleanup_analysis?.correlations ?? []).map((row) => [String(row.path || "").toLowerCase(), row]),
  );
  for (const item of trashItems) {
    const path = item.original_path || "";
    if (!path) continue;
    const cleanup = cleanupByPath.get(path.toLowerCase());
    const name = pathBasename(path);
    addDeletion(
      item.display_at || item.deleted_at || item.modified,
      path,
      cleanup?.summary || `${name} was deleted or moved to the Recycle Bin.`,
    );
  }
  for (const row of sec.deletion_cleanup_analysis?.correlations ?? []) {
    if (!row.path || !row.deleted_at) continue;
    const key = `${String(row.path).toLowerCase()}|${row.deleted_at}`;
    if (seenDeletion.has(key)) continue;
    seenDeletion.add(key);
    deletionEvents.push({
      occurred_at: row.deleted_at,
      category: "deletions",
      summary: row.summary,
      path: row.path,
      cleanup_at: row.cleanup_at,
      cleanup_at_display: row.cleanup_at_display,
      cleanup_type: row.cleanup_type,
      gap_human: row.gap_human,
    });
  }
  for (const hit of sec.executor_artifact_evidence?.hits ?? []) {
    if (hit.file_exists !== false || hit.path_allowlisted || isReviewNoisePath(hit.path)) continue;
    const labels = [...(hit.executor_name_hits ?? []), ...(hit.cheat_filename_hints ?? [])];
    if (!labels.length) continue;
    const path = hit.path || "";
    const name = pathBasename(path);
    addDeletion(
      hit.display_at || hit.modified,
      path,
      `${name} is no longer on disk or in the Recycle Bin; Windows activity traces still record the deletion.`,
    );
  }
  const activityEvents = [
    ...deletionEvents,
    ...(activity.events ?? [])
      .filter((e) => e.occurred_at && e.category !== "deletions" && !isReviewNoisePath(e.path))
      .map((e) => ({
        occurred_at: e.occurred_at,
        category: e.category,
        summary: e.label || e.detail,
        path: e.path,
      })),
  ].sort((a, b) => tsMs(b.occurred_at) - tsMs(a.occurred_at));

  const downloadItems = (sec.browser_download_history?.items ?? []).map((dl) => ({
    browser: dl.browser,
    profile: dl.profile,
    url: dl.url,
    target_path: dl.target_path,
    file_name: pathBasename(dl.target_path || dl.url),
    started_at: dl.started_at,
    ended_at: dl.ended_at,
    state: dl.state,
    suspicious: dl.suspicious,
    matched_labels: dl.matched_labels ?? [],
  }));

  return {
    available: true,
    last_computer_activity: {
      available: true,
      boot_time: perf.boot_time,
      scan_time: report.generated_at,
      milestones: [
        perf.boot_time ? { occurred_at: perf.boot_time, label: "PC was turned on", summary: "Last boot time." } : null,
        { occurred_at: report.generated_at, label: "Scan finished", summary: "Report collected." },
      ].filter(Boolean),
      events: activityEvents.slice(0, 120),
      event_count: activityEvents.length,
    },
    executable_inventory: {
      available: true,
      total_count: inventoryItems.length,
      suspicious_count: inventoryItems.filter((i) => i.suspicious).length,
      items: inventoryItems.slice(0, 120),
    },
    string_detection: {
      available: true,
      hit_count: stringItems.length,
      items: stringItems.slice(0, 80),
    },
    execution_activity: {
      available: true,
      event_count: executionItems.length,
      suspicious_count: executionItems.filter((i) => i.suspicious).length,
      items: executionItems.slice(0, 100),
    },
    download_history: {
      available: Boolean(sec.browser_download_history?.available || downloadItems.length),
      download_count: downloadItems.length,
      suspicious_count: downloadItems.filter((i) => i.suspicious).length,
      items: downloadItems.slice(0, 120),
    },
  };
}
