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
];

export function reviewerSafeText(text) {
  if (text == null || text === "") return null;
  const value = String(text).trim();
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
