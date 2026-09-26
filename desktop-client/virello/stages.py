"""Professional forensic scan stages and mode gating."""
from __future__ import annotations

from typing import Any

from virello.models import SCAN_STAGE_DEFINITIONS, ScanMode, ScanStageDef

STAGE_KEYS = tuple(stage.key for stage in SCAN_STAGE_DEFINITIONS)

# Quick mode skips the deep filesystem walk; remaining weights renormalize to 1.0.
QUICK_ENABLED = frozenset(
    {
        "PREPARING",
        "ENVIRONMENT",
        "PROCESSES",
        "ARTIFACTS",
        "SIGNATURES",
        "CORRELATION",
        "RISK_EVAL",
        "REPORT",
    }
)

DEEP_ENABLED = frozenset(STAGE_KEYS)


def stage_definitions() -> list[dict[str, Any]]:
    return [
        {
            "key": s.key,
            "label": s.label,
            "weight": s.weight,
            "description": s.description,
        }
        for s in SCAN_STAGE_DEFINITIONS
    ]


def stages_for_mode(mode: ScanMode | str) -> list[dict[str, Any]]:
    """Return enabled stages for a mode with weights renormalized to sum to 1.0."""
    mode_key = str(mode or "deep").lower()
    enabled = QUICK_ENABLED if mode_key == "quick" else DEEP_ENABLED
    selected: list[ScanStageDef] = [s for s in SCAN_STAGE_DEFINITIONS if s.key in enabled]
    total = sum(s.weight for s in selected) or 1.0
    rows: list[dict[str, Any]] = []
    running = 0.0
    for index, stage in enumerate(selected):
        if index == len(selected) - 1:
            weight = round(1.0 - running, 6)
        else:
            weight = round(stage.weight / total, 6)
            running += weight
        rows.append(
            {
                "key": stage.key,
                "label": stage.label,
                "weight": weight,
                "description": stage.description,
                "enabled": True,
            }
        )
    return rows


def stage_progress_map(mode: ScanMode | str = "deep") -> dict[str, float]:
    return {row["key"]: float(row["weight"]) for row in stages_for_mode(mode)}


def cumulative_progress(completed_keys: list[str], mode: ScanMode | str = "deep") -> float:
    weights = stage_progress_map(mode)
    done = sum(weights.get(key, 0.0) for key in completed_keys)
    return round(min(1.0, max(0.0, done)), 6)
