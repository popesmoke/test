"""Shoppex product definitions derived from the pricing catalog."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pricing

SHOPPEX_API_BASE = os.getenv("SHOPPEX_API_BASE", "https://api.shoppex.io").rstrip("/")
SHOPPEX_API_KEY = os.getenv("SHOPPEX_API_KEY", "").strip()
SHOPPEX_USER_AGENT = os.getenv(
    "SHOPPEX_USER_AGENT",
    "Shoppex-Developer-Client/1.0 (Virello; +https://virello-secure.pages.dev)",
).strip()
SHOPPEX_GATEWAYS = [
    item.strip().upper()
    for item in os.getenv(
        "SHOPPEX_GATEWAYS",
        "BITCOIN,LITECOIN,USDT,SOLANA,PAYPAL",
    ).split(",")
    if item.strip()
]
SHOPPEX_DYNAMIC_WEBHOOK_URL = os.getenv("SHOPPEX_DYNAMIC_WEBHOOK_URL", "").strip()
SHOPPEX_DYNAMIC_WEBHOOK_SECRET = os.getenv("SHOPPEX_DYNAMIC_WEBHOOK_SECRET", "").strip()
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "1510614253508493373").strip()
DISCORD_ACCESS_ROLE_ID = os.getenv("DISCORD_ACCESS_ROLE_ID", "1510614274299531334").strip()


def shoppex_api_configured() -> bool:
    return bool(SHOPPEX_API_KEY)


def _api_headers(*, with_json: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {SHOPPEX_API_KEY}",
        "Accept": "application/json",
        "User-Agent": SHOPPEX_USER_AGENT,
    }
    if with_json:
        headers["Content-Type"] = "application/json"
    return headers


def _format_api_error(method: str, path: str, status: int, detail: str) -> str:
    if "error_1010" in detail or "browser_signature_banned" in detail:
        return (
            f"Shoppex API {method} {path} failed ({status}): Cloudflare blocked the request "
            f"(Error 1010). Retry after updating, or set SHOPPEX_USER_AGENT to a custom value. "
            f"Detail: {detail[:400]}"
        )
    return f"Shoppex API {method} {path} failed ({status}): {detail}"


def _api_request(method: str, path: str, payload: dict | None = None) -> dict:
    if not SHOPPEX_API_KEY:
        raise RuntimeError("SHOPPEX_API_KEY is not configured")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{SHOPPEX_API_BASE}{path}",
        data=body,
        method=method,
        headers=_api_headers(with_json=payload is not None),
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(_format_api_error(method, path, error.code, detail)) from error


def list_products() -> list[dict]:
    payload = _api_request("GET", "/dev/v1/products?limit=100")
    if isinstance(payload, list):
        return payload
    return list(payload.get("data") or payload.get("products") or [])


def fetch_invoice(uniqid: str) -> dict | None:
    normalized = str(uniqid or "").strip()
    if not normalized:
        return None
    try:
        payload = _api_request("GET", f"/dev/v1/invoices/{normalized}")
    except RuntimeError:
        return None
    if isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload if isinstance(payload, dict) else None


def fetch_order(order_id: str) -> dict | None:
    normalized = str(order_id or "").strip()
    if not normalized:
        return None
    try:
        payload = _api_request("GET", f"/dev/v1/orders/{normalized}")
    except RuntimeError:
        return None
    if isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload if isinstance(payload, dict) else None


def _product_description(plan: dict) -> str:
    features = "\n".join(f"• {feature}" for feature in plan.get("features", []))
    return (
        f"{plan['blurb']}\n\n"
        f"Includes:\n{features}\n\n"
        "At checkout, enter your **Discord user ID** (17–20 digits). "
        "Join the Virello Discord server first, then complete payment — your reviewer role is granted automatically."
    )


def build_product_payload(plan: dict) -> dict:
    price = round(plan["price_cents"] / 100, 2)
    product_type = str(plan.get("shoppex_type") or "SERVICE").upper()
    payload: dict = {
        "title": plan["title"],
        "price": price,
        "currency": "USD",
        "type": product_type,
        "description": _product_description(plan),
        "slug": plan.get("shoppex_slug"),
        "gateways": SHOPPEX_GATEWAYS,
        "discord_integration": bool(DISCORD_GUILD_ID and DISCORD_ACCESS_ROLE_ID),
        "discord_set_role": bool(DISCORD_GUILD_ID and DISCORD_ACCESS_ROLE_ID),
        "discord_server_id": DISCORD_GUILD_ID or None,
        "discord_role_id": DISCORD_ACCESS_ROLE_ID or None,
        "discord_remove_role": False,
        "discord_optional": False,
        "delivery_instructions": {
            "enabled": False,
            "required": False,
        },
        "custom_fields": [
            {
                "name": "Discord user ID",
                "key": "discord_user_id",
                "type": "text",
                "required": True,
                "placeholder": "123456789012345678",
            },
        ],
        "sort_priority": 100 - plan.get("months", 1),
        "unlisted": False,
        "private": False,
    }

    if product_type in {"SUBSCRIPTION", "SUBSCRIPTION_V2"}:
        payload["recurring_interval"] = plan.get("shoppex_recurring_interval", "MONTH")
        payload["recurring_interval_count"] = int(plan.get("shoppex_recurring_interval_count") or 1)

    license_period = plan.get("shoppex_license_period")
    if license_period:
        payload["license_period"] = license_period
        payload["licensing_enabled"] = True

    if SHOPPEX_DYNAMIC_WEBHOOK_URL and product_type not in {"SUBSCRIPTION", "SUBSCRIPTION_V2"}:
        payload["type"] = "DYNAMIC"
        payload["dynamic_webhook"] = SHOPPEX_DYNAMIC_WEBHOOK_URL
        if SHOPPEX_DYNAMIC_WEBHOOK_SECRET:
            payload["dynamic_webhook_secret"] = SHOPPEX_DYNAMIC_WEBHOOK_SECRET

    existing_id = pricing.shoppex_product_id(plan["id"])
    if existing_id:
        payload["metadata"] = {"plan_id": plan["id"], "existing_product_id": existing_id}
    return payload


def find_product_id_by_slug(slug: str) -> str | None:
    normalized = str(slug or "").strip().lower()
    if not normalized:
        return None
    for product in list_products():
        product_slug = str(product.get("slug") or "").strip().lower()
        if product_slug == normalized:
            return str(product.get("id") or product.get("uniqid") or "").strip() or None
    return None


def sync_plan(plan: dict, *, dry_run: bool = False) -> dict:
    payload = build_product_payload(plan)
    if dry_run:
        return {"plan_id": plan["id"], "action": "dry_run", "payload": payload}

    existing_id = pricing.shoppex_product_id(plan["id"])
    if not existing_id:
        existing_id = find_product_id_by_slug(str(plan.get("shoppex_slug") or ""))

    if existing_id:
        response = _api_request("PATCH", f"/dev/v1/products/{existing_id}", payload)
        action = "updated"
    else:
        response = _api_request("POST", "/dev/v1/products", payload)
        action = "created"

    product = response.get("data") if isinstance(response.get("data"), dict) else response
    product_id = str(product.get("id") or product.get("uniqid") or "").strip()
    dynamic_secret = product.get("dynamic_webhook_secret") or product.get("dynamicWebhookSecret")
    return {
        "plan_id": plan["id"],
        "action": action,
        "product_id": product_id,
        "slug": product.get("slug") or plan.get("shoppex_slug"),
        "dynamic_webhook_secret": dynamic_secret,
        "url": pricing.shoppex_product_url(plan),
    }


def sync_all_plans(*, dry_run: bool = False) -> list[dict]:
    results: list[dict] = []
    for plan in pricing.all_plans():
        if not plan.get("shoppex"):
            continue
        results.append(sync_plan(plan, dry_run=dry_run))
    return results
