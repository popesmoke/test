from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DetectionMetadata:
    """Structured metadata attached to every detection for reporting and tuning."""

    rule_id: str
    module: str
    version: str = "1.0.0"
    fp_controls: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)


@dataclass
class ForensicFinding:
    severity: str  # info | low | medium | high
    confidence: float  # 0.0 - 1.0
    title: str
    reason: str
    artifact_sources: list[str]
    correlated_evidence: list[dict[str, Any]]
    timestamps: list[str]
    primary_path: str | None = None
    sha256: str | None = None
    signature_status: str | None = None
    entropy: float | None = None
    yara_matches: list[str] = field(default_factory=list)
    risk_score: float = 0.0
    tags: list[str] = field(default_factory=list)
    metadata: DetectionMetadata | None = None

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.metadata:
            d["metadata"] = asdict(self.metadata)
        return d


@dataclass
class TimelineEvent:
    ts_iso: str
    source: str
    action: str
    path: str | None
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.ts_iso,
            "source": self.source,
            "action": self.action,
            "path": self.path,
            "detail": self.detail,
        }


@dataclass
class RiskWeights:
    unsigned: float = 18.0
    high_entropy: float = 12.0
    yara_positive: float = 22.0
    temp_execution: float = 14.0
    removable_drive: float = 16.0
    deleted_after_exec: float = 20.0
    rename_chain: float = 15.0
    random_filename: float = 10.0
    double_extension: float = 12.0
    shortly_before_session: float = 8.0
    cheat_keyword: float = 14.0
    packed_pe: float = 10.0


def default_risk_weights() -> RiskWeights:
    return RiskWeights()
