"""Shoppex purchase resolution and relay to virellobot."""

from __future__ import annotations

import json
from typing import Any

import bot_fulfillment
import pricing
import shoppex
import shoppex_catalog
import site_store


def resolve_shoppex_purchase(payload: dict) -> dict[str, Any]:
    """Resolve discord_id, plan_id, and invoice_id from a Shoppex webhook payload."""
    enriched = shoppex.enrich_shoppex_payload(payload)
    discord_id = shoppex.extract_discord_id(enriched)
    plan_id = shoppex.resolve_plan_id(enriched)
    invoice_id = shoppex.extract_invoice_id(enriched)
    subscription_id = shoppex.extract_subscription_id(enriched)

    if shoppex_catalog.shoppex_api_configured():
        if invoice_id and (not discord_id or not plan_id):
            invoice = shoppex_catalog.fetch_invoice(invoice_id)
            if invoice:
                enriched = shoppex._merge_shoppex_source(enriched, invoice)
                enriched["invoice"] = invoice
                discord_id = discord_id or shoppex.extract_discord_id(enriched)
                plan_id = plan_id or shoppex.resolve_plan_id(enriched)

        if subscription_id and (not discord_id or not plan_id or not invoice_id):
            subscription = shoppex_catalog.fetch_subscription(subscription_id)
            if subscription:
                enriched = shoppex._merge_shoppex_source(enriched, subscription)
                discord_id = discord_id or shoppex.extract_discord_id(enriched)
                plan_id = plan_id or shoppex.resolve_plan_id(enriched)
                invoice_id = invoice_id or shoppex.extract_invoice_id(enriched)

        if not invoice_id and subscription_id:
            subscription = shoppex_catalog.fetch_subscription(subscription_id)
            if subscription:
                enriched = shoppex._merge_shoppex_source(enriched, subscription)
                invoice_id = shoppex.extract_invoice_id(enriched) or invoice_id

    data_block = enriched.get("data") if isinstance(enriched.get("data"), dict) else {}
    custom_fields = (
        data_block.get("custom_fields")
        or data_block.get("customFields")
        or enriched.get("custom_fields")
        or enriched.get("customFields")
    )

    return {
        "discord_id": discord_id,
        "plan_id": plan_id,
        "invoice_id": invoice_id,
        "subscription_id": subscription_id,
        "amount_cents": shoppex.extract_amount_cents(enriched),
        "custom_fields": custom_fields,
        "enriched": enriched,
    }


def relay_purchase_to_bot(
    purchase: dict[str, Any],
    *,
    trust_paid: bool,
) -> dict:
    discord_id = str(purchase.get("discord_id") or "").strip()
    plan_id = str(purchase.get("plan_id") or "").strip()
    invoice_id = str(purchase.get("invoice_id") or "").strip() or None

    if not discord_id.isdigit():
        return {"ok": False, "reason": "missing_discord_id"}
    if not plan_id or not pricing.plan_by_id(plan_id):
        return {"ok": False, "reason": "missing_plan_id"}

    return bot_fulfillment.notify_bot_shoppex_fulfillment(
        discord_id,
        plan_id,
        invoice_id=invoice_id,
        trust_paid=trust_paid,
        custom_fields=purchase.get("custom_fields"),
    )


def license_granted(bot_result: dict | None) -> bool:
    if not bot_result or not bot_result.get("ok"):
        return False
    payload = bot_result.get("payload") or {}
    if payload.get("ok") is False:
        return False
    return bool(payload.get("expiresAt") or payload.get("expires_at"))


def record_scanner_access(
    conn,
    db_execute,
    purchase: dict[str, Any],
    *,
    bot_result: dict | None,
) -> str | None:
    discord_id = purchase.get("discord_id")
    plan_id = purchase.get("plan_id")
    invoice_id = purchase.get("invoice_id")
    if not discord_id or not plan_id:
        return None

    bot_payload = (bot_result or {}).get("payload") or {}
    license_expires_at = pricing.license_expires_at_from_ms(bot_payload.get("expiresAt"))
    if not license_expires_at:
        license_expires_at = pricing.license_expires_at_iso(plan_id)

    if invoice_id:
        site_store.grant_shoppex_access(
            conn,
            db_execute,
            shoppex_invoice_id=invoice_id,
            discord_id=discord_id,
            plan_id=plan_id,
            amount_cents=int(purchase.get("amount_cents") or 0),
            license_expires_at=license_expires_at,
        )
    else:
        site_store.sync_bot_license_grant(
            conn,
            db_execute,
            discord_id=discord_id,
            plan_id=plan_id,
            shoppex_invoice_id=None,
            license_expires_at=license_expires_at,
            expires_at_ms=bot_payload.get("expiresAt"),
            amount_cents=int(purchase.get("amount_cents") or 0),
        )
    return license_expires_at


def fulfillment_log_fields(purchase: dict[str, Any], result: dict) -> str:
    bot = result.get("bot") or {}
    bot_payload = bot.get("payload") or {}
    bot_detail = bot.get("detail") or {}
    return json.dumps(
        {
            "discord_id": purchase.get("discord_id"),
            "plan_id": purchase.get("plan_id"),
            "invoice_id": purchase.get("invoice_id"),
            "bot_ok": bool(bot.get("ok")),
            "bot_reason": bot.get("reason"),
            "bot_detail": bot_detail.get("reason") if isinstance(bot_detail, dict) else bot_detail,
            "license_granted": license_granted(bot),
            "expires_at": bot_payload.get("expiresAt"),
            "role_fallback_ok": bool((result.get("role_fallback") or {}).get("ok")),
        },
    )
