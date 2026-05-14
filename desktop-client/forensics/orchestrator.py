from __future__ import annotations

import os
from typing import Any, Callable

from .correlation_engine import gather_forensic_context, run_correlation_engine
from .models import RiskWeights, default_risk_weights

RunCommand = Callable[..., str]


def _env_filters() -> dict[str, Any]:
    filters: dict[str, Any] = {}
    if os.getenv("FORENSICS_USN_EXECUTABLE_ONLY", "").lower() in ("1", "true", "yes"):
        filters["usn_executable_only"] = True
    if os.getenv("FORENSICS_USN_UNSIGNED_ONLY", "").lower() in ("1", "true", "yes"):
        filters["usn_unsigned_only"] = True
    if os.getenv("FORENSICS_USN_ENTROPY_MIN"):
        try:
            filters["usn_entropy_min"] = float(os.environ["FORENSICS_USN_ENTROPY_MIN"])
        except ValueError:
            pass
    if os.getenv("FORENSICS_USN_YARA_POSITIVE_ONLY", "").lower() in ("1", "true", "yes"):
        filters["usn_yara_positive_only"] = True
    return filters


def _env_weights() -> RiskWeights | None:
    raw = os.getenv("FORENSICS_RISK_WEIGHTS_JSON")
    if not raw:
        return None
    try:
        import json

        d = json.loads(raw)
        w = default_risk_weights()
        for k, v in d.items():
            if hasattr(w, k) and isinstance(v, (int, float)):
                setattr(w, k, float(v))
        return w
    except Exception:
        return None


def run_windows_forensic_correlation(run_command: RunCommand) -> dict[str, Any]:
    """Collect forensic subsystems, run correlation engine, return JSON-serializable report."""
    if os.name != "nt":
        return {"available": False, "reason": "Windows only", "modules": {}}

    ctx = gather_forensic_context(run_command)
    weights = _env_weights() or default_risk_weights()
    correlated = run_correlation_engine(ctx, run_command, weights=weights, filters=_env_filters())

    return {
        "available": True,
        "schema_version": "2026-05-14",
        "session_anchor_utc": ctx.get("session_anchor_utc"),
        "modules": {
            "saved_files_viewer": {
                "description": "Recent LNK, Downloads/Desktop drops, JumpList containers, Discord/temp paths.",
                "data": ctx.get("saved_files"),
            },
            "usn_journal_parser": {
                "description": "Sampled NTFS USN CSV via fsutil across fixed volumes.",
                "data": ctx.get("usn"),
                "filters_supported": [
                    "FORENSICS_USN_EXECUTABLE_ONLY",
                    "FORENSICS_USN_UNSIGNED_ONLY",
                    "FORENSICS_USN_ENTROPY_MIN",
                    "FORENSICS_USN_YARA_POSITIVE_ONLY",
                ],
            },
            "deleted_bam_parser": {
                "description": "BAM paths missing on disk + Prefetch/USN correlation (true carved deleted keys require hive transaction tooling).",
                "note": "Heuristic: missing BAM target file, plus optional Prefetch stem match.",
            },
            "windows_sqlite_parser": {
                "description": "Read-only Chrome/Edge History + downloads; ActivitiesCache best-effort paths.",
                "data": ctx.get("browser_sqlite"),
                "activity_cache": ctx.get("activity_cache"),
                "activity_cache_executable_strings": ctx.get("activity_cache_paths"),
            },
            "bam_parser": {"description": "Structured HKLM BAM UserSettings execution paths.", "data": ctx.get("bam")},
            "prefetch_parser": {
                "description": "Prefetch filenames with executable token extraction.",
                "data": ctx.get("prefetch"),
            },
            "pcasvc_executed": {
                "description": "Program Compatibility Assistant operational events.",
                "data": ctx.get("pca"),
            },
        },
        "correlation_engine": correlated,
        "shared_infrastructure": {
            "sha256": "first 2MB sample per analyzed file",
            "authenticode": "PowerShell Get-AuthenticodeSignature batch",
            "entropy": "Shannon on 256KB sample",
            "yara": "optional yara-python + FORENSICS_YARA_RULES or packaged yara_rules/*.yar",
            "risk_weights": "defaults overridable via FORENSICS_RISK_WEIGHTS_JSON",
            "json_output": "findings[].* and correlation_engine.*",
        },
    }
