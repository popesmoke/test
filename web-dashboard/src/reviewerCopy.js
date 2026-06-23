/** Strip scanner-internals from reviewer-visible strings. */

const BLOCKED_PATTERNS = [
  /tamper or integrity/i,
  /surviving artifacts/i,
  /when usn or event logs/i,
  /recycle bin \$i metadata/i,
  /reconstruction confidence/i,
  /usn journaling/i,
  /must rely on recycle/i,
  /bam, prefetch, pca/i,
  /sha-?256/i,
  /prefetch/i,
  /\bbam\b/i,
  /\busn\b/i,
  /forensic/i,
  /provenance/i,
  /artifact hit/i,
  /no_substantiated/i,
  /disk-backed/i,
  /sqlite/i,
  /windows artifacts/i,
  /profile\.folder/i,
  /filesystem scan/i,
  /verdict:/i,
  /executor path/i,
  /download history/i,
  /recycle bin but still/i,
  /removed from disk or/i,
  /potassium/i,
  /volume shadow copy/i,
  /shadow-copy/i,
  /vssadmin/i,
  /defender exclusion/i,
  /antivirus exclusion/i,
  /event log/i,
  /sysmain/i,
  /amcache/i,
  /user-mode/i,
  /kernel-level/i,
];

const GENERIC_REASON_LABELS = {
  "Known executor binary hash": "Known program fingerprint",
  "Executor artifact evidence": "Repeated warning signs",
  "Roblox integrity signals": "Game client looked unusual",
  "Executor / cheat path matches": "Flagged file locations",
  "Executor / cheat-tagged recent files": "Recent flagged files",
  "Prefetch execution traces": "Recent program activity",
  "Profile folder executor filenames": "Files in common folders",
  "Profile folder cheat-like filenames": "Suspicious file names",
  "Profile folder odd filenames": "Unusual file names",
  "Deleted cheat/executor traces recovered": "Deleted programs left traces",
  "Suspicious Recycle Bin items": "Recycle Bin items flagged",
  "Persistence mechanisms": "Auto-start entries flagged",
  "Forensic engine findings": "Extra warning signs",
  "Cross-artifact agreement": "Same signal in multiple places",
  "UserAssist activity": "Recent launch activity",
  "BAM activity": "Recent launch activity",
  "Defender signal": "Security software signal",
  "Deletion or log clearing": "Cleanup activity detected",
  "Bypass / cover-up signals": "Signs of hiding activity",
  "Crash or log matches": "Log keyword matches",
  "No matched indicators": "No major matches",
};

const GENERIC_REASON_DETAILS = {
  "Known executor binary hash": "One or more files matched a known fingerprint on the watch list.",
  "Executor artifact evidence": "Several related warning signs showed up on this scan.",
  "Roblox integrity signals": "Something around the game client looked unusual.",
  "Executor / cheat path matches": "One or more file paths matched the watch list.",
  "Executor / cheat-tagged recent files": "Recent files matched review keywords.",
  "Prefetch execution traces": "Recent program activity matched the watch list.",
  "Profile folder executor filenames": "Files in common folders matched the watch list.",
  "Profile folder cheat-like filenames": "Some file names looked like common cheat labels.",
  "Profile folder odd filenames": "Some file names looked randomly generated.",
  "Deleted cheat/executor traces recovered": "Programs were deleted, but traces of them still remain on this PC.",
  "Suspicious Recycle Bin items": "The Recycle Bin still holds flagged item names.",
  "Persistence mechanisms": "Something was set to start automatically with Windows.",
  "Forensic engine findings": "Additional warning signs were recorded.",
  "Cross-artifact agreement": "The same program name appeared in more than one place.",
  "UserAssist activity": "Recent launch activity matched review keywords.",
  "BAM activity": "Recent launch activity matched review keywords.",
  "Defender signal": "Windows security settings or history looked unusual.",
  "Deletion or log clearing": "Signs appeared that logs or traces may have been cleaned up.",
  "Bypass / cover-up signals": "Signs appeared that someone may have tried to hide activity.",
  "Crash or log matches": "Logs contained words from the watch list.",
  "No matched indicators": "Nothing major matched the watch lists on this scan.",
};

const GENERIC_FINDING_TITLES = {
  "Deleted executor traces recovered": "Deleted programs left traces",
  "Known executor left forensic traces after deletion": "Deleted programs left traces",
  "Shell history mentions cleanup or disable commands": "Command history looked unusual",
  "Prefetch proves a checked executor ran": "Recent program activity flagged",
  "6 file(s) in Downloads/Desktop/Documents matched a checked executor name":
    "Files in common folders matched a checked program name",
  "Disk-backed forensic signals contributed": "Review summary",
  "Shadow-copy service is stopped": "Backup service is turned off",
  "Defender exclusions are configured": "Security scan exclusions found",
  "Tampering with the anti-cheat itself": "Security software was changed",
  "BAM execution logging appears disabled": "Program activity logging looks disabled",
  "Real-time protection is disabled": "Real-time protection is off",
};

