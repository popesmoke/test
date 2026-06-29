"""Evidence reliability tiers and probabilistic confidence scoring for scan hits."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

# Source reliability: how much we trust the artifact class alone (0–1).
ARTIFACT_SOURCE_RELIABILITY: dict[str, float] = {
    "sha256_blocklist": 0.95,
    "live_process": 0.92,
    "live_injected_module": 0.94,
    "bam_execution_binary": 0.90,
    "bam_execution": 0.88,
    "dam_execution": 0.88,
    "amcache_hive": 0.80,
    "srum_database": 0.74,
    "srum_database_path": 0.76,
    "temp_directory": 0.52,
    "browser_cache": 0.36,
    "prefetch_execution": 0.72,
    "pca_compat": 0.68,
    "usn_journal": 0.66,
    "recycle_bin": 0.64,
    "recycle_bin_content": 0.64,
    "shimcache": 0.62,
    "userassist": 0.60,
    "recent_lnk": 0.58,
    "registry_uninstall": 0.56,
    "scheduled_task": 0.55,
    "ifeo_hijack": 0.85,
    "roblox_protocol_registry": 0.82,
    "roblox_autoexec_folder": 0.78,
    "roblox_log": 0.58,
    "roblox_log_rbxasset": 0.72,
    "wer_crash_dump": 0.50,
    "defender_history": 0.58,
    "application_event_log": 0.48,
    "registry_shell": 0.46,
    "mui_cache": 0.44,
    "persistence": 0.54,
    "browser_download": 0.38,
    "browser_history_domain": 0.15,
    "full_pc_filesystem": 0.42,
    "filesystem_indicator": 0.35,
    "profile_binary_sweep": 0.40,
    "known_install_path": 0.48,
    "removed_artifact": 0.70,
}

NAME_ONLY_SOURCES = frozenset(
    {
        "browser_history_domain",
        "filesystem_indicator",
        "full_pc_filesystem",
        "profile_binary_sweep",
        "roblox_log",
    }
)

STRONG_EVIDENCE_SOURCES = frozenset(
    {
        "sha256_blocklist",
        "live_process",
        "live_injected_module",
        "bam_execution",
        "bam_execution_binary",
        "dam_execution",
        "prefetch_execution",
        "amcache_hive",
    }
)

RELIABILITY_CLASS_BY_SOURCE: dict[str, str] = {
    "sha256_blocklist": "strong",
    "live_process": "strong",
    "live_injected_module": "strong",
    "bam_execution": "strong",
    "bam_execution_binary": "strong",
    "dam_execution": "strong",
    "amcache_hive": "strong",
    "srum_database": "medium",
    "srum_database_path": "medium",
    "temp_directory": "medium",
    "browser_cache": "weak",
    "prefetch_execution": "medium",
    "browser_history_domain": "contextual",
    "browser_download": "weak",
    "filesystem_indicator": "weak",
}


def _path_key(path: str) -> str:
    return str(path or "").replace("/", "\\").lower().strip()


def _basename_key(path: str) -> str:
    key = _path_key(path)
    slash = key.rfind("\\")
    return key[slash + 1 :] if slash >= 0 else key


def _stem_key(path: str) -> str:
    base = _basename_key(path)
    dot = base.rfind(".")
    return base[:dot] if dot > 0 else base


def artifact_source_reliability(source: str) -> float:
    return ARTIFACT_SOURCE_RELIABILITY.get(str(source or ""), 0.40)


def reliability_class_for_source(source: str) -> str:
    return RELIABILITY_CLASS_BY_SOURCE.get(str(source or ""), "medium")


def _confidence_tier(score: float) -> str:
    if score >= 0.82:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _recency_factor(iso_ts: str | None, *, now: datetime | None = None) -> float:
    if not iso_ts:
        return 0.85
    now = now or datetime.now(timezone.utc)
    try:
        ts = datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        hours = max(0.0, (now - ts).total_seconds() / 3600.0)
    except ValueError:
        return 0.85
    if hours <= 72:
        return 1.0
    if hours <= 168:
        return 0.88
    if hours <= 720:
        return 0.72
    return 0.55


def compute_hit_confidence(
    hit: dict[str, Any],
    *,
    corroboration_count: int = 1,
    tamper_risk: float = 0.0,
) -> dict[str, Any]:
    source = str(hit.get("artifact_source") or "")
    base = artifact_source_reliability(source)
    labels = list(hit.get("executor_name_hits") or [])
    cheat_hints = list(hit.get("cheat_filename_hints") or [])
    reasons = list(hit.get("reasons") or [])

    strength = base
    if hit.get("sha256") or "sha256_blocklist" in str(hit.get("note") or ""):
        strength = max(strength, 0.95)
    if hit.get("authenticode_status") == "Valid":
        strength = min(strength, max(0.35, strength * 0.75))
    elif hit.get("authenticode_status") in {"NotSigned", "NotTrusted", "HashMismatch"}:
        strength = max(strength, 0.62)
    if source in NAME_ONLY_SOURCES and not hit.get("sha256"):
        strength = min(strength, 0.42)
    if labels and source in NAME_ONLY_SOURCES:
        strength = min(strength, 0.38)
    if cheat_hints and not labels:
        strength = min(strength, 0.48)
    if hit.get("removed_artifact") or hit.get("file_exists") is False:
        strength = max(strength, min(0.92, strength + 0.08))

    for reason in reasons:
        if reason.startswith("sha256_blocklist:"):
            strength = max(strength, 0.94)
        elif reason in {"module_from_high_risk_folder", "unsigned_module_in_roblox"}:
            strength = max(strength, 0.78)
        elif reason == "executor_name_in_module":
            strength = max(strength, 0.58)

    corroboration_boost = min(0.22, max(0.0, (corroboration_count - 1) * 0.07))
    recency = _recency_factor(hit.get("display_at") or hit.get("modified"))
    tamper_penalty = min(0.25, max(0.0, tamper_risk))

    confidence = max(0.05, min(0.99, (strength * recency) + corroboration_boost - tamper_penalty))
    tier = _confidence_tier(confidence)
    return {
        "confidence": round(confidence, 3),
        "confidence_tier": tier,
        "reliability_class": reliability_class_for_source(source),
        "source_reliability": round(base, 3),
        "corroboration_count": int(max(1, corroboration_count)),
        "recency_factor": round(recency, 3),
        "evidence_strength": round(strength, 3),
    }


def _index_corroboration(hits: list[dict[str, Any]]) -> dict[str, int]:
    by_path: dict[str, set[str]] = {}
    by_stem: dict[str, set[str]] = {}
    for hit in hits:
        source = str(hit.get("artifact_source") or "")
        path = _path_key(str(hit.get("path") or ""))
        stem = _stem_key(str(hit.get("path") or ""))
        if path:
            by_path.setdefault(path, set()).add(source)
        if stem and len(stem) >= 4:
            by_stem.setdefault(stem, set()).add(source)
    counts: dict[str, int] = {}
    for hit in hits:
        path = _path_key(str(hit.get("path") or ""))
        stem = _stem_key(str(hit.get("path") or ""))
        sources: set[str] = set()
        if path:
            sources |= by_path.get(path, set())
        if stem:
            sources |= by_stem.get(stem, set())
        counts[id(hit)] = max(1, len(sources))
    return counts


def enrich_executor_artifact_evidence(
    bundle: dict[str, Any],
    *,
    tamper_risk: float = 0.0,
) -> dict[str, Any]:
    if not bundle.get("available"):
        return bundle
    hits = list(bundle.get("hits") or [])
    if not hits:
        bundle["confidence_engine_version"] = 2
        return bundle

    corroboration = _index_corroboration(hits)
    enriched: list[dict[str, Any]] = []
    for hit in hits:
        row = dict(hit)
        meta = compute_hit_confidence(
            row,
            corroboration_count=corroboration.get(id(hit), 1),
            tamper_risk=tamper_risk,
        )
        row.update(meta)
        enriched.append(row)

    enriched.sort(
        key=lambda row: (
            0 if row.get("confidence_tier") == "high" else 1 if row.get("confidence_tier") == "medium" else 2,
            -(float(row.get("confidence") or 0)),
        )
    )
    bundle["hits"] = enriched
    bundle["high_confidence_hits"] = sum(1 for row in enriched if row.get("confidence_tier") == "high")
    bundle["medium_confidence_hits"] = sum(1 for row in enriched if row.get("confidence_tier") == "medium")
    bundle["confidence_engine_version"] = 2
    return bundle


def build_provenance_chains(
    hits: list[dict[str, Any]],
    *,
    cross_signals: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Group multi-source evidence into reviewer-facing provenance chains."""
    groups: dict[str, dict[str, Any]] = {}
    for hit in hits:
        stem = _stem_key(str(hit.get("path") or ""))
        if not stem or len(stem) < 3:
            continue
        key = stem
        group = groups.setdefault(
            key,
            {
                "stem": stem.upper(),
                "labels": set(),
                "sources": set(),
                "steps": [],
                "max_confidence": 0.0,
                "paths": set(),
            },
        )
        for label in hit.get("executor_name_hits") or []:
            group["labels"].add(str(label))
        source = str(hit.get("artifact_source") or "")
        if source:
            group["sources"].add(source)
        path = str(hit.get("path") or "")
        if path:
            group["paths"].add(path[:520])
        group["max_confidence"] = max(group["max_confidence"], float(hit.get("confidence") or 0))
        group["steps"].append(
            {
                "action": "removed_trace" if hit.get("removed_artifact") else "artifact_hit",
                "source": source,
                "confidence": hit.get("confidence"),
                "confidence_tier": hit.get("confidence_tier"),
                "occurred_at": hit.get("display_at") or hit.get("modified"),
                "path": path[:520] if path else None,
            }
        )

    for signal in cross_signals or []:
        path = str(signal.get("path") or "")
        stem = _stem_key(path)
        if not stem or stem not in groups:
            continue
        groups[stem]["steps"].append(
            {
                "action": str(signal.get("type") or "correlation"),
                "source": "cross_artifact_correlation",
                "confidence": 0.85 if signal.get("severity") == "high" else 0.65,
                "occurred_at": signal.get("occurred_at"),
                "summary": signal.get("summary"),
            }
        )

    chains: list[dict[str, Any]] = []
    for stem, group in groups.items():
        unique_sources = sorted(group["sources"])
        if len(unique_sources) < 2 and group["max_confidence"] < 0.72:
            continue
        confidence = min(
            0.99,
            group["max_confidence"] + min(0.18, (len(unique_sources) - 1) * 0.06),
        )
        chains.append(
            {
                "stem": group["stem"],
                "labels": sorted(group["labels"]),
                "corroborating_sources": unique_sources,
                "corroboration_count": len(unique_sources),
                "confidence": round(confidence, 3),
                "confidence_tier": _confidence_tier(confidence),
                "steps": group["steps"][:12],
                "summary": (
                    f"{', '.join(sorted(group['labels'])[:3]) or 'Flagged program'} — "
                    f"{len(unique_sources)} independent source(s); "
                    f"confidence {int(confidence * 100)}%."
                ),
            }
        )

    chains.sort(key=lambda row: (-float(row.get("confidence") or 0), -len(row.get("steps") or [])))
    return chains[:40]


