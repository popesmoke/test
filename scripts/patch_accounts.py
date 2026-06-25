from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "desktop-client" / "app.py"
text = APP.read_text(encoding="utf-8")

replacements = [
    (
        """    def _append_account(user_id: str | None, username: str | None, sources: list[str]) -> None:
        if user_id:
            uid = str(user_id)
            if uid in seen_ids:
                for account in accounts:
                    if str(account.get("user_id") or "") == uid:
                        account["sources"] = sorted(set(account.get("sources") or []) | set(sources))
                        if username and _roblox_is_plausible_username(username) and not account.get("username"):
                            account["username"] = username
                        return
                return
            seen_ids.add(uid)
            accounts.append(
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
            )""",
        """    def _append_account(
        user_id: str | None,
        username: str | None,
        sources: list[str],
        *,
        authenticated: bool = False,
    ) -> None:
        if user_id:
            uid = str(user_id)
            if uid in seen_ids:
                for account in accounts:
                    if str(account.get("user_id") or "") == uid:
                        account["sources"] = sorted(set(account.get("sources") or []) | set(sources))
                        if username and _roblox_is_plausible_username(username) and not account.get("username"):
                            account["username"] = username
                        if authenticated:
                            account["authenticated"] = True
                        return
                return
            seen_ids.add(uid)
            accounts.append(
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
            )""",
    ),
    (
        """def roblox_browser_account_scan() -> dict:
    \"\"\"Privacy-safe account hints — Roblox client logs/storage plus browser profiles.\"\"\"
    accounts: list[dict] = []
    seen_ids: set[str] = set()
    artifacts: list[dict] = []""",
        """def roblox_browser_account_scan() -> dict:
    \"\"\"Privacy-safe account hints — Roblox client logs/storage plus browser profiles.\"\"\"
    accounts: list[dict] = []
    seen_ids: set[str] = set()
    artifacts: list[dict] = []
    browser_close = {"closed": [], "failed": []}
    # Browser processes are intentionally left running; locked cookie DBs are copied instead.""",
    ),
    (
        """    if client_session:
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
        """    if client_session:
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
        """        "browsers_closed": [],
        "browsers_close_failed": [],""",
        """        "browsers_closed": browser_close.get("closed") or [],
        "browsers_close_failed": browser_close.get("failed") or [],""",
    ),
    (
        """    enriched = [by_id[uid] for uid in resolved_ids if by_id[uid].get("authenticated")]
    for entry in enriched:
        entry["authenticated"] = True
    return enriched[:40]""",
        """    enriched = [by_id[uid] for uid in resolved_ids]
    for entry in enriched:
        if entry.get("authenticated"):
            entry["authenticated"] = True
    for entry in by_name.values():
        if entry.get("user_id"):
            continue
        if entry.get("username"):
            enriched.append(entry)
    return enriched[:48]""",
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
        """        "accounts": accounts[:48],
        "note": "Local client storage only.",
    }""",
        """        "accounts": accounts[:64],
        "note": "Discord desktop app storage and browser profile hints.",
    }""",
    ),
    (
        '            detail="File in Downloads/Desktop/Documents matched executor or cheat filename rules.",',
        '            detail="A file in a common user folder matched review rules.",',
    ),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"MISSING BLOCK:\n{old[:120]}...")
    text = text.replace(old, new, 1)

# Swift false positive guards
if '"Swift"' not in text.split("EXECUTOR_AMBIGUOUS_NAMES = frozenset", 1)[1].split(")", 1)[0]:
    text = text.replace(
        '        "Arceus X",\n    }\n)',
        '        "Arceus X",\n        "Swift",\n    }\n)',
        1,
    )

if '"Swift":' not in text.split("EXECUTOR_BINARY_ONLY_ALIASES", 1)[1][:800]:
    text = text.replace(
        '    "Volt": ["voltexecutor", "volt executor"],\n}',
        '    "Volt": ["voltexecutor", "volt executor"],\n    "Swift": ["swiftexecutor", "swift executor", "swiftdownload"],\n}',
        1,
    )

if "\\proton_mail\\" not in text:
    text = text.replace(
        '    "vk_swiftshader",',
        '    "vk_swiftshader",\n    "\\\\proton_mail\\\\",\n    "\\\\protonpass\\\\",\n    "\\\\proton mail\\\\",',
        1,
    )

APP.write_text(text, encoding="utf-8")
print("Patched app.py")
