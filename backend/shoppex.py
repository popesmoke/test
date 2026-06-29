"""Shoppex webhook verification and order fulfillment."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time

import pricing

SHOPPEX_WEBHOOK_SECRET = os.getenv("SHOPPEX_WEBHOOK_SECRET", "").strip()


def _dynamic_webhook_secrets() -> list[str]:
    raw = os.getenv("SHOPPEX_DYNAMIC_WEBHOOK_SECRET", "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


SHOPPEX_SIGNATURE_TOLERANCE_SECONDS = int(os.getenv("SHOPPEX_SIGNATURE_TOLERANCE_SECONDS", "300"))


def shoppex_configured() -> bool:
    return bool(SHOPPEX_WEBHOOK_SECRET or _dynamic_webhook_secrets())


def verify_signature_v2(
    *,
    raw_body: bytes,
    signature_header: str,
    secret: str,
    tolerance_seconds: int = SHOPPEX_SIGNATURE_TOLERANCE_SECONDS,
) -> bool:
    if not secret:
        return False
    header = str(signature_header or "").strip()
    if not header:
        return False

    timestamp = None
    provided_hash = None
    for part in header.split(","):
        key, _, value = part.partition("=")
        key = key.strip().lower()
        value = value.strip()
        if key == "t":
            timestamp = value
        elif key == "h":
            provided_hash = value

    if not timestamp or not provided_hash:
        match = re.search(r"t=(\d+).*h=([a-fA-F0-9]+)", header)
        if not match:
            return False
        timestamp, provided_hash = match.group(1), match.group(2)

    try:
        timestamp_int = int(timestamp)
    except ValueError:
        return False

    if abs(int(time.time()) - timestamp_int) > tolerance_seconds:
        return False

    signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_hash)


def verify_event_webhook(raw_body: bytes, signature_header: str) -> bool:
    return verify_signature_v2(
        raw_body=raw_body,
        signature_header=signature_header,
        secret=SHOPPEX_WEBHOOK_SECRET,
    )


def verify_dynamic_webhook(
    raw_body: bytes,
    signature_header: str,
    *,
    delivery_id: str = "",
    timestamp_header: str = "",
) -> bool:
    secrets = _dynamic_webhook_secrets()
    if not secrets:
        return False

    delivery_id = str(delivery_id or "").strip()
    timestamp_header = str(timestamp_header or "").strip()
    if delivery_id and timestamp_header:
        try:
            timestamp_int = int(timestamp_header)
        except ValueError:
            return False
        if abs(int(time.time()) - timestamp_int) > SHOPPEX_SIGNATURE_TOLERANCE_SECONDS:
            return False

        header = str(signature_header or "").strip()
        provided_hash = None
        for part in header.split(","):
            key, _, value = part.partition("=")
            if key.strip().lower() == "h":
                provided_hash = value.strip()
                break
        if not provided_hash:
            match = re.search(r"h=([a-fA-F0-9]+)", header)
            provided_hash = match.group(1) if match else None
        if not provided_hash:
            return False

        signed_payload = f"{delivery_id}.{timestamp_header}.{raw_body.decode('utf-8')}".encode("utf-8")
        for secret in secrets:
            expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, provided_hash):
                return True
        return False

    return any(
        verify_signature_v2(
            raw_body=raw_body,
            signature_header=signature_header,
            secret=secret,
        )
        for secret in secrets
    )


def _collect_custom_field_candidates(custom_fields) -> list:
    candidates: list = []
    if isinstance(custom_fields, dict):
        for key, value in custom_fields.items():
            key_text = str(key).strip().lower()
            if "discord" in key_text:
                candidates.append(value)
        for key in (
            "discord_id",
            "discordId",
            "discord_user_id",
            "discordUserId",
            "Discord user ID",
            "Discord ID",
            "discord user id",
            "discord id",
        ):
            if custom_fields.get(key):
                candidates.append(custom_fields.get(key))
    elif isinstance(custom_fields, list):
        for field in custom_fields:
            if not isinstance(field, dict):
                continue
            name = str(field.get("name") or field.get("key") or "").strip().lower()
            if "discord" in name:
                candidates.append(field.get("value"))
    return candidates


def _walk_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        items: list[str] = []
        for key, nested in value.items():
            items.append(str(key))
            items.extend(_walk_strings(nested))
        return items
    if isinstance(value, list):
        items: list[str] = []
        for nested in value:
            items.extend(_walk_strings(nested))
        return items
    if value is not None:
        return [str(value)]
    return []


def extract_discord_id(payload: dict) -> str | None:
    candidates = [
        payload.get("discord_id"),
        payload.get("discordId"),
        payload.get("discord_user_id"),
        payload.get("discordUserId"),
        payload.get("customer_discord_id"),
        payload.get("customerDiscordId"),
    ]

    for key in ("custom_fields", "customFields"):
        candidates.extend(_collect_custom_field_candidates(payload.get(key)))

    line_item = payload.get("line_item") or payload.get("lineItem")
    if isinstance(line_item, dict):
        for key in ("custom_fields", "customFields"):
            candidates.extend(_collect_custom_field_candidates(line_item.get(key)))

    invoice = payload.get("invoice")
    if isinstance(invoice, dict):
        for key in ("custom_fields", "customFields"):
            candidates.extend(_collect_custom_field_candidates(invoice.get(key)))
        for item in invoice.get("items") or []:
            if isinstance(item, dict):
                for key in ("custom_fields", "customFields"):
                    candidates.extend(_collect_custom_field_candidates(item.get(key)))

    data = payload.get("data")
    if isinstance(data, dict):
        candidates.extend(
            [
                data.get("discord_id"),
                data.get("discordId"),
                data.get("discord_user_id"),
                data.get("discordUserId"),
                data.get("customer_discord_id"),
                data.get("customerDiscordId"),
            ],
        )
        discord = data.get("discord")
        if isinstance(discord, dict):
            candidates.extend(
                [
                    discord.get("id"),
                    discord.get("user_id"),
                    discord.get("userId"),
                ],
            )
        customer = data.get("customer")
        if isinstance(customer, dict):
            candidates.extend(
                [
                    customer.get("discord_id"),
                    customer.get("discordId"),
                ],
            )
        for key in ("custom_fields", "customFields"):
            candidates.extend(_collect_custom_field_candidates(data.get(key)))

        nested_line_item = data.get("line_item") or data.get("lineItem")
        if isinstance(nested_line_item, dict):
            for key in ("custom_fields", "customFields"):
                candidates.extend(_collect_custom_field_candidates(nested_line_item.get(key)))

        for item in data.get("items") or []:
            if isinstance(item, dict):
                for key in ("custom_fields", "customFields"):
                    candidates.extend(_collect_custom_field_candidates(item.get(key)))

    for candidate in candidates:
        normalized = _normalize_discord_id(candidate)
        if normalized:
            return normalized

    for text in _walk_strings(payload):
        normalized = _normalize_discord_id(text)
        if normalized:
            return normalized
    return None


def _normalize_discord_id(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d{17,20}", text):
        return text
    return None


def extract_plan_id(payload: dict) -> str | None:
    data = payload.get("data")
    if not isinstance(data, dict):
        data = payload

    for key in ("plan_id", "planId"):
        plan_id = str(data.get(key) or payload.get(key) or "").strip()
        if plan_by_id_safe(plan_id):
            return plan_id

    product_candidates: list[str] = []
    for key in ("product_id", "productId", "product_uniqid", "productUniqid", "slug"):
        value = data.get(key) or payload.get(key)
        if value:
            product_candidates.append(str(value))

    for container in (data, payload):
        line_item = container.get("line_item") or container.get("lineItem")
        if isinstance(line_item, dict):
            for key in ("product_id", "productId", "product_slug", "productSlug", "product_title", "productTitle"):
                value = line_item.get(key)
                if value:
                    product_candidates.append(str(value))

        product = container.get("product")
        if isinstance(product, dict):
            for key in ("id", "uniqid", "slug", "title"):
                value = product.get(key)
                if value:
                    product_candidates.append(str(value))

    for candidate in product_candidates:
        plan = pricing.plan_by_shoppex_product_id(candidate)
        if plan:
            return plan["id"]
        slug = candidate.rsplit("/", 1)[-1].strip().lower()
        plan = pricing.plan_by_shoppex_slug(slug)
        if plan:
            return plan["id"]

    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        plan_id = str(metadata.get("plan_id") or metadata.get("planId") or "").strip()
        if plan_by_id_safe(plan_id):
            return plan_id
    return None


def plan_by_id_safe(plan_id: str) -> bool:
    return pricing.plan_by_id(plan_id) is not None


def extract_invoice_id(payload: dict) -> str | None:
    data = payload.get("data")
    if not isinstance(data, dict):
        data = payload
    for container in (payload, data):
        for key in (
            "invoice_id",
            "invoiceId",
            "invoice_db_id",
            "invoiceDbId",
            "id",
            "uniqid",
            "order_id",
            "orderId",
        ):
            value = container.get(key)
            if value:
                return str(value)

    invoice = payload.get("invoice")
    if isinstance(invoice, dict):
        for key in ("uniqid", "id", "invoice_id", "invoiceId"):
            value = invoice.get(key)
            if value:
                return str(value)
    return None


def enrich_payload_from_invoice_api(payload: dict) -> dict:
    if extract_discord_id(payload):
        return payload

    invoice_id = extract_invoice_id(payload)
    if not invoice_id:
        return payload

    try:
        import shoppex_catalog

        invoice = shoppex_catalog.fetch_invoice(invoice_id)
        if not invoice:
            return payload

        merged = dict(payload)
        data = dict(merged.get("data") or {})
        if invoice.get("custom_fields"):
            data["custom_fields"] = invoice.get("custom_fields")
        if invoice.get("items"):
            data["items"] = invoice.get("items")
        if invoice.get("product_id") and not data.get("product_id"):
            data["product_id"] = invoice.get("product_id")
        if invoice.get("product_title") and not data.get("product_title"):
            data["product_title"] = invoice.get("product_title")
        merged["data"] = data
        merged["invoice"] = invoice
        return merged
    except Exception:
        return payload


def extract_amount_cents(payload: dict) -> int:
    data = payload.get("data")
    if not isinstance(data, dict):
        data = payload
    for key in ("total", "amount", "price"):
        value = data.get(key)
        if value is None:
            continue
        try:
            number = float(value)
            if number > 1000:
                return int(number)
            return int(round(number * 100))
        except (TypeError, ValueError):
            continue
    plan_id = extract_plan_id(payload)
    if plan_id:
        plan = pricing.plan_by_id(plan_id)
        if plan:
            return int(plan["price_cents"])
    return 0


def handle_event(payload: dict) -> dict:
    event_type = str(payload.get("event") or payload.get("type") or "").strip().lower()
    if event_type in {"order:paid", "order:paid:product", "subscription:created", "subscription:renewed"}:
        return {"action": "fulfill", "payload": payload}
    if event_type in {"subscription:cancelled", "order:cancelled", "order:disputed"}:
        return {"action": "revoke", "payload": payload}
    return {"action": "ignore", "payload": payload}


def dynamic_fulfillment_response(plan: dict | None) -> dict:
    title = plan["title"] if plan else "Virello license"
    return {
        "service_text": (
            f"{title} activated. Join the Virello Discord if you have not already — "
            "your reviewer role and console access are granted automatically after payment."
        ),
        "dynamic_response": {
            "plan_id": plan["id"] if plan else None,
            "product": "virello-scanner",
        },
    }


def parse_json(raw_body: bytes) -> dict:
    return json.loads(raw_body.decode("utf-8"))
