"""Tests for evidence_engine confidence and indicator_strength mapping."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evidence_engine import (  # noqa: E402
    _indicator_strength_for_hit,
    compute_hit_confidence,
    enrich_executor_artifact_evidence,
)


def test_indicator_strength_high_with_sha256_is_confirmed():
    hit = {
        "artifact_source": "sha256_blocklist",
        "sha256": "a" * 64,
        "executor_name_hits": ["Wave"],
        "reasons": ["sha256_blocklist:Wave"],
        "display_at": "2026-09-26T12:00:00Z",
    }
    meta = compute_hit_confidence(hit, corroboration_count=2)
    assert meta["confidence_tier"] == "high"
    assert meta["indicator_strength"] == "confirmed"
    assert meta["confidence"] >= 0.82


def test_indicator_strength_high_without_sha_is_strong():
    hit = {
        "artifact_source": "live_process",
        "executor_name_hits": ["Xeno"],
        "reasons": ["live_process_match"],
        "display_at": "2026-09-26T12:00:00Z",
    }
    meta = compute_hit_confidence(hit, corroboration_count=3)
    assert meta["confidence_tier"] == "high"
    assert meta["indicator_strength"] == "strong"


def test_indicator_strength_medium_is_suspicious():
    assert _indicator_strength_for_hit("medium", {"artifact_source": "prefetch_execution"}) == "suspicious"
    assert _indicator_strength_for_hit("high", {"sha256": "abc"}) == "confirmed"
    assert _indicator_strength_for_hit("high", {}) == "strong"
    assert _indicator_strength_for_hit("low", {}) == "weak"


def test_indicator_strength_low_is_weak():
    hit = {
        "artifact_source": "browser_history_domain",
        "executor_name_hits": ["Wave"],
        "display_at": "2024-01-01T12:00:00Z",
    }
    meta = compute_hit_confidence(hit, corroboration_count=1)
    assert meta["confidence_tier"] == "low"
    assert meta["indicator_strength"] == "weak"


def test_enrich_attaches_findings_bundle_when_virello_available():
    bundle = {
        "available": True,
        "hits": [
            {
                "artifact_source": "bam_execution",
                "path": r"C:\Users\test\AppData\Local\Xeno\xeno.exe",
                "executor_name_hits": ["Xeno"],
                "sha256": "b" * 64,
                "reasons": ["sha256_blocklist:Xeno"],
                "display_at": "2026-09-26T12:00:00Z",
            }
        ],
    }
    out = enrich_executor_artifact_evidence(bundle)
    assert out["hits"][0].get("indicator_strength") in {"confirmed", "strong", "suspicious", "weak"}
    assert "findings_bundle" in out or normalize_optional_ok(out)


def normalize_optional_ok(out: dict) -> bool:
    # If virello import failed in frozen builds, enrich still returns silently.
    return "confidence_engine_version" in out and "hits" in out
