"""Core dataclasses and typed models for Virello findings and scan flow."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Severity = Literal["informational", "low", "medium", "high", "critical"]
ConfidenceTier = Literal["low", "moderate", "high", "confirmed"]
IndicatorStrength = Literal["informational", "weak", "suspicious", "strong", "confirmed"]
ScanMode = Literal["quick", "deep", "custom"]
FindingStatus = Literal["open", "reviewed", "dismissed", "confirmed"]


@dataclass
class EvidenceItem:
    kind: str
    value: str
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "value": self.value, "label": self.label}


@dataclass
class Finding:
    id: str
    title: str
    category: str
    severity: Severity
    confidence: float
    confidence_tier: ConfidenceTier
    indicator_strength: IndicatorStrength
    detection_method: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    location: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    why_flagged: str = ""
    related_ids: list[str] = field(default_factory=list)
    recommended_action: str = ""
    hashes: dict[str, str] = field(default_factory=dict)
    status: FindingStatus = "open"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence"] = [
            item.to_dict() if isinstance(item, EvidenceItem) else dict(item)
            for item in self.evidence
        ]
        return payload


@dataclass(frozen=True)
class ScanStageDef:
    key: str
    label: str
    weight: float
    description: str = ""


# Professional forensic scan stages (weights sum to 1.0 for deep mode).
SCAN_STAGE_DEFINITIONS: tuple[ScanStageDef, ...] = (
    ScanStageDef("PREPARING", "Preparing scan", 0.05, "Initialize budgets, paths, and intelligence."),
    ScanStageDef("ENVIRONMENT", "Environment inventory", 0.08, "OS, profile, and Roblox install context."),
    ScanStageDef("PROCESSES", "Process inspection", 0.12, "Live processes, modules, and handles."),
    ScanStageDef("FILESYSTEM", "Filesystem walk", 0.18, "Deep path enumeration and install zones."),
    ScanStageDef("ARTIFACTS", "Artifact collection", 0.20, "Prefetch, BAM, Amcache, browser, logs."),
    ScanStageDef("SIGNATURES", "Signature matching", 0.12, "Hash blocklist and name/alias signatures."),
    ScanStageDef("CORRELATION", "Correlation", 0.10, "Cross-source provenance and corroboration."),
    ScanStageDef("RISK_EVAL", "Risk evaluation", 0.08, "Confidence scoring and bypass resilience."),
    ScanStageDef("REPORT", "Report assembly", 0.07, "Findings bundle and reviewer summary."),
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
