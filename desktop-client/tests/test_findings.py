"""Tests for finding normalization and bundle summary."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from virello.findings import (  # noqa: E402
    build_findings_bundle,
    derive_indicator_strength,
    normalize_hit_to_finding,
)
from virello.models import Finding  # noqa: E402


def test_normalize_hit_builds_why_flagged_without_sensational_language():
    hit = {
        "artifact_source": "prefetch_execution",
        "path": r"C:\Users\a\AppData\Local\Wave\wave.exe",
        "executor_name_hits": ["Wave"],
        "reasons": ["prefetch_match"],
        "confidence": 0.71,
        "confidence_tier": "medium",
        "indicator_strength": "suspicious",
        "display_at": "2026-09-20T10:00:00Z",
    }
    finding = normalize_hit_to_finding(hit)
    assert finding["category"] == "executor_artifact"
    assert finding["confidence_tier"] == "moderate"
    assert finding["indicator_strength"] == "suspicious"
    assert "why_flagged" in finding and finding["why_flagged"]
    banned = ("cheat found", "hack found", "CHEAT FOUND")
    text = finding["why_flagged"].lower()
    assert all(phrase.lower() not in text for phrase in banned)
    assert "recommended_action" in finding and finding["recommended_action"]


def test_normalize_sha256_high_maps_to_confirmed_tier():
    hit = {
        "artifact_source": "sha256_blocklist",
        "path": r"C:\Temp\xeno.exe",
        "executor_name_hits": ["Xeno"],
        "sha256": "c" * 64,
        "reasons": ["sha256_blocklist:Xeno"],
        "confidence": 0.95,
        "confidence_tier": "high",
        "display_at": "2026-09-26T12:00:00Z",
    }
    finding = normalize_hit_to_finding(hit)
    assert finding["confidence_tier"] == "confirmed"
    assert finding["indicator_strength"] == "confirmed"
    assert finding["severity"] == "critical"
    assert finding["hashes"].get("sha256") == "c" * 64


def test_finding_to_dict_roundtrip_fields():
    finding = Finding(
        id="f_test",
        title="Test",
        category="executor_artifact",
        severity="medium",
        confidence=0.6,
        confidence_tier="moderate",
        indicator_strength="suspicious",
        detection_method="prefetch_execution",
        why_flagged="Matched via prefetch.",
        recommended_action="Review.",
    )
    payload = finding.to_dict()
    assert payload["id"] == "f_test"
    assert payload["severity"] == "medium"
    assert isinstance(payload["evidence"], list)


def test_build_findings_bundle_summary_counts():
    evidence = {
        "available": True,
        "hits": [
            {
                "artifact_source": "sha256_blocklist",
                "path": r"C:\a.exe",
                "executor_name_hits": ["Wave"],
                "sha256": "d" * 64,
                "confidence": 0.96,
                "confidence_tier": "high",
                "indicator_strength": "confirmed",
            },
            {
                "artifact_source": "browser_history_domain",
                "path": "",
                "executor_name_hits": ["Wave"],
                "confidence": 0.2,
                "confidence_tier": "low",
                "indicator_strength": "weak",
            },
        ],
    }
    bundle = build_findings_bundle(evidence, provenance_chains=[{"stem": "WAVE"}], bypass_findings=[])
    assert bundle["finding_count"] == 2
    assert bundle["summary"]["by_severity"]["critical"] == 1
    assert bundle["summary"]["by_confidence_tier"]["confirmed"] == 1
    assert bundle["summary"]["by_confidence_tier"]["low"] == 1
    assert bundle["summary"]["provenance_chain_count"] == 1


def test_derive_indicator_strength_mapping():
    assert derive_indicator_strength("high", has_sha256=True) == "confirmed"
    assert derive_indicator_strength("high", has_sha256=False) == "strong"
    assert derive_indicator_strength("medium") == "suspicious"
    assert derive_indicator_strength("low") == "weak"
