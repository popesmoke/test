"""Normalize raw scan hits into reviewer-facing findings."""
from __future__ import annotations

import hashlib
from typing import Any

from virello.models import (
    ConfidenceTier,
    EvidenceItem,
    Finding,
    IndicatorStrength,
    Severity,
    utc_now_iso,
)

_SOURCE_LABELS: dict[str, str] = {
    "sha256_blocklist": "verified binary fingerprint",
    "live_process": "running process",
    "live_injected_module": "module loaded into a process",
    "bam_execution_binary": "Background Activity Moderator execution record",
    "bam_execution": "Background Activity Moderator execution record",
    "dam_execution": "Desktop Activity Moderator execution record",
    "amcache_hive": "Amcache inventory entry",
    "prefetch_execution": "Prefetch execution artifact",
    "pca_compat": "Program Compatibility Assistant artifact",
    "usn_journal": "NTFS USN journal entry",
    "recycle_bin": "Recycle Bin remnant",
    "recycle_bin_content": "Recycle Bin remnant",
    "shimcache": "Shimcache / AppCompatCache entry",
    "userassist": "UserAssist execution record",
    "recent_lnk": "Recent .lnk shortcut",
    "registry_uninstall": "uninstall registry entry",
    "scheduled_task": "scheduled task",
    "ifeo_hijack": "IFEO image-file execution options entry",
    "roblox_protocol_registry": "Roblox protocol registry entry",
    "roblox_autoexec_folder": "Roblox autoexec / workspace folder",
    "roblox_log": "Roblox client log",
    "roblox_log_rbxasset": "Roblox log rbxasset signature",
    "browser_download": "browser download record",
    "browser_history_domain": "browser history domain match",
    "full_pc_filesystem": "filesystem path match",
    "filesystem_indicator": "filesystem path indicator",
    "profile_binary_sweep": "profile binary sweep",
    "known_install_path": "known install path",
    "removed_artifact": "removed or missing artifact",
}


def _map_confidence_tier(raw_tier: str, *, has_sha256: bool) -> ConfidenceTier:
    tier = str(raw_tier or "low").lower()
    if tier == "high" and has_sha256:
        return "confirmed"
    if tier == "medium":
        return "moderate"
    if tier in {"low", "moderate", "high", "confirmed"}:
        return tier  # type: ignore[return-value]
    return "low"


def derive_indicator_strength(
    confidence_tier: str,
    *,
    has_sha256: bool = False,
    source_reliability: float | None = None,
) -> IndicatorStrength:
    """Map confidence tier (+ hash / reliability) to indicator strength."""
    tier = str(confidence_tier or "low").lower()
    if tier in {"confirmed"} or (tier == "high" and has_sha256):
        return "confirmed"
    if tier == "high":
        return "strong"
    if tier in {"medium", "moderate"}:
        strength: IndicatorStrength = "suspicious"
    elif tier == "low":
        strength = "weak"
    else:
        strength = "informational"

    if source_reliability is not None and source_reliability < 0.25 and strength in {"suspicious", "strong"}:
        return "weak"
    return strength


def _severity_for_strength(strength: IndicatorStrength) -> Severity:
    return {
        "confirmed": "critical",
        "strong": "high",
        "suspicious": "medium",
        "weak": "low",
        "informational": "informational",
    }.get(strength, "low")  # type: ignore[return-value]


def _recommended_action(strength: IndicatorStrength) -> str:
    return {
        "confirmed": "Preserve the matched binary and related artifacts, then remove or quarantine after review.",
        "strong": "Investigate the path and corroborating sources before remediation.",
        "suspicious": "Review this indicator with additional artifacts; do not treat it as standalone confirmation.",
        "weak": "Record for context only; seek stronger corroboration before any action.",
        "informational": "Informational context only; no remediation required.",
    }.get(strength, "Review the indicator with available corroborating evidence.")


def _why_flagged(hit: dict[str, Any]) -> str:
    source = str(hit.get("artifact_source") or "unknown")
    source_label = _SOURCE_LABELS.get(source, source.replace("_", " "))
    labels = [str(x) for x in (hit.get("executor_name_hits") or []) if x]
    cheat_hints = [str(x) for x in (hit.get("cheat_filename_hints") or []) if x]
    reasons = [str(x) for x in (hit.get("reasons") or []) if x]
    parts: list[str] = [f"Matched via {source_label}"]
    if labels:
        parts.append(f"linked brand token(s): {', '.join(labels[:4])}")
    if cheat_hints:
        parts.append(f"filename pattern hint(s): {', '.join(cheat_hints[:3])}")
    filtered_reasons = [r for r in reasons if not r.lower().startswith("cheat")]
    if filtered_reasons:
        parts.append(f"supporting reason(s): {', '.join(filtered_reasons[:4])}")
    if hit.get("removed_artifact") or hit.get("file_exists") is False:
        parts.append("artifact appears removed or missing on disk")
    text = "; ".join(parts) + "."
    # Never use sensational language.
    banned = ("cheat found", "hack found", "executor found!!!", "caught cheating")
    lowered = text.lower()
    for phrase in banned:
        if phrase in lowered:
            text = text.replace(phrase, "indicator matched").replace(phrase.upper(), "indicator matched")
    return text


