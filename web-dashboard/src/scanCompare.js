import { buildInvestigationFindings } from "./findingsModel.js";

function fingerprint(finding) {
  const hash = (finding.hashes ?? [])[0];
  if (hash) return `hash:${String(hash).toLowerCase()}`;
  const loc = String(finding.location || "").toLowerCase();
  if (loc) return `loc:${loc}|${finding.category}`;
  return `id:${finding.id}`;
}

function changeKey(finding) {
  return [
    finding.severity,
    finding.confidenceTier,
    finding.status,
    finding.title,
  ].join("|");
}

/**
 * Diff two reports by normalized investigation findings.
 * @returns {{ added: object[], removed: object[], changed: object[], summary: object }}
 */
export function compareSessions(prevReport, currReport, prevSummary = null, currSummary = null) {
  const prev = buildInvestigationFindings(prevReport ?? {}, prevSummary);
  const curr = buildInvestigationFindings(currReport ?? {}, currSummary);

  const prevMap = new Map(prev.map((f) => [fingerprint(f), f]));
  const currMap = new Map(curr.map((f) => [fingerprint(f), f]));

  const added = [];
  const removed = [];
  const changed = [];

  for (const [key, finding] of currMap) {
    if (!prevMap.has(key)) {
      added.push(finding);
      continue;
    }
    const before = prevMap.get(key);
    if (changeKey(before) !== changeKey(finding)) {
      changed.push({ previous: before, current: finding });
    }
  }

  for (const [key, finding] of prevMap) {
    if (!currMap.has(key)) removed.push(finding);
  }

  return {
    added,
    removed,
    changed,
    summary: {
      previousCount: prev.length,
      currentCount: curr.length,
      addedCount: added.length,
      removedCount: removed.length,
      changedCount: changed.length,
      netDelta: curr.length - prev.length,
    },
  };
}
