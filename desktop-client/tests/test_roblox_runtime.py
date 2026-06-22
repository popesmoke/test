"""Unit tests for Roblox runtime helper scoring."""
from __future__ import annotations

import unittest

from roblox_runtime import _score_rwx_region, roblox_runtime_provenance_scan


class RobloxRuntimeHelperTests(unittest.TestCase):
    def test_large_jit_region_scores_low(self) -> None:
        self.assertEqual(_score_rwx_region(32 * 1024 * 1024, False), "low")

    def test_small_pe_region_scores_high(self) -> None:
        self.assertEqual(_score_rwx_region(512 * 1024, True), "high")

    def test_medium_region_without_pe(self) -> None:
        self.assertEqual(_score_rwx_region(4 * 1024 * 1024, False), "medium")

    def test_runtime_scan_completes_without_exception(self) -> None:
        result = roblox_runtime_provenance_scan(win_authenticode_status=lambda _path: "NotSigned")
        self.assertIn("available", result)
        self.assertNotIn("failed safely", str(result.get("reason") or ""))


if __name__ == "__main__":
    unittest.main()
