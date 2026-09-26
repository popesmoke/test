"""Tests for intelligence loader and whitelist classification."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from virello import __version__  # noqa: E402
from virello.intelligence.loader import (  # noqa: E402
    get_aliases,
    get_executor_names,
    get_schema_version,
    get_updated_at,
    load_intelligence,
    reload_intelligence,
)
from virello.stages import STAGE_KEYS, stages_for_mode  # noqa: E402
from virello.whitelist import classify_path  # noqa: E402


def test_package_version():
    assert __version__ == "2.0.0"


def test_load_intelligence_populates_executors():
    reload_intelligence()
    db = load_intelligence()
    names = get_executor_names()
    aliases = get_aliases()

    assert get_schema_version() >= 1
    assert get_updated_at()
    assert "Wave" in names
    assert "Xeno" in names
    assert "Volt" in names
    assert "Wave" in aliases
    assert "waveexecutor" in aliases["Wave"]
    assert "volt" in db.install_dir_names
    assert "Wave" in db.ambiguous_names
    assert "Electron" in db.binary_only_aliases
    assert db.known_relative_paths["Xeno"]
    assert "getwave.gg" in db.download_domain_hints["Wave"]
    assert db.rbxasset_signatures["Delta"]
    assert "autoexec" in db.autoexec_dir_names
    assert db.blocklist_path.endswith("executor_sha256_blocklist.json")
    assert db.trusted_path_fragments
    assert "chromedriver" in db.benign_executable_stems
    assert any("robloxplayerbeta" in f for f in db.roblox_trusted_launcher_fragments)
    assert any("selenium" in f for f in db.dev_tool_path_fragments)


def test_classify_path_trusted_and_dev_and_suspicious():
    trusted = classify_path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    assert trusted["status"] == "trusted"

    roblox = classify_path(r"C:\Users\a\AppData\Local\Roblox\Versions\version-1\RobloxPlayerBeta.exe")
    assert roblox["status"] == "trusted"

    dev = classify_path(r"C:\proj\.venv\Lib\site-packages\selenium\webdriver\chrome\chromedriver.exe")
    assert dev["status"] in {"benign_dev", "trusted"}

    stem = classify_path(r"C:\tools\chromedriver.exe")
    assert stem["status"] == "benign_dev"
    assert "chromedriver" in stem["reason"]

    zone = classify_path(r"C:\Users\a\Downloads\mystery.exe")
    assert zone["status"] == "suspicious_zone"

    unknown = classify_path(r"D:\custom\apps\widget.exe")
    assert unknown["status"] in {"unknown", "suspicious_zone"}


def test_classify_path_does_not_silently_suppress():
    result = classify_path(r"C:\Windows\System32\notepad.exe")
    assert "status" in result and "reason" in result
    assert result["status"] == "trusted"


def test_stages_weights_sum_to_one():
    deep = stages_for_mode("deep")
    quick = stages_for_mode("quick")
    assert abs(sum(s["weight"] for s in deep) - 1.0) < 1e-5
    assert abs(sum(s["weight"] for s in quick) - 1.0) < 1e-5
    assert "FILESYSTEM" in {s["key"] for s in deep}
    assert "FILESYSTEM" not in {s["key"] for s in quick}
    assert set(STAGE_KEYS) == {s["key"] for s in deep}
