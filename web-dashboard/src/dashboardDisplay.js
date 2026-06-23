import { formatDisplayLocation, displayPathFields, publicFindingLabels } from "./resultPrivacy.js";

export function formatSimpleOsLabel(os) {
  const raw = String(os || "").trim();
  if (!raw) return "Windows PC";
  if (raw.toLowerCase().includes("windows")) {
    const version = raw.match(/(\d+\.\d+)/);
    return version ? `Windows ${version[1]}` : "Windows";
  }
  return raw.split("-")[0] || raw;
}

export function formatSystemOverviewLines(system, perf, formatGmtPlus3) {
  const lines = [
    `System: ${formatSimpleOsLabel(system?.os)}`,
    `CPU: ${system?.cpu_count_physical ?? "?"} cores (${system?.cpu_count_logical ?? "?"} threads)`,
  ];
  if (perf?.boot_time) {
    lines.push(`Last boot: ${formatGmtPlus3(perf.boot_time)}`);
  }
  return lines;
}

export function formatRecycleBinItems(items) {
  return (items ?? [])
    .filter((item) => item.original_path || item.name?.startsWith?.("$I"))
    .slice(0, 30)
    .map((item) => {
      const name = item.original_path
        ? formatDisplayLocation(displayPathFields(item.original_path)) || "Deleted file"
        : "Deleted item";
      const flagged = item.suspicious_recycle_item || (item.executor_name_hits ?? []).length;
      return {
        key: `${item.name}-${item.deleted_at || item.modified}`,
        name,
        flagged,
        when: item.display_at || item.deleted_at || item.modified,
        note: flagged ? "Matched review rules" : "In Recycle Bin",
      };
    });
}

export function formatPersistenceEntries(persistence) {
  if (persistence?.available === false) {
    return { empty: true, message: persistence.reason || "Startup scan not available on this PC." };
  }
  const suspicious = persistence?.suspicious_entries ?? persistence?.suspicious ?? [];
  if (!suspicious.length) {
    return { empty: true, message: "No flagged startup or auto-run entries." };
  }
  return {
    empty: false,
    rows: suspicious.slice(0, 25).map((entry, index) => ({
      key: `${entry.source}-${entry.name}-${index}`,
      title: entry.name || "Startup entry",
      detail: publicFindingLabels([
        ...(entry.executor_name_hits ?? []),
        ...(entry.cheat_filename_hints ?? []),
      ]).join(", ") || "Flagged startup item",
      target: formatDisplayLocation(displayPathFields(entry.target || "")) || "System startup",
    })),
  };
}

export function formatRobloxIntegrity(runtime) {
  if (runtime?.available === false) {
    return { empty: true, message: runtime.reason || "Roblox check not available on this scan." };
  }
  const modules = runtime?.suspicious_modules ?? [];
  if (!modules.length) {
    return { empty: true, message: "No unusual Roblox signals on this scan." };
  }
  return {
    empty: false,
    rows: modules.slice(0, 20).map((row, index) => ({
      key: `${row.module_path || row.path}-${index}`,
      title:
        publicFindingLabels(row.executor_labels ?? row.reasons ?? []).join(", ") || "Unusual Roblox signal",
      path: formatDisplayLocation(displayPathFields(row.module_path || row.path || "")) || "Roblox process",
      mode: row.scan_mode === "live" ? "While Roblox was open" : "From system logs",
    })),
  };
}
