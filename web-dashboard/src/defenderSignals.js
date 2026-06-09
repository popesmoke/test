export function parseMaybeJson(value) {
  if (value == null) return null;
  if (typeof value === "object") return value;
  if (typeof value !== "string" || !value.trim()) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function userProfileExclusions(settings) {
  const paths = settings?.ExclusionPath;
  if (!Array.isArray(paths)) return [];
  return paths.filter((path) =>
    /\\users\\|\\downloads|\\desktop|\\appdata\\local\\temp/i.test(String(path)),
  );
}

export function defenderSummary(defender) {
  if (!defender?.available) {
    return { available: false, statusLabel: "Unavailable", detail: defender?.reason || "Not collected on this OS." };
  }
  const structured = defender.settings_structured ?? parseMaybeJson(defender.settings) ?? {};
  const status = defender.computer_status ?? {};
  const summary = defender.summary ?? {};
  const threats = defender.threat_detections ?? [];
  const quarantine = defender.quarantine_history ?? [];
  const realtimeOff =
    structured.DisableRealtimeMonitoring === true || summary.realtime_monitoring_disabled === true;
  const realtime =
    status.RealTimeProtectionEnabled ?? summary.real_time_protection_enabled ?? !realtimeOff;
  const exclusions = userProfileExclusions(structured);

  let statusLabel = "Protected";
  let tone = "clean";
  if (realtimeOff || realtime === false) {
    statusLabel = "Real-time protection off";
    tone = "bad";
  } else if (quarantine.length || threats.length) {
    statusLabel = `${quarantine.length || threats.length} threat signal(s)`;
    tone = quarantine.length ? "bad" : "watch";
  } else if (exclusions.length) {
    statusLabel = `${exclusions.length} user-folder exclusion(s)`;
    tone = "watch";
  }

  return {
    available: true,
    statusLabel,
    tone,
    realtimeEnabled: realtime !== false,
    tamperProtected: status.IsTamperProtected ?? summary.tamper_protection_enabled,
    threatCount: threats.length,
    quarantineCount: quarantine.length,
    userExclusions: exclusions,
    threats,
    quarantine,
    protectionEvents: parseMaybeJson(defender.protection_history) ?? [],
  };
}

export function defenderHasActionableSignal(defender) {
  const view = defenderSummary(defender);
  if (!view.available) return false;
  if (!view.realtimeEnabled) return true;
  if (view.quarantineCount > 0 || view.threatCount > 0) return true;
  if (view.userExclusions.length > 0) return true;
  const history = defender.protection_history ?? "";
  if (/quarantine|threat.*detected|malware|removed threat|disabled.*real-?time/i.test(history)) {
    return true;
  }
  return false;
}
