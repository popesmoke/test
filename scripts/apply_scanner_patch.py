"""Apply scanner patches via temp file (app.py may be locked for direct writes)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "desktop-client" / "app.py"
TMP = ROOT / "desktop-client" / "app_patched_tmp.py"
text = APP.read_text(encoding="utf-8")

replacements = [
    (
        "SCAN_SOFT_TARGET_SECONDS = 72.0\n# Hard ceiling for the full diagnostic pass (3 minutes).\nSCAN_MAX_SECONDS = 180.0\n# Reserve time for correlation/report assembly so the filesystem walk cannot consume the whole budget.\nSCAN_CORRELATION_RESERVE_SECONDS = 22.0\nFULL_PC_WALK_MAX_SECONDS = 30.0",
        "SCAN_SOFT_TARGET_SECONDS = 55.0\n# Hard ceiling for the full diagnostic pass (6 minutes).\nSCAN_MAX_SECONDS = 360.0\n# Reserve time for correlation/report assembly so the filesystem walk cannot consume the whole budget.\nSCAN_CORRELATION_RESERVE_SECONDS = 18.0\nFULL_PC_WALK_MAX_SECONDS = 22.0",
    ),
    (
        "ARTIFACT_SCAN_MAX_TIMEOUT_SEC = 7.0\nDISK_EXECUTABLE_FALLBACK_TIMEOUT_SEC = 6.0\nPIPELINE_DRAIN_MAX_SECONDS = 9.0",
        "ARTIFACT_SCAN_MAX_TIMEOUT_SEC = 5.0\nDISK_EXECUTABLE_FALLBACK_TIMEOUT_SEC = 4.0\nPIPELINE_DRAIN_MAX_SECONDS = 7.0",
    ),
    (
        '    enriched = [by_id[uid] for uid in resolved_ids if by_id[uid].get("authenticated")]\n    for entry in enriched:\n        entry["authenticated"] = True\n    return enriched[:40]',
        '    enriched = [by_id[uid] for uid in resolved_ids]\n    for entry in enriched:\n        if entry.get("authenticated"):\n            entry["authenticated"] = True\n    for entry in by_name.values():\n        if entry.get("user_id"):\n            continue\n        if entry.get("username"):\n            enriched.append(entry)\n    return enriched[:48]',
    ),
    (
        """def roblox_browser_account_scan() -> dict:
    \"\"\"Privacy-safe account hints — Roblox client logs/storage plus browser profiles.\"\"\"
    accounts: list[dict] = []
    seen_ids: set[str] = set()
    artifacts: list[dict] = []

    def _append_account(user_id: str | None, username: str | None, sources: list[str]) -> None:""",
        """def roblox_browser_account_scan() -> dict:
    \"\"\"Privacy-safe account hints — Roblox client logs/storage plus browser profiles.\"\"\"
    accounts: list[dict] = []
    seen_ids: set[str] = set()
    artifacts: list[dict] = []
    browser_close = {"closed": [], "failed": []}
    # Browser processes are intentionally left running; locked cookie DBs are copied instead.

    def _append_account(
        user_id: str | None,
        username: str | None,
        sources: list[str],
        *,
        authenticated: bool = False,
    ) -> None:""",
    ),
    (
        """                for account in accounts:
                    if str(account.get("user_id") or "") == uid:
                        account["sources"] = sorted(set(account.get("sources") or []) | set(sources))
                        if username and _roblox_is_plausible_username(username) and not account.get("username"):
                            account["username"] = username
                        return""",
        """                for account in accounts:
                    if str(account.get("user_id") or "") == uid:
                        account["sources"] = sorted(set(account.get("sources") or []) | set(sources))
                        if username and _roblox_is_plausible_username(username) and not account.get("username"):
                            account["username"] = username
                        if authenticated:
                            account["authenticated"] = True
                        return""",
    ),
    (
        """            accounts.append(
                {
                    "user_id": uid,
                    "username": username,
                    "sources": sources,
                    "authenticated": False,
                }
            )
            return
        if username and _roblox_is_plausible_username(username):
            accounts.append(
                {
                    "user_id": None,
                    "username": username,
                    "sources": sources,
                    "authenticated": False,
                }
            )

    def _merge_browser_artifact(artifact: dict) -> None:""",
        """            accounts.append(
                {
                    "user_id": uid,
                    "username": username,
                    "sources": sources,
                    "authenticated": authenticated,
                }
            )
            return
        if username and _roblox_is_plausible_username(username):
            accounts.append(
                {
                    "user_id": None,
                    "username": username,
                    "sources": sources,
                    "authenticated": authenticated,
                }
            )

    def _merge_browser_artifact(artifact: dict) -> None:""",
    ),
    (
        """    client_session = _roblox_client_session_user()
    if client_session:
        _append_account(
            client_session.get("user_id"),
            client_session.get("username"),
            list(client_session.get("sources") or ["Roblox client session"]),
        )
    for account in _roblox_app_storage_accounts():
        _append_account(
            account.get("user_id"),
            account.get("username") or account.get("display_name"),
            list(account.get("sources") or ["Roblox client storage"]),
        )""",
        """    client_session = _roblox_client_session_user()
    if client_session:
        _append_account(
            client_session.get("user_id"),
            client_session.get("username"),
            list(client_session.get("sources") or ["Roblox client session"]),
            authenticated=bool(client_session.get("user_id")),
        )
    for account in _roblox_app_storage_accounts():
        _append_account(
            account.get("user_id"),
            account.get("username") or account.get("display_name"),
            list(account.get("sources") or ["Roblox client storage"]),
            authenticated=bool(account.get("authenticated")),
        )""",
    ),
    (
        '        "browsers_closed": [],\n        "browsers_close_failed": [],',
        '        "browsers_closed": browser_close.get("closed") or [],\n        "browsers_close_failed": browser_close.get("failed") or [],',
    ),
    (
        """def discord_local_accounts_scan() -> dict[str, object]:
    \"\"\"Read Discord user IDs and display names from local client storage only.\"\"\"
    if platform.system() != "Windows":
        return {"available": False, "accounts": [], "reason": "Windows-only"}
    if scan_collect_phase_exhausted():
        return {"available": False, "accounts": [], "reason": "Scan time budget exhausted"}

    appdata = Path(os.environ.get("APPDATA", ""))
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    discord_roots = [
        appdata / "discord",
        appdata / "discordcanary",
        appdata / "discordptb",
        local / "Discord",
        local / "DiscordCanary",
        local / "DiscordPTB",
    ]""",
        """def _discord_discover_roots() -> list[Path]:
    \"\"\"Collect Discord desktop app storage roots, including Microsoft Store installs.\"\"\"
    appdata = Path(os.environ.get("APPDATA", ""))
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    roots: list[Path] = [
        appdata / "discord",
        appdata / "discordcanary",
        appdata / "discordptb",
        local / "Discord",
        local / "DiscordCanary",
        local / "DiscordPTB",
    ]
    packages = local / "Packages"
    if packages.is_dir():
        try:
            for pkg in packages.iterdir():
                name = pkg.name.lower()
                if not name.startswith("discordinc.discord"):
                    continue
                for candidate in (
                    pkg / "LocalCache" / "Roaming" / "discord",
                    pkg / "LocalCache" / "Roaming" / "discordcanary",
                    pkg / "LocalCache" / "Roaming" / "discordptb",
                    pkg / "LocalState",
                ):
                    if candidate.is_dir():
                        roots.append(candidate)
        except OSError:
            pass
    for base in (local / "Discord", local / "DiscordCanary", local / "DiscordPTB"):
        if not base.is_dir():
            continue
        try:
            for entry in base.iterdir():
                if entry.is_dir() and entry.name.startswith("app-"):
                    roots.append(entry)
        except OSError:
            pass
    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root).lower()
        if key in seen:
            continue
        seen.add(key)
        if root.is_dir():
            deduped.append(root)
    return deduped


def discord_local_accounts_scan() -> dict[str, object]:
    \"\"\"Read Discord user IDs and display names from local client storage only.\"\"\"
    if platform.system() != "Windows":
        return {"available": False, "accounts": [], "reason": "Windows-only"}
    if scan_collect_phase_exhausted():
        return {"available": False, "accounts": [], "reason": "Scan time budget exhausted"}

    discord_roots = _discord_discover_roots()""",
    ),
    (
        '        "accounts": accounts[:48],\n        "note": "Local client storage only.",',
        '        "accounts": accounts[:64],\n        "note": "Discord desktop app storage and browser profile hints.",',
    ),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"MISSING BLOCK:\n{old[:120]}...")
    text = text.replace(old, new, 1)

TMP.write_text(text, encoding="utf-8")
APP.unlink()
TMP.rename(APP)
print("Patched app.py via temp swap")
