"""Unit tests for Roblox runtime helper scoring."""
from __future__ import annotations

import unittest

from roblox_runtime import _score_rwx_region


class RobloxRuntimeHelperTests(unittest.TestCase):
    def test_large_jit_region_scores_low(self) -> None:
        self.assertEqual(_score_rwx_region(32 * 1024 * 1024, False), "low")

    def test_small_pe_region_scores_high(self) -> None:
        self.assertEqual(_score_rwx_region(512 * 1024, True), "high")

    def test_medium_region_without_pe(self) -> None:
        self.assertEqual(_score_rwx_region(4 * 1024 * 1024, False), "medium")


if __name__ == "__main__":
    unittest.main()
