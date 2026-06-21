"""Unit tests for evidence confidence scoring and unified verdict logic."""
from __future__ import annotations

import unittest

from evidence_engine import (
    build_evidence_verdict,
    compute_hit_confidence,
    enrich_executor_artifact_evidence,
)


class EvidenceEngineTests(unittest.TestCase):
    def test_name_only_browser_history_is_capped(self) -> None:
        hit = {
            "artifact_source": "browser_history_domain",
            "executor_name_hits": ["Wave"],
            "display_at": "2026-06-20T12:00:00+00:00",
        }
        meta = compute_hit_confidence(hit, corroboration_count=1)
        self.assertLessEqual(meta["confidence"], 0.42)
        self.assertEqual(meta["confidence_tier"], "low")

    def test_sha256_blocklist_reaches_high_tier(self) -> None:
        hit = {
            "artifact_source": "full_pc_filesystem",
            "sha256": "a" * 64,
            "reasons": ["sha256_blocklist:Wave"],
            "display_at": "2026-06-21T08:00:00+00:00",
        }
        meta = compute_hit_confidence(hit, corroboration_count=2)
        self.assertGreaterEqual(meta["confidence"], 0.82)
        self.assertEqual(meta["confidence_tier"], "high")

    def test_runtime_verified_handle_boosts_verdict(self) -> None:
        verdict = build_evidence_verdict(
            executor_artifact_evidence={"available": True, "hits": []},
            roblox_runtime={
                "available": True,
                "verified_external_handles": [
                    {
                        "pid": 9999,
                        "reason": "cross_process_vm_access_to_roblox",
                        "detection_method": "handle_enumeration",
                        "confidence": "high",
                    }
                ],
                "external_process_handles": [
                    {
                        "pid": 9999,
                        "reason": "cross_process_vm_access_to_roblox",
                        "detection_method": "handle_enumeration",
                        "confidence": "high",
                    }
                ],
            },
            bypass_resilience={"available": True, "risk_score": 0, "findings": []},
            cross_artifact={"signals": []},
            scan_budget={"deadline_exceeded": False},
            filesystem_integrity={"reconstruction_confidence": "normal"},
        )
        self.assertGreaterEqual(verdict["score"], 26)
        self.assertIn("handle table verified", " ".join(verdict["runtime_reasons"]).lower())
        self.assertGreaterEqual(verdict["runtime_signal_count"], 1)

    def test_low_confidence_rwx_does_not_inflate_score(self) -> None:
        verdict = build_evidence_verdict(
            executor_artifact_evidence={"available": True, "hits": []},
            roblox_runtime={
                "available": True,
                "suspicious_memory_regions": [
                    {"confidence": "low", "reason": "private_executable_writable_region"}
                ],
                "high_confidence_memory_regions": [],
            },
            bypass_resilience={"available": True, "risk_score": 0, "findings": []},
            cross_artifact={"signals": []},
            scan_budget={"deadline_exceeded": False},
            filesystem_integrity={"reconstruction_confidence": "normal"},
        )
        self.assertLess(verdict["score"], 40)

    def test_enrich_sorts_high_confidence_first(self) -> None:
        bundle = enrich_executor_artifact_evidence(
            {
                "available": True,
                "hits": [
                    {
                        "path": "C:\\Users\\x\\Downloads\\low.exe",
                        "artifact_source": "browser_history_domain",
                        "executor_name_hits": ["Wave"],
                    },
                    {
                        "path": "C:\\Users\\x\\AppData\\Local\\Wave\\wave.exe",
                        "artifact_source": "bam_execution",
                        "executor_name_hits": ["Wave"],
                        "display_at": "2026-06-21T08:00:00+00:00",
                    },
                ],
            }
        )
        tiers = [row.get("confidence_tier") for row in bundle["hits"]]
        self.assertEqual(tiers[0], "high")


if __name__ == "__main__":
    unittest.main()
