"""Grant Discord guild roles after Shoppex or manual fulfillment."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DISCORD_API_BASE = "https://discord.com/api/v10"


def grant_access_role(discord_id: str) -> dict:
    guild_id = os.getenv("DISCORD_GUILD_ID", "1510614253508493373").strip()
    role_id = os.getenv("DISCORD_ACCESS_ROLE_ID", "1510614274299531334").strip()
    bot_token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN", "")
    normalized_id = str(discord_id or "").strip()

    if not guild_id or not role_id or not bot_token:
        return {"ok": False, "reason": "not_configured"}
    if not normalized_id.isdigit():
        return {"ok": False, "reason": "invalid_discord_id"}

    request = urllib.request.Request(
        f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{normalized_id}/roles/{role_id}",
        data=b"{}",
        method="PUT",
        headers={
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "VirelloScannerBackend/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            return {"ok": True, "status": response.status}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        reason = "user_not_in_guild" if error.code == 404 else f"http_{error.code}"
        return {"ok": False, "reason": reason, "detail": detail[:500]}
