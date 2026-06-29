"""Stripe Checkout session helpers (stdlib HTTP — no SDK required)."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://virello-secure.pages.dev").rstrip("/")


def stripe_configured() -> bool:
    return bool(STRIPE_SECRET_KEY)


def _stripe_request(method: str, path: str, data: dict | None = None) -> dict:
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe is not configured")
    body = urllib.parse.urlencode(data).encode("utf-8") if data else None
    request = urllib.request.Request(
        f"https://api.stripe.com/v1{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {STRIPE_SECRET_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def create_checkout_session(*, price_id: str, plan_id: str, discord_id: str, customer_email: str | None = None) -> dict:
    payload = {
        "mode": "payment",
        "success_url": f"{FRONTEND_URL}/purchase?checkout=success&plan={urllib.parse.quote(plan_id)}",
        "cancel_url": f"{FRONTEND_URL}/purchase?checkout=cancel",
        "client_reference_id": discord_id,
        "metadata[plan_id]": plan_id,
        "metadata[discord_id]": discord_id,
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "payment_method_types[0]": "card",
    }
    if customer_email:
        payload["customer_email"] = customer_email
    return _stripe_request("POST", "/checkout/sessions", payload)
