import { scanReviewFromReport } from "./reportDigest.js";
import { formatDisplayLocation, privacyPath, publicFindingLabels } from "./resultPrivacy.js";
import {
  genericFindingTitle,
  genericReasonDetail,
  genericReasonLabel,
  reviewerSafeText,
} from "./reviewerCopy.js";

const SEVERITY_RANK = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
const CONFIDENCE_RANK = { high: 0, medium: 1, low: 2 };
const STATUS_RANK = { confirmed: 0, suspicious: 1, inconclusive: 2, informational: 3 };

function pathBasename(path) {
  const key = String(path || "").replace(/\//g, "\\");
  const i = key.lastIndexOf("\\");
  return i >= 0 ? key.slice(i + 1) : key;
}

function stableId(parts) {
  return parts
    .map((part) =>
      String(part ?? "")
        .toLowerCase()
        .replace(/[^a-z0-9._-]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .slice(0, 64),
    )
    .filter(Boolean)
    .join("|");
}

function normalizeSeverity(value) {
  const key = String(value || "").toLowerCase();
  if (key === "critical" || key === "high" || key === "medium" || key === "low") return key;
  if (key === "info" || key === "informational") return "low";
  return "medium";
}

function normalizeConfidenceTier(tier, numeric) {
  const raw = String(tier || "").toLowerCase();
  if (raw === "high" || raw === "medium" || raw === "low") return raw;
  const n = Number(numeric);
  if (Number.isFinite(n)) {
    if (n >= 0.82) return "high";
    if (n >= 0.55) return "medium";
    return "low";
  }
  return "medium";
}

function normalizeConfidence(value) {
  const n = Number(value);
  if (Number.isFinite(n)) {
    if (n > 1) return Math.max(0, Math.min(1, n / 100));
    return Math.max(0, Math.min(1, n));
  }
  return null;
}

function severityFromConfidenceTier(tier) {
  if (tier === "high") return "high";
  if (tier === "low") return "low";
  return "medium";
}

function statusFromSignals({ severity, confidenceTier, removed, confirmedHash }) {
  if (confirmedHash) {
    return "confirmed";
  }
  if (confidenceTier === "high" || severity === "high" || severity === "critical") {
    return "suspicious";
  }
  if (removed && confidenceTier !== "low") return "suspicious";
  if (confidenceTier === "low" || severity === "low") return "inconclusive";
  if (severity === "medium" || confidenceTier === "medium") return "suspicious";
  return "informational";
}

function evidenceFromHit(hit) {
  const items = [];
  const path = hit.path || hit.target_path || hit.file_path;
  if (path) {
    items.push({
      kind: "path",
      label: "Location",
      value: privacyPath(path),
      raw: path,
    });
  }
  if (hit.artifact_source) {
    items.push({
      kind: "source",
      label: "Source",
      value: String(hit.artifact_source),
    });
  }
  if (hit.sha256) {
    items.push({
      kind: "hash",
      label: "SHA-256",
      value: String(hit.sha256),
    });
  }
  if (hit.note) {
    const safe = reviewerSafeText(hit.note) || genericReasonDetail("Executor artifact evidence", hit.note);
    items.push({ kind: "note", label: "Note", value: safe });
  }
  if (hit.file_exists === false || hit.removed_artifact) {
    items.push({
      kind: "state",
      label: "Disk state",
      value: "Removed from disk; system traces remain",
    });
  }
  return items;
}

function findingShell(partial) {
  const confidence = normalizeConfidence(partial.confidence);
  const confidenceTier = normalizeConfidenceTier(partial.confidenceTier, confidence);
  const severity = normalizeSeverity(partial.severity || severityFromConfidenceTier(confidenceTier));
  const status =
    partial.status ||
    statusFromSignals({
      severity,
      confidenceTier,
      removed: partial.removed,
      confirmedHash: partial.confirmedHash,
    });

  return {
    id: partial.id,
    title: partial.title || "Investigation finding",
    category: partial.category || "general",
    severity,
    confidence,
    confidenceTier,
    indicatorStrength: partial.indicatorStrength ?? partial.evidence_strength ?? null,
    detectionMethod: partial.detectionMethod || "scan",
    whyFlagged: partial.whyFlagged || "A warning sign was recorded on this scan.",
    evidence: Array.isArray(partial.evidence) ? partial.evidence : [],
    location: partial.location || null,
    timestamp: partial.timestamp || null,
    hashes: Array.isArray(partial.hashes) ? partial.hashes.filter(Boolean) : [],
    relatedIds: Array.isArray(partial.relatedIds) ? partial.relatedIds : [],
    recommendedAction: partial.recommendedAction || defaultAction(status, severity),
    status,
  };
}

function defaultAction(status, severity) {
  if (status === "confirmed" || severity === "critical" || severity === "high") {
    return "Preserve evidence, verify the path and hashes, and treat as a serious indicator pending human review.";
  }
  if (status === "suspicious") {
    return "Cross-check related traces and timeline events before drawing a conclusion.";
  }
  if (status === "inconclusive") {
    return "Note as weak signal only; do not treat as proof without corroboration.";
  }
  return "Record for context; no immediate escalation required.";
}

function fromArtifactHits(sec) {
  const hits = sec.executor_artifact_evidence?.hits ?? [];
  return hits.map((hit, index) => {
    const labels = publicFindingLabels([
      ...(hit.executor_name_hits ?? []),
      ...(hit.cheat_filename_hints ?? []).map((h) => `cheat:${h}`),
    ]);
    const path = hit.path || "";
    const title =
      labels[0] ||
      genericFindingTitle(pathBasename(path) || hit.note || "Artifact evidence");
    const confidenceTier = normalizeConfidenceTier(hit.confidence_tier, hit.confidence);
    const confirmedHash =
      hit.artifact_source === "sha256_blocklist" ||
      (Array.isArray(hit.reasons) && hit.reasons.some((reason) => String(reason).startsWith("sha256_blocklist:")));
    return findingShell({
      id: stableId(["artifact", hit.artifact_source, path, hit.sha256, index]),
      title,
      category: "artifact",
      severity: confirmedHash ? "high" : severityFromConfidenceTier(confidenceTier),
      confidence: hit.confidence,
      confidenceTier,
      indicatorStrength: hit.evidence_strength ?? hit.source_reliability ?? null,
      detectionMethod: hit.artifact_source || "executor_artifact",
      whyFlagged:
        reviewerSafeText(hit.note) ||
        (hit.file_exists === false
          ? "System traces reference this program even though it is no longer on disk."
          : "Matched a reviewed artifact pattern on this device."),
      evidence: evidenceFromHit(hit),
      location: formatDisplayLocation(hit) || privacyPath(path),
      timestamp: hit.display_at || hit.modified || hit.file_modified || null,
      hashes: hit.sha256 ? [hit.sha256] : [],
      removed: hit.file_exists === false || hit.removed_artifact,
      confirmedHash,
      recommendedAction: confirmedHash
        ? "Confirm the hash match against the watch list and document chain of custody."
        : undefined,
    });
  });
}

function fromBypassFindings(sec) {
  const findings = sec.bypass_resilience?.findings ?? [];
  return findings.map((row, index) =>
    findingShell({
      id: stableId(["bypass", row.category, row.title, index]),
      title: genericFindingTitle(row.title),
      category: row.category || "bypass",
      severity: normalizeSeverity(row.severity),
      confidence: row.severity === "high" ? 0.78 : row.severity === "low" ? 0.45 : 0.62,
      confidenceTier: row.severity === "high" ? "high" : row.severity === "low" ? "low" : "medium",
      detectionMethod: "bypass_resilience",
      whyFlagged: genericReasonDetail(row.title, row.detail),
      evidence: row.detail
        ? [{ kind: "note", label: "Detail", value: genericReasonDetail(row.title, row.detail) }]
        : [],
      status: row.severity === "high" ? "suspicious" : "inconclusive",
      recommendedAction: "Investigate whether logging or cleanup tools were used to hide activity.",
    }),
  );
}

function fromProvenanceChains(sec, review) {
  const verdictChains = sec.evidence_verdict?.provenance_chains ?? [];
  const reviewChains = review.evidence_chains?.chains ?? [];
  const chains = verdictChains.length ? verdictChains : reviewChains;
  return chains.map((chain, index) => {
    const labels = publicFindingLabels(chain.labels ?? []);
    const title = labels[0] || genericFindingTitle(chain.stem) || "Corroborated traces";
    const confidenceTier = normalizeConfidenceTier(chain.confidence_tier || chain.confidence, chain.confidence);
    const steps = chain.steps ?? [];
    return findingShell({
      id: stableId(["chain", chain.stem, index]),
      title,
      category: "provenance",
      severity: confidenceTier === "high" ? "high" : "medium",
      confidence: chain.confidence,
      confidenceTier,
      detectionMethod: "provenance_chain",
      whyFlagged:
        reviewerSafeText(chain.summary) ||
        "Multiple independent sources agree on related activity.",
      evidence: steps.slice(0, 8).map((step, stepIndex) => ({
        kind: "step",
        label: step.action || step.source || `Step ${stepIndex + 1}`,
        value: reviewerSafeText(step.detail || step.summary) || privacyPath(step.path) || "Related trace",
        timestamp: step.occurred_at || null,
      })),
      location: steps[0] ? privacyPath(steps[0].path) : null,
      timestamp: steps.find((s) => s.occurred_at)?.occurred_at || null,
      relatedIds: [],
      status: confidenceTier === "high" ? "confirmed" : "suspicious",
      recommendedAction: "Review each corroborating source before treating as conclusive.",
    });
  });
}

function fromScanReview(review) {
  const out = [];
  for (const row of review.executable_inventory?.items ?? []) {
    if (!row.suspicious && !(row.labels ?? []).length) continue;
    const labels = publicFindingLabels(row.labels ?? []);
    out.push(
      findingShell({
        id: stableId(["inventory", row.path, row.name]),
        title: labels[0] || row.name || "Flagged program",
        category: "inventory",
        severity: row.file_exists === false ? "high" : "medium",
        confidence: row.file_exists === false ? 0.72 : 0.58,
        confidenceTier: row.file_exists === false ? "high" : "medium",
        detectionMethod: "executable_inventory",
        whyFlagged: row.trace_note || "Flagged from system activity records.",
        evidence: [
          {
            kind: "path",
            label: "Location",
            value: formatDisplayLocation(row) || row.name,
          },
          ...(labels.length
            ? [{ kind: "label", label: "Indicators", value: labels.join(", ") }]
            : []),
        ],
        location: formatDisplayLocation(row),
        timestamp: row.last_seen || null,
        removed: row.file_exists === false,
        status: row.file_exists === false ? "suspicious" : "suspicious",
      }),
    );
  }

  for (const row of review.download_history?.items ?? []) {
    if (!row.suspicious && !(row.matched_labels ?? []).length) continue;
    const labels = publicFindingLabels(row.matched_labels ?? []);
    out.push(
      findingShell({
        id: stableId(["download", row.target_path, row.file_name, row.started_at]),
        title: row.file_name || "Flagged download",
        category: "download",
        severity: "medium",
        confidence: 0.55,
        confidenceTier: "medium",
        detectionMethod: "browser_download",
        whyFlagged: labels.length
          ? `Download matched: ${labels.join(", ")}`
          : "Browser download matched review criteria.",
        evidence: [
          {
            kind: "path",
            label: "Location",
            value: formatDisplayLocation(row) || row.file_name,
          },
          row.browser
            ? { kind: "meta", label: "Browser", value: String(row.browser) }
            : null,
        ].filter(Boolean),
        location: formatDisplayLocation(row),
        timestamp: row.started_at || null,
        status: "suspicious",
      }),
    );
  }
  return out;
}

function fromSummaryReasons(summary) {
  return (summary?.reasons ?? [])
    .filter((reason) => reason.points > 0)
    .filter((reason) => reason.label !== "Unified evidence verdict")
    .map((reason, index) =>
      findingShell({
        id: stableId(["score", reason.label, index]),
        title: genericReasonLabel(reason.label),
        category: "score",
        severity: reason.points >= 20 ? "high" : reason.points >= 10 ? "medium" : "low",
        confidence: Math.min(0.9, 0.35 + reason.points / 100),
        confidenceTier: reason.points >= 20 ? "high" : reason.points >= 10 ? "medium" : "low",
        detectionMethod: "score_model",
        whyFlagged: genericReasonDetail(reason.label, reason.detail),
        evidence: [
          {
            kind: "note",
            label: "Score contribution",
            value: `${reason.points} point(s)`,
          },
        ],
        status: reason.points >= 20 ? "suspicious" : "informational",
      }),
    );
}

function fromEvidenceVerdict(sec) {
  const verdict = sec.evidence_verdict;
  if (!verdict?.available) return [];
  const out = [];
  for (const reason of verdict.runtime_reasons ?? []) {
    out.push(
      findingShell({
        id: stableId(["runtime", reason]),
        title: genericFindingTitle(reason),
        category: "runtime",
        severity: "high",
        confidence: 0.8,
        confidenceTier: "high",
        detectionMethod: "roblox_runtime",
        whyFlagged: reviewerSafeText(reason) || "Runtime provenance signal detected.",
        evidence: [{ kind: "note", label: "Signal", value: reviewerSafeText(reason) || reason }],
        status: "suspicious",
        recommendedAction: "Confirm runtime signals against process and module inventory.",
      }),
    );
  }
  if (verdict.scan_complete === false) {
    out.push(
      findingShell({
        id: "verdict|scan-incomplete",
        title: "Scan ended incomplete",
        category: "methodology",
        severity: "medium",
        confidence: 0.9,
        confidenceTier: "high",
        detectionMethod: "scan_budget",
        whyFlagged: "The scanner hit a time budget; treat weaker signals as inconclusive.",
        evidence: [],
        status: "inconclusive",
        recommendedAction: "Re-run the scan if a definitive review is required.",
      }),
    );
  }
  return out;
}

/** Normalize any report into InvestigationFinding objects. */
export function buildInvestigationFindings(report, summary = null) {
  const bundle = report?.findings_bundle;
  if (bundle?.available && Array.isArray(bundle.findings) && bundle.findings.length) {
    const mapped = bundle.findings.map((finding, index) => {
      const severity = normalizeSeverity(finding.severity);
      const confidenceTier = normalizeConfidenceTier(
        finding.confidence_tier || finding.confidenceTier,
        finding.confidence,
      );
      const confidence = normalizeConfidence(finding.confidence);
      const confirmedHash =
        finding.detection_method === "sha256_blocklist" && Boolean(finding.hashes?.sha256 || finding.sha256);
      return {
        id: finding.id || stableId(["bundle", finding.location || finding.title, index]),
        title: finding.title || "Indicator",
        category: finding.category || "executor_artifact",
        severity,
        confidence,
        confidenceTier,
        status:
          finding.indicator_strength === "confirmed" || finding.status === "confirmed"
            ? "confirmed"
            : statusFromSignals({
                severity,
                confidenceTier,
                removed: Boolean(finding.metadata?.removed_artifact),
                confirmedHash,
              }),
        detectionMethod: finding.detection_method || finding.detectionMethod || "",
        why: finding.why_flagged || finding.why || "",
        recommendedAction: finding.recommended_action || finding.recommendedAction || "",
        location: finding.location || "",
        timestamp: finding.timestamp || "",
        evidence: Array.isArray(finding.evidence) ? finding.evidence : [],
        relatedIds: Array.isArray(finding.related_ids) ? finding.related_ids : [],
        hashes: finding.hashes || {},
        indicatorStrength: finding.indicator_strength || null,
        source: "findings_bundle",
      };
    });
    return sortFindings(mapped, "severity");
  }

  const sec = report?.security_integrity_signals ?? {};
  const review = scanReviewFromReport(report ?? {});
  const raw = [
    ...fromArtifactHits(sec),
    ...fromBypassFindings(sec),
    ...fromProvenanceChains(sec, review),
    ...fromScanReview(review),
    ...fromEvidenceVerdict(sec),
    ...fromSummaryReasons(summary),
  ];

  const byId = new Map();
  for (const finding of raw) {
    if (!finding?.id) continue;
    if (!byId.has(finding.id)) byId.set(finding.id, finding);
  }

  const findings = [...byId.values()];
  const groups = groupRelatedFindings(findings);
  for (const group of groups) {
    if (group.length < 2) continue;
    const ids = group.map((f) => f.id);
    for (const finding of group) {
      finding.relatedIds = ids.filter((id) => id !== finding.id);
    }
  }

  return sortFindings(findings, "severity");
}

export function filterFindings(findings, filters = {}) {
  const q = String(filters.query || filters.q || "").trim().toLowerCase();
  const severities = normalizeFilterSet(filters.severity || filters.severities);
  const confidences = normalizeFilterSet(filters.confidence || filters.confidenceTiers);
  const categories = normalizeFilterSet(filters.category || filters.categories);
  const statuses = normalizeFilterSet(filters.status || filters.statuses);

  return (findings ?? []).filter((finding) => {
    if (severities && !severities.has(finding.severity)) return false;
    if (confidences && !confidences.has(finding.confidenceTier)) return false;
    if (categories && !categories.has(finding.category)) return false;
    if (statuses && !statuses.has(finding.status)) return false;
    if (!q) return true;
    const hay = [
      finding.title,
      finding.category,
      finding.whyFlagged,
      finding.location,
      finding.detectionMethod,
      finding.status,
      ...(finding.hashes ?? []),
      ...(finding.evidence ?? []).map((e) => `${e.label} ${e.value}`),
    ]
      .join(" ")
      .toLowerCase();
    return hay.includes(q);
  });
}

function normalizeFilterSet(value) {
  if (!value) return null;
  const list = Array.isArray(value) ? value : String(value).split(",");
  const set = new Set(list.map((v) => String(v).trim().toLowerCase()).filter(Boolean));
  return set.size ? set : null;
}

export function sortFindings(findings, sortKey = "severity") {
  const key = String(sortKey || "severity");
  const list = [...(findings ?? [])];
  list.sort((a, b) => {
    if (key === "confidence") {
      const tier = (CONFIDENCE_RANK[a.confidenceTier] ?? 9) - (CONFIDENCE_RANK[b.confidenceTier] ?? 9);
      if (tier) return tier;
      return (b.confidence ?? 0) - (a.confidence ?? 0);
    }
    if (key === "time" || key === "timestamp") {
      return tsMs(b.timestamp) - tsMs(a.timestamp);
    }
    if (key === "title") {
      return String(a.title).localeCompare(String(b.title));
    }
    if (key === "status") {
      return (STATUS_RANK[a.status] ?? 9) - (STATUS_RANK[b.status] ?? 9);
    }
    if (key === "category") {
      return String(a.category).localeCompare(String(b.category));
    }
    const sev = (SEVERITY_RANK[a.severity] ?? 9) - (SEVERITY_RANK[b.severity] ?? 9);
    if (sev) return sev;
    const conf = (CONFIDENCE_RANK[a.confidenceTier] ?? 9) - (CONFIDENCE_RANK[b.confidenceTier] ?? 9);
    if (conf) return conf;
    return String(a.title).localeCompare(String(b.title));
  });
  return list;
}

function tsMs(value) {
  if (!value) return 0;
  const ms = Date.parse(String(value));
  return Number.isNaN(ms) ? 0 : ms;
}

function relatedKey(finding) {
  const hash = (finding.hashes ?? [])[0];
  if (hash) return `hash:${String(hash).toLowerCase()}`;
  const loc = String(finding.location || "")
    .toLowerCase()
    .replace(/\.[^.\\/]+$/, "");
  if (loc) return `loc:${loc}`;
  const base = pathBasename(finding.location || finding.title || "").toLowerCase();
  if (base) return `name:${base.replace(/\.[^.]+$/, "")}`;
  return `id:${finding.id}`;
}

export function groupRelatedFindings(findings) {
  const buckets = new Map();
  for (const finding of findings ?? []) {
    const key = relatedKey(finding);
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(finding);
  }
  return [...buckets.values()];
}

export function severityCounts(findings) {
  const counts = {
    total: 0,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    confirmed: 0,
    suspicious: 0,
    informational: 0,
    inconclusive: 0,
    confidenceHigh: 0,
    confidenceMedium: 0,
    confidenceLow: 0,
  };
  for (const finding of findings ?? []) {
    counts.total += 1;
    if (counts[finding.severity] != null) counts[finding.severity] += 1;
    if (counts[finding.status] != null) counts[finding.status] += 1;
    if (finding.confidenceTier === "high") counts.confidenceHigh += 1;
    else if (finding.confidenceTier === "medium") counts.confidenceMedium += 1;
    else counts.confidenceLow += 1;
  }
  return counts;
}

export function engineVerdictPlain(report, summary = null) {
  const verdict = report?.security_integrity_signals?.evidence_verdict;
  if (verdict?.available && verdict.verdict) {
    const map = {
      likely_executor_activity: {
        tone: "bad",
        label: "Likely suspicious program activity",
        blurb: "Strong artifact and/or runtime signals align. Review findings carefully.",
      },
      suspicious_activity: {
        tone: "watch",
        label: "Suspicious activity indicated",
        blurb: "Multiple warning signs need human review before a final call.",
      },
      inconclusive_or_weak_signals: {
        tone: "watch",
        label: "Weak or inconclusive signals",
        blurb: "Indicators exist but do not meet a high-confidence standard alone.",
      },
      no_substantiated_executor_activity: {
        tone: "clean",
        label: "No substantiated activity",
        blurb: "Nothing on this scan met the evidence threshold for a serious finding.",
      },
    };
    const key = String(verdict.verdict).replace(/_scan_incomplete$/, "");
    const meta = map[key] || {
      tone: "watch",
      label: "Engine verdict available",
      blurb: verdict.note || "Review severity and confidence separately.",
    };
    return {
      ...meta,
      engineScore: Number(verdict.score) || 0,
      scanComplete: verdict.scan_complete !== false,
      incomplete: String(verdict.verdict).includes("scan_incomplete") || verdict.scan_complete === false,
      raw: verdict.verdict,
      note: verdict.note || null,
    };
  }

  const score = Number(summary?.score) || 0;
  if (score >= 70) {
    return {
      tone: "bad",
      label: "Elevated concern",
      blurb: "Score model shows elevated risk. Inspect high-severity findings first.",
      engineScore: score,
      scanComplete: true,
      incomplete: false,
      raw: null,
      note: null,
    };
  }
  if (score >= 35) {
    return {
      tone: "watch",
      label: "Review recommended",
      blurb: "Some indicators warrant a closer look. Severity and confidence are shown separately.",
      engineScore: score,
      scanComplete: true,
      incomplete: false,
      raw: null,
      note: null,
    };
  }
  return {
    tone: "clean",
    label: "Looks clear",
    blurb: "No major indicators stood out. Absence of evidence is not proof of innocence.",
    engineScore: score,
    scanComplete: true,
    incomplete: false,
    raw: null,
    note: null,
  };
}

export const METHODOLOGY_BLURB =
  "Findings combine artifact reliability, corroboration across Windows trace layers, runtime provenance when available, and tamper/cover-up signals. Severity describes impact; confidence describes how strongly the evidence supports the indicator. Indicators assist human review and are not automatic proof of guilt.";
