/** Simple reviewer-facing view of which Windows trace layers were checked. */

const STATUS_LABELS = {
  collected: "Checked",
  unavailable: "Not available",
  skipped: "Skipped",
};

const STATUS_TONES = {
  collected: "clean",
  unavailable: "muted",
  skipped: "watch",
};

export function forensicSourcesView(sec) {
  const inventory = sec?.forensic_sources_inventory ?? {};
  if (!inventory.available) {
    return {
      available: false,
      sources: [],
      inconsistencies: [],
      summary: inventory.reason || "Trace checklist was not included in this report.",
    };
  }
  const sources = (inventory.sources ?? []).map((row) => ({
    id: row.id,
    label: row.label,
    status: row.status || "skipped",
    statusLabel: STATUS_LABELS[row.status] || "Unknown",
    tone: STATUS_TONES[row.status] || "muted",
    count: Number(row.count) || 0,
  }));
  const inconsistencies = (inventory.inconsistency_checks ?? []).map((row) => ({
    summary: String(row.summary || "Timeline mismatch detected"),
    severity: row.severity || "medium",
    type: row.type || "inconsistency",
  }));
  return {
    available: true,
    sources,
    inconsistencies,
    collectedCount: inventory.collected_count ?? sources.filter((s) => s.status === "collected").length,
    sourceCount: inventory.source_count ?? sources.length,
    summary: `${inventory.collected_count ?? 0} of ${inventory.source_count ?? sources.length} trace layers were checked on this scan.`,
  };
}

export function securitySignalsView(sec) {
  const defender = sec?.defender ?? {};
  const deletion = sec?.deletion_and_log_clearing_signals ?? {};
  const traceCleaners = sec?.trace_cleaner_signals ?? {};
  const eventLogs = sec?.windows_event_logs ?? {};
  const exclusions =
    defender?.summary?.user_profile_exclusion_count ??
    (defender?.settings_structured?.ExclusionPath?.length || 0);

  const logClearingHints = [];
  const rawSample = String(deletion?.raw_sample || "");
  if (/1102|cleared|truncate|journal/i.test(rawSample)) {
    logClearingHints.push("Event logs may have been cleared recently.");
  }
  if ((deletion?.usn_delete_line_count || 0) > 0) {
    logClearingHints.push(`${deletion.usn_delete_line_count} file delete events in the change journal.`);
  }

  return {
    defenderAvailable: Boolean(defender.available),
    realtimeOff:
      defender?.summary?.realtime_monitoring_disabled === true ||
      defender?.computer_status?.RealTimeProtectionEnabled === false,
    exclusionCount: Number(exclusions) || 0,
    threatCount: (defender?.threat_detections ?? []).length,
    protectionHistoryLength: String(defender?.protection_history || "").length,
    logClearingHints,
    traceCleanerCount: traceCleaners?.finding_count ?? (traceCleaners?.findings ?? []).length,
    traceCleaners: traceCleaners?.findings ?? [],
    eventLogCount: eventLogs?.count ?? (eventLogs?.events ?? []).length,
  };
}