def build_evidence_verdict(
    *,
    executor_artifact_evidence: dict[str, Any] | None,
    roblox_runtime: dict[str, Any] | None,
    bypass_resilience: dict[str, Any] | None,
    cross_artifact: dict[str, Any] | None,
    scan_budget: dict[str, Any] | None,
    filesystem_integrity: dict[str, Any] | None,
) -> dict[str, Any]:
    hits = list((executor_artifact_evidence or {}).get("hits") or [])
    runtime = roblox_runtime or {}
    bypass = bypass_resilience or {}
    budget = scan_budget or {}
    integrity = filesystem_integrity or {}

    tamper_risk = 0.0
    if bypass.get("available") and (bypass.get("findings") or []):
        tamper_risk = min(0.35, (float(bypass.get("risk_score") or 0) / 100.0) * 0.35)
    recon = str(integrity.get("reconstruction_confidence") or "normal").lower()
    if recon in {"reduced", "severely_limited"}:
        tamper_risk = max(tamper_risk, 0.12 if recon == "reduced" else 0.22)

    high_hits = [h for h in hits if h.get("confidence_tier") == "high"]
    medium_hits = [h for h in hits if h.get("confidence_tier") == "medium"]
    strong_sources = {
        str(h.get("artifact_source") or "")
        for h in hits
        if str(h.get("artifact_source") or "") in STRONG_EVIDENCE_SOURCES
    }

    runtime_score = 0.0
    runtime_reasons: list[str] = []
    if runtime.get("available"):
        if runtime.get("suspicious_memory_regions"):
            runtime_score += 28
            runtime_reasons.append("Suspicious executable private memory in Roblox.")
        if runtime.get("module_trust_failures"):
            runtime_score += 22
            runtime_reasons.append("Unsigned/untrusted modules loaded into Roblox.")
        if runtime.get("external_process_handles"):
            runtime_score += 30
            runtime_reasons.append("External process(es) hold high-risk access to Roblox.")
        if runtime.get("suspicious_drivers"):
            runtime_score += 18
            runtime_reasons.append("Non-Microsoft or suspicious kernel drivers present.")
        if runtime.get("launch_provenance_anomaly"):
            runtime_score += 12
            runtime_reasons.append("Roblox launch chain looks unusual.")

    artifact_score = min(70, len(high_hits) * 14 + len(medium_hits) * 5)
    corroboration_bonus = min(15, len(strong_sources) * 3)
    bypass_penalty = min(12, int(float(bypass.get("risk_score") or 0) * 0.08))

    score = max(0, min(100, artifact_score + runtime_score + corroboration_bonus - bypass_penalty))
    if budget.get("deadline_exceeded"):
        score = min(score, 72)
    if recon == "severely_limited":
        score = min(score, 65)

    if score >= 78 and (high_hits or runtime_score >= 22):
        verdict = "likely_executor_activity"
    elif score >= 52 and (medium_hits or runtime_score >= 12):
        verdict = "suspicious_activity"
    elif score >= 28:
        verdict = "inconclusive_or_weak_signals"
    else:
        verdict = "no_substantiated_executor_activity"

    if budget.get("deadline_exceeded") or recon == "severely_limited":
        verdict = f"{verdict}_scan_incomplete"

    chains = build_provenance_chains(
        hits,
        cross_signals=list((cross_artifact or {}).get("signals") or []),
    )

    return {
        "available": True,
        "engine_version": 2,
        "score": int(score),
        "verdict": verdict,
        "high_confidence_hit_count": len(high_hits),
        "medium_confidence_hit_count": len(medium_hits),
        "strong_source_count": len(strong_sources),
        "runtime_signal_count": sum(
            1
            for key in (
                "suspicious_memory_regions",
                "module_trust_failures",
                "external_process_handles",
                "suspicious_drivers",
                "launch_provenance_anomaly",
            )
            if runtime.get(key)
        ),
        "tamper_risk": round(tamper_risk, 3),
        "scan_complete": not bool(budget.get("deadline_exceeded")),
        "reconstruction_confidence": recon,
        "runtime_reasons": runtime_reasons,
        "provenance_chains": chains,
        "note": (
            "Unified verdict combines artifact reliability tiers, corroboration, Roblox runtime provenance, "
            "and tamper risk. Browser visit history alone cannot reach a high verdict."
        ),
    }
