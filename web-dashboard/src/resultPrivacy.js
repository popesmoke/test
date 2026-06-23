function pathBasename(path) {
  const key = String(path || "").replace(/\//g, "\\");
  const i = key.lastIndexOf("\\");
  return i >= 0 ? key.slice(i + 1) : key;
}

export function formatReviewPath(path) {
  const raw = String(path || "").replace(/\//g, "\\").trim();
  if (!raw) return "";
  const userMatch = raw.match(/^[A-Za-z]:\\Users\\[^\\]+\\(.+)$/i);
  if (userMatch) return `%USERPROFILE%\\${userMatch[1]}`;
  const driveMatch = raw.match(/^[A-Za-z]:\\(.+)$/i);
  if (driveMatch && !driveMatch[1].toLowerCase().startsWith("windows\\")) {
    return `%USERPROFILE%\\${driveMatch[1]}`;
  }
  return raw;
}

export function locationHint(path) {
  const low = String(path || "").toLowerCase().replace(/\//g, "\\");
  for (const [marker, label] of [
    ["\\downloads\\", "Downloads"],
    ["\\desktop\\", "Desktop"],
    ["\\documents\\", "Documents"],
    ["\\appdata\\local\\", "AppData (local)"],
    ["\\appdata\\roaming\\", "AppData (roaming)"],
    ["\\temp\\", "Temp"],
    ["\\recycle.bin\\", "Recycle Bin"],
  ]) {
    if (low.includes(marker)) return label;
  }
  return null;
}

export function displayPathFields(path) {
  const name = pathBasename(path);
  return {
    name: name || null,
    location_hint: locationHint(path),
  };
}

export function redactProfilePrefix(text) {
  return String(text || "")
    .replace(/[A-Za-z]:\\Users\\[^\\]+/gi, "[user folder]")
    .replace(/https?:\/\/[^\s]+/gi, "[link removed]")
    .slice(0, 220);
}

const INTERNAL_CHEAT_HINTS = new Set([
  "aimbot",
  "wallhack",
  "triggerbot",
  "silent_aim",
  "speedhack",
  "flyhack",
  "noclip",
  "cheat_engine",
  "roblox_hack",
  "rbx_cheat",
  "free_cheat",
  "hyperion_bypass",
  "hwid_spoof",
  "sunc_compat",
  "unc_compat",
  "auto_execute",
  "script_hub",
  "cheat_label",
  "hack_label",
  "dll_injector",
  "esp",
  "exploit",
  "key_system",
  "research_tool",
  "suspicious_process",
  "suspicious_executed_binary",
]);

const EXECUTOR_BRAND_NAMES = new Set([
  "Volt",
  "Potassium",
  "Wave",
  "Synapse Z",
  "Seliware",
  "Madium",
  "Cosmic",
  "Velocity",
  "SirHurt",
  "Solara",
  "Xeno",
  "Serotonin",
  "Severe",
  "RbxCli",
  "Lumen",
  "Matcha",
  "Matrix Hub",
  "Photon",
  "DX9WARE V2",
  "MacSploit",
  "Opiumware",
  "Delta",
  "Vega X",
  "Codex",
  "Swift",
]);

export function publicFindingLabels(labels) {
  const out = new Set();
  for (const raw of labels ?? []) {
    const label = String(raw || "").trim();
    if (!label) continue;
    if (label.startsWith("cheat:") || INTERNAL_CHEAT_HINTS.has(label)) {
      out.add("Cheat-related indicator");
      continue;
    }
    if (
      label === "known_hash"
      || label === "known_executor"
      || label === "research_tool"
      || EXECUTOR_BRAND_NAMES.has(label)
    ) {
      out.add("Known suspicious program");
      continue;
    }
    if (/executor|inject|bypass|exploit|cheat|hack/i.test(label)) {
      out.add("Suspicious activity indicator");
      continue;
    }
    out.add("Activity indicator");
  }
  return [...out];
}

function sanitizeActivitySummary(summary) {
  const raw = String(summary || "").trim();
  if (!raw) return "Activity recorded on this PC.";
  const low = raw.toLowerCase();
  if (low.includes("executor") || low.includes("cheat") || low.includes("inject") || low.includes("exploit")) {
    return "Suspicious program activity was recorded.";
  }
  if (low.includes("deleted") || low.includes("removed") || low.includes("recycle bin")) {
    return "File removal was logged, but a system trace remains.";
  }
  if (low.includes("download")) {
    return "A browser download was recorded.";
  }
  if (low.includes("powershell") || low.includes("shell history") || low.includes("command")) {
    return "Command-line activity matched review keywords.";
  }
  if (raw.length > 96) {
    return "System activity was recorded on this PC.";
  }
  return raw;
}

function sanitizeActivityEvent(event) {
  const path = event?.path || "";
  return {
    occurred_at: event?.occurred_at ?? null,
    time_unknown: event?.time_unknown,
    category: event?.category,
    summary: sanitizeActivitySummary(event?.summary),
    filter: event?.filter,
    cleanup_at: event?.cleanup_at,
    cleanup_at_display: event?.cleanup_at_display,
    gap_human: event?.gap_human,
    still_in_recycle_bin: event?.still_in_recycle_bin,
    ...displayPathFields(path),
  };
}

function sanitizeInventoryRow(row) {
  const path = row?.path || "";
  return {
    ...displayPathFields(path),
    labels: publicFindingLabels(row?.labels),
    suspicious: Boolean(row?.suspicious),
    last_seen: row?.last_seen,
    file_exists: row?.file_exists,
    trace_note: row?.trace_note
      || (row?.file_exists === false
        ? "Removed from disk, but a system trace remains."
        : row?.sources?.length
          ? "Flagged from system activity records."
          : undefined),
  };
}

function sanitizeStringHit(row) {
  const path = row?.file_path || row?.path || "";
  return {
    ...displayPathFields(path),
    snippet: redactProfilePrefix(row?.snippet),
    occurred_at: row?.occurred_at,
  };
}

function sanitizeExecutionRow(row) {
  const path = row?.path || "";
  return {
    ...displayPathFields(path),
    occurred_at: row?.occurred_at,
    summary: row?.summary || "Program execution recorded.",
    suspicious: Boolean(row?.suspicious),
  };
}

function sanitizeDownloadRow(row) {
  const path = row?.target_path || row?.path || "";
  const labels = publicFindingLabels(row?.matched_labels);
  return {
    file_name: row?.file_name || pathBasename(path) || "Download",
    browser: row?.browser,
    started_at: row?.started_at || row?.ended_at,
    state: row?.state,
    suspicious: Boolean(row?.suspicious || labels.length),
    matched_labels: labels,
    location_hint: row?.location_hint || locationHint(path),
    has_url: Boolean(row?.has_url ?? row?.url),
  };
}

function sanitizeChain(chain) {
  return {
    stem: chain?.stem ? "Related program" : undefined,
    labels: publicFindingLabels(chain?.labels),
    confidence: chain?.confidence,
    summary: chain?.summary || "Multiple related traces were found.",
    steps: (chain?.steps ?? []).map((step) => ({
      action: step?.action,
      detail: sanitizeActivitySummary(step?.detail) || "Related activity was recorded.",
      occurred_at: step?.occurred_at,
      file_exists: step?.file_exists,
      ...displayPathFields(step?.path || ""),
    })),
  };
}

/** Apply privacy + anti-fingerprinting sanitization to scan review payloads. */
export function sanitizeScanReview(review) {
  if (!review || typeof review !== "object") return review;
  const activity = review.last_computer_activity ?? {};
  const inventory = review.executable_inventory ?? {};
  const strings = review.string_detection ?? {};
  const execution = review.execution_activity ?? {};
  const downloads = review.download_history ?? {};
  const chains = review.evidence_chains ?? {};

  const events = (activity.events ?? []).map(sanitizeActivityEvent);
  const items = (inventory.items ?? [])
    .filter((row) => row?.suspicious || (row?.labels ?? []).length)
    .map(sanitizeInventoryRow);
  const stringItems = (strings.items ?? []).map(sanitizeStringHit);
  const execItems = (execution.items ?? [])
    .filter((row) => row?.suspicious)
    .map(sanitizeExecutionRow);
  const downloadItems = (downloads.items ?? []).map(sanitizeDownloadRow);
  const chainItems = (chains.chains ?? []).map(sanitizeChain);

  return {
    ...review,
    last_computer_activity: {
      ...activity,
      events,
      event_count: events.length,
    },
    executable_inventory: {
      ...inventory,
      items,
      total_count: items.length,
      suspicious_count: items.filter((row) => row.suspicious).length,
    },
    string_detection: {
      ...strings,
      items: stringItems,
      hit_count: stringItems.length,
      note: "Matched words in logs, scripts, or command history.",
    },
    execution_activity: {
      ...execution,
      items: execItems,
      event_count: execItems.length,
      suspicious_count: execItems.filter((row) => row.suspicious).length,
    },
    download_history: {
      ...downloads,
      items: downloadItems,
      download_count: downloadItems.length,
      suspicious_count: downloadItems.filter((row) => row.suspicious).length,
    },
    evidence_chains: {
      ...chains,
      chains: chainItems,
      chain_count: chainItems.length,
      note: "Related traces grouped when multiple signals agree.",
    },
  };
}

export function formatDisplayLocation(row) {
  const name = row?.name || row?.file_name;
  const hint = row?.location_hint;
  const path = row?.path || row?.target_path || row?.file_path;
  if (path) {
    const formatted = formatReviewPath(path);
    if (formatted) return formatted;
  }
  if (name && hint) return `%USERPROFILE%\\${hint}\\${name}`;
  return name || (hint ? `%USERPROFILE%\\${hint}` : null);
}

export function shortActivityPath(path) {
  return formatDisplayLocation(displayPathFields(path)) || pathBasename(path) || "User folder";
}

export function privacyPath(path) {
  return shortActivityPath(path);
}

export function privacyAccountLabel(account) {
  const id = account?.user_id;
  if (!id) return "Roblox account detected";
  return `Roblox account #${String(id).slice(-4).padStart(4, "0")}`;
}
