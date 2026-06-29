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


def verify_delivery_signature_v2(
    *,
    raw_body: bytes,
    signature_header: str,
    delivery_id: str,
    timestamp_header: str,
    secret: str,
    tolerance_seconds: int = SHOPPEX_SIGNATURE_TOLERANCE_SECONDS,
) -> bool:
    if not secret:
        return False

    delivery_id = str(delivery_id or "").strip()
    timestamp_header = str(timestamp_header or "").strip()
    header = str(signature_header or "").strip()
    if not delivery_id or not timestamp_header or not header:
        return False

    segments = [part.strip() for part in header.split(",")]
    if "v1" not in segments:
        return False

    parts: dict[str, str] = {}
    for part in segments:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        parts[key.strip().lower()] = value.strip()

    timestamp = parts.get("t")
    provided_hash = parts.get("h")
    if timestamp != timestamp_header or not provided_hash:
        return False
    if not re.fullmatch(r"[0-9a-fA-F]{64}", provided_hash):
        return False

    try:
        timestamp_int = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time()) - timestamp_int) > tolerance_seconds:
        return False

    signed_payload = f"{delivery_id}.{timestamp}.".encode("utf-8") + raw_body
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_hash)


def verify_event_webhook(
    raw_body: bytes,
    signature_header: str,
    *,
    delivery_id: str = "",
    timestamp_header: str = "",
) -> bool:
    if not SHOPPEX_WEBHOOK_SECRET:
        return False

    delivery_id = str(delivery_id or "").strip()
    timestamp_header = str(timestamp_header or "").strip()
    if delivery_id and timestamp_header:
        return verify_delivery_signature_v2(
            raw_body=raw_body,
            signature_header=signature_header,
            delivery_id=delivery_id,
            timestamp_header=timestamp_header,
            secret=SHOPPEX_WEBHOOK_SECRET,
        )

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
        for secret in secrets:
            if verify_delivery_signature_v2(
                raw_body=raw_body,
                signature_header=signature_header,
                delivery_id=delivery_id,
                timestamp_header=timestamp_header,
                secret=secret,
            ):
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
        for key in ("product_title", "productTitle", "title"):
            value = container.get(key)
            if value:
                product_candidates.append(str(value))

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
        plan = pricing.plan_by_shoppex_title(candidate)
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


def _event_type(payload: dict) -> str:
    return str(payload.get("event") or payload.get("type") or "").strip().lower()


def _is_subscription_event(payload: dict) -> bool:
    return _event_type(payload).startswith("subscription:")


def extract_subscription_id(payload: dict) -> str | None:
    data = payload.get("data")
    if not isinstance(data, dict):
        data = payload
    subscription = payload.get("subscription")
    if isinstance(subscription, dict):
        for key in ("id", "subscription_id", "subscriptionId", "uniqid"):
            value = subscription.get(key)
            if value:
                return str(value)
    for key in ("subscription_id", "subscriptionId"):
        value = data.get(key) or payload.get(key)
        if value:
            return str(value)
    if _is_subscription_event(payload):
        value = data.get("id") or data.get("uniqid")
        if value:
            return str(value)
    return None


def extract_invoice_id(payload: dict) -> str | None:
    data = payload.get("data")
    if not isinstance(data, dict):
        data = payload

    subscription = payload.get("subscription")
    if isinstance(subscription, dict):
        invoices = subscription.get("invoices") or []
        for invoice in reversed(invoices):
            if not isinstance(invoice, dict):
                continue
            for key in ("uniqid", "invoice_id", "invoiceId", "id"):
                value = invoice.get(key)
                if value:
                    return str(value)

    invoice = payload.get("invoice")
    if isinstance(invoice, dict):
        for key in ("uniqid", "id", "invoice_id", "invoiceId"):
            value = invoice.get(key)
            if value:
                return str(value)

    for container in (payload, data):
        for key in (
            "invoice_id",
            "invoiceId",
            "invoice_db_id",
            "invoiceDbId",
            "invoice_uniqid",
            "invoiceUniqid",
            "uniqid",
            "order_id",
            "orderId",
        ):
            value = container.get(key)
            if value:
                return str(value)

    if not _is_subscription_event(payload):
        for container in (payload, data):
            value = container.get("id")
            if value:
                return str(value)
    return None


def _merge_shoppex_source(payload: dict, source: dict) -> dict:
    merged = dict(payload)
    data = dict(merged.get("data") or {})
    if source.get("custom_fields"):
        data["custom_fields"] = source.get("custom_fields")
    items = source.get("items") or []
    if items:
        data["items"] = items
        first = items[0] if isinstance(items[0], dict) else {}
        if first.get("product_id") and not data.get("product_id"):
            data["product_id"] = first.get("product_id")
        if first.get("product_title") and not data.get("product_title"):
            data["product_title"] = first.get("product_title")
        if first.get("custom_fields"):
            existing = data.get("custom_fields")
            if isinstance(existing, dict) and isinstance(first.get("custom_fields"), dict):
                data["custom_fields"] = {**existing, **first.get("custom_fields")}
            elif not existing:
                data["custom_fields"] = first.get("custom_fields")
    if source.get("product_id") and not data.get("product_id"):
        data["product_id"] = source.get("product_id")
    if source.get("product_title") and not data.get("product_title"):
        data["product_title"] = source.get("product_title")
    if source.get("total") is not None and data.get("total") is None:
        data["total"] = source.get("total")
    if source.get("total_display") is not None and data.get("total_display") is None:
        data["total_display"] = source.get("total_display")
    merged["data"] = data
    return merged


