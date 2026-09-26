"""Intelligence package — structured signatures and whitelist data."""
from __future__ import annotations

from virello.intelligence.loader import (
    IntelligenceDB,
    get_aliases,
    get_ambiguous_names,
    get_autoexec_dir_names,
    get_binary_only_aliases,
    get_download_domain_hints,
    get_executor_names,
    get_install_dir_names,
    get_known_relative_paths,
    get_rbxasset_signatures,
    get_schema_version,
    get_updated_at,
    load_intelligence,
    reload_intelligence,
)

__all__ = [
    "IntelligenceDB",
    "get_aliases",
    "get_ambiguous_names",
    "get_autoexec_dir_names",
    "get_binary_only_aliases",
    "get_download_domain_hints",
    "get_executor_names",
    "get_install_dir_names",
    "get_known_relative_paths",
    "get_rbxasset_signatures",
    "get_schema_version",
    "get_updated_at",
    "load_intelligence",
    "reload_intelligence",
]