const GENERIC_FINDING_DETAILS = {
  "Deleted executor traces recovered":
    "Programs were deleted, but traces of them still remain on this PC.",
  "Known executor left forensic traces after deletion":
    "Programs were deleted, but traces of them still remain on this PC.",
  "Shadow-copy service is stopped":
    "Windows restore points are not running. This is sometimes done before cleanup or tampering.",
  "Defender exclusions are configured":
    "Folders or programs are excluded from antivirus scanning. Check that these are legitimate.",
  "Tampering with the anti-cheat itself":
    "Security software settings were changed in a way that could hide activity.",
};

/** Normalize punctuation and fix common mojibake before display. */
export function plainDisplayText(text) {
  if (text == null || text === "") return "";
  return String(text)
    .replace(/β€[""]?/g, ", ")
    .replace(/â€[""]?/g, ", ")
    .replace(/\u00e2\u20ac[\u201c\u201d"]?/g, ", ")
    .replace(/\s*—\s*/g, ", ")
    .replace(/\s*–\s*/g, ", ")
    .replace(/\s*·\s*/g, ", ")
    .replace(/,\s*,+/g, ", ")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function genericReasonLabel(label) {
  const key = String(label || "").trim();
  const mapped = GENERIC_REASON_LABELS[key];
  if (mapped) return mapped;
  return plainDisplayText(
    key.replace(/\b(executor|cheat|forensic|bam|prefetch|sha-?256|usn)\b/gi, "flagged").trim(),
  );
}

export function genericReasonDetail(label, detail) {
  const key = String(label || "").trim();
  if (GENERIC_REASON_DETAILS[key]) return GENERIC_REASON_DETAILS[key];
  if (GENERIC_FINDING_DETAILS[key]) return GENERIC_FINDING_DETAILS[key];
  const safe = reviewerSafeText(detail);
  if (!safe) return "Something unusual was recorded on this scan.";
  if (BLOCKED_PATTERNS.some((pattern) => pattern.test(safe))) {
    return "Something unusual was recorded on this scan.";
  }
  const cleaned = plainDisplayText(safe);
  if (!cleaned || cleaned.length > 120) return "Something unusual was recorded on this scan.";
  return cleaned;
}

export function genericFindingTitle(title) {
  const raw = String(title || "").trim();
  if (!raw) return "Warning sign";
  if (GENERIC_FINDING_TITLES[raw]) return GENERIC_FINDING_TITLES[raw];
  if (/verdict:|no_substantiated|artifact hit|provenance|forensic|bam|prefetch|sha-?256|\busn\b/i.test(raw)) {
    return "Review summary";
  }
  return plainDisplayText(
    raw
      .replace(/\bexecutor\b/gi, "flagged program")
      .replace(/\bcheat\b/gi, "flagged")
      .replace(/\bforensic\b/gi, "system"),
  );
}

export function reviewerSafeText(text) {
  if (text == null || text === "") return null;
  const value = plainDisplayText(String(text).trim());
  if (!value) return null;
  if (BLOCKED_PATTERNS.some((pattern) => pattern.test(value))) return null;
  return value;
}

export function activitySuspicionRank(event) {
  const extra = event?.extra ?? {};
  const category = String(event?.category ?? "");
  const kind = String(event?.kind ?? "");
  const label = String(event?.label ?? "").toLowerCase();
  if (extra.suspicious) return 0;
  if (category === "execution" && label) return 1;
  if (category === "commands") return 2;
  if (kind === "sha256_blocklist") return 3;
  if (category === "execution") return 4;
  if (category === "persistence") return 5;
  if (category === "deletions" && label && !label.includes("recycle")) return 6;
  if (category === "browser" && extra.suspicious) return 7;
  if (category === "files") return 8;
  if (category === "deletions") return 9;
  if (category === "browser") return 10;
  if (category === "roblox") return 11;
  return 12;
}

export function sortBySuspicion(events) {
  return [...(events ?? [])].sort((left, right) => {
    const rankDiff = activitySuspicionRank(left) - activitySuspicionRank(right);
    if (rankDiff !== 0) return rankDiff;
    const leftMs = left?.occurred_at ? new Date(left.occurred_at).getTime() : 0;
    const rightMs = right?.occurred_at ? new Date(right.occurred_at).getTime() : 0;
    return rightMs - leftMs;
  });
}
