"""Path classification against intelligence whitelist — audit only, never silent suppress."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from virello.intelligence.loader import load_intelligence

ClassificationStatus = str  # trusted | benign_dev | unknown | suspicious_zone


def _norm(path: str) -> str:
    return str(path or "").replace("/", "\\").lower().strip()


def classify_path(path: str, *, intel: Any | None = None) -> dict[str, str]:
    """
    Classify a filesystem path for reviewer audit.

    Returns status among: trusted | benign_dev | unknown | suspicious_zone.
    Does not suppress hits — callers decide how to use the classification.
    """
    db = intel if intel is not None else load_intelligence()
    low = _norm(path)
    if not low:
        return {"status": "unknown", "reason": "empty_path"}

    for fragment in db.roblox_trusted_launcher_fragments:
        if fragment.lower() in low:
            return {"status": "trusted", "reason": f"roblox_trusted_launcher:{fragment}"}

    for fragment in db.trusted_path_fragments:
        if fragment.lower() in low:
            return {"status": "trusted", "reason": f"trusted_path_fragment:{fragment}"}

    for fragment in db.dev_tool_path_fragments:
        if fragment.lower() in low:
            return {"status": "benign_dev", "reason": f"dev_tool_fragment:{fragment}"}

    stem = Path(low).stem.lower()
    if stem in {s.lower() for s in db.benign_executable_stems}:
        return {"status": "benign_dev", "reason": f"benign_executable_stem:{stem}"}

    for fragment in db.suspicious_zone_fragments:
        if fragment.lower() in low:
            return {"status": "suspicious_zone", "reason": f"suspicious_zone:{fragment}"}

    return {"status": "unknown", "reason": "no_whitelist_match"}
