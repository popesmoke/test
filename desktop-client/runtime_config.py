"""Runtime settings: baked in at secure build time, or from env when running from source."""
from __future__ import annotations

import os


def get_api_url() -> str:
    for key in ("DIAGNOSTIC_API_URL", "DNG_API_URL"):
        value = os.environ.get(key, "").strip()
        if value:
            return value.rstrip("/")

    try:
        from embedded_build_config import API_URL as baked_url  # type: ignore

        if baked_url:
            return str(baked_url).rstrip("/")
    except ImportError:
        pass

    return "https://virello-secure.onrender.com"


def is_protected_build() -> bool:
    try:
        from embedded_build_config import BUILD_PROTECTED  # type: ignore

        return bool(BUILD_PROTECTED)
    except ImportError:
        return False
