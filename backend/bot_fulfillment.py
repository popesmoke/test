"""Notify the Virello Discord bot after Shoppex fulfillment."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def bot_fulfillment_configured() -> bool:
    return bool(_fulfillment_url() and _fulfillment_secret())


def _fulfillment_url() -> str:
    base = os.getenv("BOT_FULFILLMENT_URL", "").strip().rstrip("/")
    if base:
        return f"{base}/webhooks/shoppex-fulfill"
    return ""


def _fulfillment_secret() -> str:
    return (
        os.getenv("BOT_FULFILLMENT_SECRET", "").strip()
        or os.getenv("SHOPPEX_FULFILLMENT_SECRET", "").strip()
    )


def notify_bot_shoppex_revoke(
    discord_id: str,
    *,
    invoice_id: str | None = None,
    reason: str = "Shoppex subscription ended",
) -> dict:
    url = _fulfillment_url()
    secret = _fulfillment_secret()
    normalized_id = str(discord_id or "").strip()

    if not url or not secret:
        return {"ok": False, "reason": "not_configured"}
    if not normalized_id.isdigit():
        return {"ok": False, "reason": "invalid_payload"}

    body = json.dumps(
        {
            "action": "revoke",
            "discord_id": normalized_id,
            "invoice_id": invoice_id,
            "reason": reason,
        },
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Virello-Fulfillment-Secret": secret,
            "User-Agent": "VirelloScannerBackend/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return {"ok": True, "status": response.status, "payload": payload}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            parsed = {"detail": detail[:500]}
        return {
            "ok": False,
            "reason": f"http_{error.code}",
            "detail": parsed,
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return {"ok": False, "reason": "request_failed", "detail": str(error)}


def notify_bot_shoppex_fulfillment(
    discord_id: str,
    plan_id: str,
    *,
    invoice_id: str | None = None,
) -> dict:
    url = _fulfillment_url()
    secret = _fulfillment_secret()
    normalized_id = str(discord_id or "").strip()
    normalized_plan = str(plan_id or "").strip()

    if not url or not secret:
        return {"ok": False, "reason": "not_configured"}
    if not normalized_id.isdigit() or not normalized_plan:
        return {"ok": False, "reason": "invalid_payload"}

    body = json.dumps(
        {
            "discord_id": normalized_id,
            "plan_id": normalized_plan,
            "invoice_id": invoice_id,
        },
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Virello-Fulfillment-Secret": secret,
            "User-Agent": "VirelloScannerBackend/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return {"ok": True, "status": response.status, "payload": payload}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            parsed = {"detail": detail[:500]}
        return {
            "ok": False,
            "reason": f"http_{error.code}",
            "detail": parsed,
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return {"ok": False, "reason": "request_failed", "detail": str(error)}