def _hit_id(hit: dict[str, Any], index: int = 0) -> str:
    existing = hit.get("id") or hit.get("finding_id")
    if existing:
        return str(existing)
    basis = "|".join(
        [
            str(hit.get("artifact_source") or ""),
            str(hit.get("path") or ""),
            str(hit.get("sha256") or ""),
            ",".join(str(x) for x in (hit.get("executor_name_hits") or [])[:3]),
            str(index),
        ]
    )
    return "f_" + hashlib.sha1(basis.encode("utf-8", errors="replace")).hexdigest()[:12]


def _evidence_from_hit(hit: dict[str, Any]) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    path = str(hit.get("path") or "")
    if path:
        items.append(EvidenceItem(kind="path", value=path[:520], label="Artifact path"))
    sha = str(hit.get("sha256") or "")
    if sha:
        items.append(EvidenceItem(kind="sha256", value=sha.lower(), label="SHA-256"))
    source = str(hit.get("artifact_source") or "")
    if source:
        items.append(EvidenceItem(kind="artifact_source", value=source, label="Artifact source"))
    for label in hit.get("executor_name_hits") or []:
        items.append(EvidenceItem(kind="brand_token", value=str(label), label="Brand token"))
    for reason in (hit.get("reasons") or [])[:6]:
        items.append(EvidenceItem(kind="reason", value=str(reason), label="Reason"))
    return items


def normalize_hit_to_finding(hit: dict[str, Any], *, index: int = 0) -> dict[str, Any]:
    """Convert a raw scan hit into a Finding-shaped dict."""
    row = dict(hit or {})
    has_sha256 = bool(
        row.get("sha256")
        or any(str(r).startswith("sha256_blocklist:") for r in (row.get("reasons") or []))
    )
    raw_tier = str(row.get("confidence_tier") or "low")
    confidence = float(row.get("confidence") or 0.0)
    source_reliability = row.get("source_reliability")
    reliability = float(source_reliability) if source_reliability is not None else None

    # Prefer precomputed indicator_strength from evidence_engine when present.
    strength_raw = row.get("indicator_strength")
    if strength_raw in {"informational", "weak", "suspicious", "strong", "confirmed"}:
        strength: IndicatorStrength = strength_raw  # type: ignore[assignment]
    else:
        strength = derive_indicator_strength(
            raw_tier,
            has_sha256=has_sha256,
            source_reliability=reliability,
        )

    mapped_tier = _map_confidence_tier(raw_tier, has_sha256=has_sha256)
    labels = [str(x) for x in (row.get("executor_name_hits") or []) if x]
    title_brand = labels[0] if labels else "Tracked indicator"
    path = str(row.get("path") or "")
    source = str(row.get("artifact_source") or "unknown")

    finding = Finding(
        id=_hit_id(row, index),
        title=f"{title_brand} artifact indicator",
        category="executor_artifact",
        severity=_severity_for_strength(strength),
        confidence=round(confidence, 3),
        confidence_tier=mapped_tier,
        indicator_strength=strength,
        detection_method=source,
        evidence=_evidence_from_hit(row),
        location=path[:520],
        timestamp=str(row.get("display_at") or row.get("modified") or utc_now_iso()),
        metadata={
            "artifact_source": source,
            "reliability_class": row.get("reliability_class"),
            "corroboration_count": row.get("corroboration_count"),
            "path_allowlisted": row.get("path_allowlisted"),
            "removed_artifact": bool(row.get("removed_artifact")),
            "cheat_filename_hints": list(row.get("cheat_filename_hints") or []),
            "authenticode_status": row.get("authenticode_status"),
        },
        why_flagged=_why_flagged(row),
        related_ids=[],
        recommended_action=_recommended_action(strength),
        hashes={"sha256": str(row.get("sha256")).lower()} if row.get("sha256") else {},
        status="open",
    )
    return finding.to_dict()


def build_findings_bundle(
    executor_artifact_evidence: dict[str, Any] | None,
    provenance_chains: list[dict[str, Any]] | None = None,
    bypass_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a structured findings list plus severity/confidence summary counts."""
    evidence = executor_artifact_evidence or {}
    hits = list(evidence.get("hits") or [])
    findings = [normalize_hit_to_finding(hit, index=i) for i, hit in enumerate(hits)]

    by_severity: dict[str, int] = {}
    by_confidence: dict[str, int] = {}
    by_strength: dict[str, int] = {}
    for finding in findings:
        sev = str(finding.get("severity") or "low")
        tier = str(finding.get("confidence_tier") or "low")
        strength = str(finding.get("indicator_strength") or "weak")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_confidence[tier] = by_confidence.get(tier, 0) + 1
        by_strength[strength] = by_strength.get(strength, 0) + 1

    bypass = list(bypass_findings or [])
    chains = list(provenance_chains or [])

    return {
        "available": True,
        "schema_version": 1,
        "findings": findings,
        "finding_count": len(findings),
        "summary": {
            "by_severity": by_severity,
            "by_confidence_tier": by_confidence,
            "by_indicator_strength": by_strength,
            "provenance_chain_count": len(chains),
            "bypass_finding_count": len(bypass),
            "high_or_above": sum(
                by_severity.get(k, 0) for k in ("high", "critical")
            ),
        },
        "provenance_chains": chains,
        "bypass_findings": bypass,
    }
