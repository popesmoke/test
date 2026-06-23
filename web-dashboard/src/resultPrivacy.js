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

const INTERNAL_NOISE_LABELS = new Set(["download_url_extension"]);

function isNoiseInventoryName(name) {
  const base = String(name || "").trim();
  if (!base || base.toLowerCase() === "file" || base.toLowerCase() === "download") return true;
  if (base.startsWith("?") || base.includes("__cf_chl")) return true;
  if (/^UNCONFIRMED\b/i.test(base) || /\.crdownload$/i.test(base)) return true;
  if (/^[A-Za-z0-9]{2,8}[-_~][A-Za-z0-9_~\-]{8,}$/.test(base) && !/\.(exe|dll|msi|bat|ps1|zip|rar|7z)$/i.test(base)) {
    return true;
  }
  return false;
}

export function isNoiseInventoryRow(row) {
  const labels = row?.labels ?? [];
  const meaningful = labels.filter((label) => !INTERNAL_NOISE_LABELS.has(String(label || "").trim()));
  if (!meaningful.length) return true;
  const name = row?.name || row?.file_name || pathBasename(row?.path || row?.target_path || "");
  return isNoiseInventoryName(name);
}

export function primaryFindingSubject(labels, row) {
  for (const raw of labels ?? []) {
    const label = String(raw || "").trim();
    if (EXECUTOR_BRAND_NAMES.has(label)) return label;
  }
  const name = String(row?.name || row?.file_name || pathBasename(row?.path || "") || "").trim();
  if (name && !isNoiseInventoryName(name)) {
    const stem = name.replace(/\.[a-z0-9]{1,5}$/i, "");
    if (stem.length >= 3 && stem.length <= 48) return stem;
  }
  return null;
}

export function publicFindingLabels(labels) {
  const out = new Set();
  for (const raw of labels ?? []) {
    const label = String(raw || "").trim();
    if (!label || INTERNAL_NOISE_LABELS.has(label)) continue;
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

export function publicFindingKind(labels) {
  const kinds = publicFindingLabels(labels);
  return kinds[0] || "Activity indicator";
}

export function publicFindingTitle(labels, row) {
  const kind = publicFindingKind(labels);
  const subject = primaryFindingSubject(labels, row);
  return subject ? `${kind} (${subject})` : kind;
}

export function publicFindingDetail(row) {
  if (row?.file_exists === false) {
    return "This program ran on this PC and was later deleted, but traces of it still remain.";
  }
  if (row?.trace_note?.toLowerCase?.().includes("removed from disk")) {
    return "This program ran on this PC and was later deleted, but traces of it still remain.";
  }
  if (row?.file_exists === true) {
    return "This program matched on this PC and appears in system activity records.";
  }
  return row?.trace_note || "Activity was recorded on this PC.";
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
  const labels = publicFindingLabels(row?.labels);
  return {
    ...displayPathFields(path),
    labels,
    suspicious: Boolean(row?.suspicious) && labels.length > 0,
    last_seen: row?.last_seen,
    file_exists: row?.file_exists,
    trace_note: row?.trace_note
      || (row?.file_exists === false
        ? "This program ran on this PC and was later deleted, but traces of it still remain."
        : row?.sources?.length
          ? "Flagged from system activity records."
          : undefined),
  };
}

export function dedupeInventoryItems(items) {
  const byKey = new Map();
  for (const row of items ?? []) {
    const nameKey = String(row?.name || row?.file_name || pathBasename(row?.path || "")).toLowerCase();
    const key = nameKey && nameKey !== "file" ? nameKey : formatDisplayLocation(row) || row?.path || row?.name;
    const existing = byKey.get(key);
    if (!existing) {
      byKey.set(key, { ...row });
      continue;
    }
    if (row.file_exists === false) existing.file_exists = false;
    if (row.last_seen && (!existing.last_seen || row.last_seen > existing.last_seen)) {
      existing.last_seen = row.last_seen;
    }
    existing.labels = [...new Set([...(existing.labels ?? []), ...(row.labels ?? [])])];
    existing.suspicious = Boolean(existing.suspicious || row.suspicious);
  }
  return [...byKey.values()];
}

export function groupFlaggedPrograms(items) {
  const groups = new Map();
  for (const row of items) {
    const title = publicFindingTitle(row.labels, row);
    const group = groups.get(title) ?? { title, items: [] };
    group.items.push(row);
    groups.set(title, group);
  }
  return [...groups.values()].sort((a, b) => b.items.length - a.items.length);
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
  const rawSummary = String(row?.summary || "").trim();
  let summary = "Program activity was recorded.";
  if (rawSummary.toLowerCase().includes("removed") || rawSummary.toLowerCase().includes("deleted")) {
    summary = "This program ran and was later removed, but traces still remain.";
  } else if (rawSummary.toLowerCase().includes("suspicious") || rawSummary.toLowerCase().includes("flagged")) {
    summary = "This program matched review keywords.";
  } else if (rawSummary && rawSummary.length <= 96) {
    summary = rawSummary;
  }
  return {
    ...displayPathFields(path),
    name: row?.name || row?.file_name || pathBasename(path) || "Program",
    occurred_at: row?.occurred_at,
    summary,
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
  const items = dedupeInventoryItems(
    (inventory.items ?? [])
      .filter((row) => row?.suspicious || (row?.labels ?? []).length)
      .filter((row) => !isNoiseInventoryRow(row))
      .map(sanitizeInventoryRow)
      .filter((row) => row.labels?.length),
  );
  const stringItems = (strings.items ?? []).map(sanitizeStringHit);
  const execItems = (execution.items ?? [])
    .filter((row) => row?.suspicious || row?.occurred_at)
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
