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

export function scanReviewFromReport(report) {
  const sec = report.security_integrity_signals ?? {};
  const bundled = sec.scan_review;
  const downloads = sec.browser_download_history;
  if (bundled?.available) {
    if (downloads?.available && !bundled.download_history?.items?.length) {
      return { ...bundled, download_history: downloads };
    }
    return bundled;
  }
  return buildClientScanReview(report);
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
    if (!item.normalized_path) continue;
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
  const addInv = (path, source, lastSeen, suspicious, labels = []) => {
    const key = String(path || "").toLowerCase();
    if (!key || seen.has(key)) return;
    seen.add(key);
    inventoryItems.push({
      path,
      name: pathBasename(path),
      sources: [source],
      labels,
      suspicious,
      last_seen: lastSeen,
    });
  };

  for (const hit of sec.roblox_executor_indicators?.file_hits ?? []) {
    addInv(hit.path, "folder_scan", hit.modified, true, hit.matched_names ?? []);
  }
  for (const hit of sec.executor_artifact_evidence?.hits ?? []) {
    addInv(
      hit.path,
      hit.artifact_source ?? "executor_artifact",
      hit.display_at || hit.modified,
      true,
      [
        ...(hit.executor_name_hits ?? []),
        ...(hit.cheat_filename_hints ?? []).map((label) => `cheat:${label}`),
      ],
    );
  }
  for (const hit of sec.designated_folder_suspicious_files?.hits ?? []) {
    const source = hit.removed_artifact ? "removed_artifact" : "folder_scan";
    addInv(
      hit.path,
      source,
      hit.display_at || hit.modified,
      true,
      [
        ...(hit.executor_name_hits ?? []),
        ...(hit.cheat_filename_hints ?? []).map((label) => `cheat:${label}`),
      ],
    );
  }
  for (const item of sec.bam?.items ?? []) {
    addInv(item.normalized_path, "execution_history", item.last_execution_utc, true, []);
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

  const activityEvents = (activity.events ?? [])
    .filter((e) => e.occurred_at)
    .map((e) => ({
      occurred_at: e.occurred_at,
      category: e.category,
      summary: e.label || e.detail,
      path: e.path,
    }))
    .sort((a, b) => tsMs(b.occurred_at) - tsMs(a.occurred_at));

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
      events: activityEvents.slice(0, 80),
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
