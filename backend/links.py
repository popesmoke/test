"""Public URLs for scanner download and suspect invite pages."""
from __future__ import annotations

import os


def public_app_url() -> str:
    return os.getenv("PUBLIC_APP_URL", "http://localhost:3000").rstrip("/")


def public_api_url() -> str:
    return os.getenv("PUBLIC_API_URL", os.getenv("API_PUBLIC_URL", "http://localhost:8000")).rstrip("/")


def scanner_download_url() -> str:
    configured = os.getenv("SCANNER_DOWNLOAD_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    release = os.getenv(
        "SCANNER_RELEASE_URL",
        "https://github.com/popesmoke/test/releases/download/scanner-latest/dngscanner.exe",
    ).strip()
    if release:
        return release.rstrip("/")
    return f"{public_api_url()}/download/scanner"


def invite_url(pin: str) -> str:
    return f"{public_app_url()}/?pin={pin}"
