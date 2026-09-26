"""Load structured intelligence JSON into an in-memory IntelligenceDB."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass
class IntelligenceDB:
    schema_version: int = 1
    updated_at: str = ""
    executor_names: list[str] = field(default_factory=list)
    executor_aliases: dict[str, list[str]] = field(default_factory=dict)
    install_dir_names: frozenset[str] = field(default_factory=frozenset)
    ambiguous_names: frozenset[str] = field(default_factory=frozenset)
    binary_only_aliases: dict[str, list[str]] = field(default_factory=dict)
    known_relative_paths: dict[str, list[str]] = field(default_factory=dict)
    download_domain_hints: dict[str, list[str]] = field(default_factory=dict)
    rbxasset_signatures: dict[str, list[str]] = field(default_factory=dict)
    autoexec_dir_names: frozenset[str] = field(default_factory=frozenset)
    trusted_path_fragments: tuple[str, ...] = ()
    benign_executable_stems: frozenset[str] = field(default_factory=frozenset)
    roblox_trusted_launcher_fragments: tuple[str, ...] = ()
    dev_tool_path_fragments: tuple[str, ...] = ()
    suspicious_zone_fragments: tuple[str, ...] = ()
    blocklist_path: str = "assets/executor_sha256_blocklist.json"
    blocklist_schema_version: int = 1
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


def _read_json(name: str) -> dict[str, Any]:
    path = DATA_DIR / name
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Intelligence file {name} must be a JSON object")
    return data


@lru_cache(maxsize=1)
def load_intelligence() -> IntelligenceDB:
    executors = _read_json("executors.json")
    whitelist = _read_json("whitelist.json")
    blocklist_meta = _read_json("blocklist_meta.json")

    schema_version = int(
        max(
            int(executors.get("schema_version") or 1),
            int(whitelist.get("schema_version") or 1),
            int(blocklist_meta.get("schema_version") or 1),
        )
    )
    updated_at = str(
        executors.get("updated_at")
        or whitelist.get("updated_at")
        or blocklist_meta.get("updated_at")
        or ""
    )

    return IntelligenceDB(
        schema_version=schema_version,
        updated_at=updated_at,
        executor_names=list(executors.get("names") or []),
        executor_aliases={str(k): list(v) for k, v in (executors.get("aliases") or {}).items()},
        install_dir_names=frozenset(str(x) for x in (executors.get("install_dir_names") or [])),
        ambiguous_names=frozenset(str(x) for x in (executors.get("ambiguous_names") or [])),
        binary_only_aliases={
            str(k): list(v) for k, v in (executors.get("binary_only_aliases") or {}).items()
        },
        known_relative_paths={
            str(k): list(v) for k, v in (executors.get("known_relative_paths") or {}).items()
        },
        download_domain_hints={
            str(k): list(v) for k, v in (executors.get("download_domain_hints") or {}).items()
        },
        rbxasset_signatures={
            str(k): list(v) for k, v in (executors.get("rbxasset_signatures") or {}).items()
        },
        autoexec_dir_names=frozenset(str(x) for x in (executors.get("autoexec_dir_names") or [])),
        trusted_path_fragments=tuple(str(x) for x in (whitelist.get("trusted_path_fragments") or [])),
        benign_executable_stems=frozenset(
            str(x) for x in (whitelist.get("benign_executable_stems") or [])
        ),
        roblox_trusted_launcher_fragments=tuple(
            str(x) for x in (whitelist.get("roblox_trusted_launcher_fragments") or [])
        ),
        dev_tool_path_fragments=tuple(
            str(x) for x in (whitelist.get("dev_tool_path_fragments") or [])
        ),
        suspicious_zone_fragments=tuple(
            str(x) for x in (whitelist.get("suspicious_zone_fragments") or [])
        ),
        blocklist_path=str(blocklist_meta.get("blocklist_path") or "assets/executor_sha256_blocklist.json"),
        blocklist_schema_version=int(blocklist_meta.get("schema_version") or 1),
        raw={"executors": executors, "whitelist": whitelist, "blocklist_meta": blocklist_meta},
    )


def reload_intelligence() -> IntelligenceDB:
    load_intelligence.cache_clear()
    return load_intelligence()


def get_executor_names() -> list[str]:
    return list(load_intelligence().executor_names)


def get_aliases() -> dict[str, list[str]]:
    return dict(load_intelligence().executor_aliases)


def get_install_dir_names() -> frozenset[str]:
    return load_intelligence().install_dir_names


def get_ambiguous_names() -> frozenset[str]:
    return load_intelligence().ambiguous_names


def get_binary_only_aliases() -> dict[str, list[str]]:
    return dict(load_intelligence().binary_only_aliases)


def get_known_relative_paths() -> dict[str, list[str]]:
    return dict(load_intelligence().known_relative_paths)


def get_download_domain_hints() -> dict[str, list[str]]:
    return dict(load_intelligence().download_domain_hints)


def get_rbxasset_signatures() -> dict[str, list[str]]:
    return dict(load_intelligence().rbxasset_signatures)


def get_autoexec_dir_names() -> frozenset[str]:
    return load_intelligence().autoexec_dir_names


def get_schema_version() -> int:
    return load_intelligence().schema_version


def get_updated_at() -> str:
    return load_intelligence().updated_at