def enrich_payload_from_subscription_api(payload: dict) -> dict:
    if extract_discord_id(payload) and extract_plan_id(payload):
        return payload

    subscription_id = extract_subscription_id(payload)
    if not subscription_id:
        return payload

    try:
        import shoppex_catalog

        subscription = shoppex_catalog.fetch_subscription(subscription_id)
        if not subscription:
            return payload

        merged = dict(payload)
        data = dict(merged.get("data") or {})
        if subscription.get("custom_fields"):
            data["custom_fields"] = subscription.get("custom_fields")

        product = subscription.get("product")
        if isinstance(product, dict):
            if product.get("id") and not data.get("product_id"):
                data["product_id"] = product.get("id")
            if product.get("title") and not data.get("product_title"):
                data["product_title"] = product.get("title")
            if product.get("uniqid") and not data.get("product_uniqid"):
                data["product_uniqid"] = product.get("uniqid")

        invoices = subscription.get("invoices") or []
        paid_invoice = None
        for invoice in reversed(invoices):
            if not isinstance(invoice, dict):
                continue
            status = str(invoice.get("status") or invoice.get("payment_status") or "").upper()
            if status in {"COMPLETED", "PAID", "ACTIVE", "FULFILLED"}:
                paid_invoice = invoice
                break
        if paid_invoice is None and invoices:
            paid_invoice = invoices[-1] if isinstance(invoices[-1], dict) else None

        if isinstance(paid_invoice, dict):
            merged = _merge_shoppex_source({**merged, "data": data}, paid_invoice)
            data = merged["data"]
            invoice_uniqid = paid_invoice.get("uniqid") or paid_invoice.get("id")
            if invoice_uniqid:
                data["invoice_uniqid"] = str(invoice_uniqid)
            merged["invoice"] = paid_invoice
        else:
            merged["data"] = data

        merged["subscription"] = subscription
        return merged
    except Exception as error:
        print(f"Shoppex subscription enrichment failed: {error}", flush=True)
        return payload


def enrich_payload_from_invoice_api(payload: dict) -> dict:
    if extract_discord_id(payload) and extract_plan_id(payload):
        return payload

    invoice_id = extract_invoice_id(payload)
    if not invoice_id:
        return payload

    try:
        import shoppex_catalog

        invoice = shoppex_catalog.fetch_invoice(invoice_id)
        order = shoppex_catalog.fetch_order(invoice_id) if not invoice else None
        source = invoice or order
        if not source:
            return payload

        merged = _merge_shoppex_source(payload, source)
        merged["invoice"] = source
        return merged
    except Exception as error:
        print(f"Shoppex invoice enrichment failed: {error}", flush=True)
        return payload


def enrich_shoppex_payload(payload: dict) -> dict:
    enriched = dict(payload)
    if _is_subscription_event(enriched) or extract_subscription_id(enriched):
        enriched = enrich_payload_from_subscription_api(enriched)

    invoice_id = extract_invoice_id(enriched)
    if invoice_id:
        data = dict(enriched.get("data") or {})
        data.setdefault("uniqid", invoice_id)
        enriched = enrich_payload_from_invoice_api({**enriched, "data": data})
    elif not extract_discord_id(enriched):
        enriched = enrich_payload_from_invoice_api(enriched)

    if not extract_discord_id(enriched) and (
        _is_subscription_event(enriched) or extract_subscription_id(enriched)
    ):
        enriched = enrich_payload_from_subscription_api(enriched)

    return enriched


def fulfillment_complete(result: dict) -> bool:
    role_ok = bool(result.get("role") and result["role"].get("ok"))
    bot_ok = bool(result.get("bot") and result["bot"].get("ok"))
    return role_ok or bot_ok


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


def resolve_plan_id(payload: dict) -> str | None:
    plan_id = extract_plan_id(payload)
    if plan_id:
        return plan_id

    amount_cents = extract_amount_cents(payload)
    if amount_cents:
        plan = pricing.plan_by_price_cents(amount_cents)
        if plan:
            return plan["id"]

    data = payload.get("data")
    if not isinstance(data, dict):
        data = payload

    product_refs: list[str] = []
    for key in ("product_id", "productId", "product_title", "productTitle", "slug"):
        value = data.get(key) or payload.get(key)
        if value:
            product_refs.append(str(value))

    product = data.get("product") or payload.get("product")
    if isinstance(product, dict):
        for key in ("id", "uniqid", "slug", "title"):
            value = product.get(key)
            if value:
                product_refs.append(str(value))

    try:
        import shoppex_catalog

        for product_ref in product_refs:
            plan = shoppex_catalog.find_plan_for_product(product_ref)
            if plan:
                return plan["id"]
    except Exception:
        pass

    return None


def handle_event(payload: dict) -> dict:
    event_type = str(payload.get("event") or payload.get("type") or "").strip().lower()
    if event_type in {
        "order:paid",
        "order:paid:product",
        "subscription:created",
        "subscription:renewed",
        "product:dynamic",
    }:
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
