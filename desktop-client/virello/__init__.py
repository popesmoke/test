"""Virello modular intelligence and findings package."""
from __future__ import annotations

from virello.findings import build_findings_bundle, normalize_hit_to_finding
from virello.intelligence import (
    IntelligenceDB,
    get_aliases,
    get_executor_names,
    get_schema_version,
    get_updated_at,
    load_intelligence,
)
from virello.models import (
    EvidenceItem,
    Finding,
    SCAN_STAGE_DEFINITIONS,
)
from virello.stages import stages_for_mode
from virello.whitelist import classify_path

__version__ = "2.0.0"

__all__ = [
    "__version__",
    "EvidenceItem",
    "Finding",
    "IntelligenceDB",
    "SCAN_STAGE_DEFINITIONS",
    "build_findings_bundle",
    "classify_path",
    "get_aliases",
    "get_executor_names",
    "get_schema_version",
    "get_updated_at",
    "load_intelligence",
    "normalize_hit_to_finding",
    "stages_for_mode",
]
