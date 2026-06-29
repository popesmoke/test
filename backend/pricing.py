"""Public pricing catalog — synced with web dashboard, Shoppex store, and Discord bot."""

from __future__ import annotations

import calendar
from datetime import datetime, timezone

PERSONAL_PLANS = [
    {
        "id": "monthly",
        "tier": "personal",
        "title": "Monthly Personal",
        "blurb": "Low-commitment entry. Run unlimited scans for a single reviewer seat — ideal for trying Virello or occasional screenshares.",
        "price": "$8.99",
        "price_cents": 899,
        "period": "/ month",
        "months": 1,
        "slots": 1,
        "featured": False,
        "stripe": True,
        "shoppex": True,
        "shoppex_slug": "virello-monthly-personal",
        "shoppex_type": "SUBSCRIPTION",
        "shoppex_recurring_interval": "MONTH",
        "shoppex_recurring_interval_count": 1,
        "features": [
            "1 reviewer seat",
            "Unlimited PIN generation",
            "Full executor & forensic scans",
            "Scanner updates included",
            "Discord support",
        ],
    },
    {
        "id": "semiannual",
        "tier": "personal",
        "title": "6-Month Personal",
        "blurb": "Best personal value vs monthly. Lock in six months of access and save over paying month-to-month.",
        "price": "$39.99",
        "price_cents": 3999,
        "period": "/ 6 months",
        "months": 6,
        "slots": 1,
        "featured": True,
        "stripe": True,
        "shoppex": True,
        "shoppex_slug": "virello-6month-personal",
        "shoppex_type": "SERVICE",
        "shoppex_license_period": "180d",
        "features": [
            "1 reviewer seat",
            "Save ~26% vs monthly",
            "Unlimited PIN generation",
            "Priority scanner updates",
            "Discord support",
        ],
    },
    {
        "id": "yearly",
        "tier": "personal",
        "title": "Yearly Personal",
        "blurb": "Lowest personal rate. One payment covers a full year — built for reviewers who screen regularly.",
        "price": "$69.99",
        "price_cents": 6999,
        "period": "/ year",
        "months": 12,
        "slots": 1,
        "featured": False,
        "stripe": True,
        "shoppex": True,
        "shoppex_slug": "virello-yearly-personal",
        "shoppex_type": "SERVICE",
        "shoppex_license_period": "365d",
        "features": [
            "1 reviewer seat",
            "Lowest personal price per month",
            "Unlimited PIN generation",
            "Early access to scanner features",
            "Discord support",
        ],
    },
]

ENTERPRISE_PLANS = [
    {
        "id": "duo",
        "tier": "enterprise",
        "title": "Duo Team",
        "blurb": "Two reviewer seats under one license. Share console access with a partner mod without paying enterprise rates.",
        "price": "$17.99",
        "price_cents": 1799,
        "period": "/ month",
        "months": 1,
        "slots": 2,
        "featured": False,
        "stripe": True,
        "shoppex": True,
        "shoppex_slug": "virello-duo-team",
        "shoppex_type": "SUBSCRIPTION",
        "shoppex_recurring_interval": "MONTH",
        "shoppex_recurring_interval_count": 1,
        "features": [
            "2 reviewer seats",
            "Shared team workflow",
            "Unlimited PIN generation",
            "Custom report branding",
            "Priority Discord support",
        ],
    },
    {
        "id": "enterprise_10",
        "tier": "enterprise",
        "title": "Enterprise (10 seats)",
        "blurb": "For growing communities. Ten reviewer seats, team management, and branding — priced below comparable tools.",
        "price": "$64.99",
        "price_cents": 6499,
        "period": "/ 6 months",
        "months": 6,
        "slots": 10,
        "featured": True,
        "stripe": True,
        "shoppex": True,
        "shoppex_slug": "virello-enterprise-10",
        "shoppex_type": "SERVICE",
        "shoppex_license_period": "180d",
        "features": [
            "10 reviewer seats",
            "Enterprise seat management",
            "Unlimited PIN generation",
            "Custom branding on reports",
            "Priority support lane",
        ],
    },
    {
        "id": "enterprise_20",
        "tier": "enterprise",
        "title": "Enterprise+ (20 seats)",
        "blurb": "Maximum team capacity. Twenty seats for large staff teams with the best per-seat rate in the lineup.",
        "price": "$89.99",
        "price_cents": 8999,
        "period": "/ 6 months",
        "months": 6,
        "slots": 20,
        "featured": False,
        "stripe": True,
        "shoppex": True,
        "shoppex_slug": "virello-enterprise-20",
        "shoppex_type": "SERVICE",
        "shoppex_license_period": "180d",
        "features": [
            "20 reviewer seats",
            "Full enterprise management",
            "Unlimited PIN generation",
            "Custom branding on reports",
            "Dedicated priority support",
        ],
    },
]

SHOPPEX_PAYMENTS = [
    {"id": "bitcoin", "label": "Bitcoin"},
    {"id": "litecoin", "label": "Litecoin"},
    {"id": "usdt", "label": "USDT"},
    {"id": "solana", "label": "Solana"},
    {"id": "paypal_ff", "label": "PayPal Friends & Family"},
]

DISCORD_TICKET_PAYMENTS = [
    {"id": "ethereum", "label": "Ethereum"},
    {"id": "greek_paysafe", "label": "Greek Paysafe"},
    {"id": "discord", "label": "Discord payment"},
]


def all_plans() -> list[dict]:
    return [*PERSONAL_PLANS, *ENTERPRISE_PLANS]


def plan_by_id(plan_id: str) -> dict | None:
    for plan in all_plans():
        if plan["id"] == plan_id:
            return plan
    return None


def plan_by_shoppex_slug(slug: str) -> dict | None:
    normalized = str(slug or "").strip().lower()
    if not normalized:
        return None
    for plan in all_plans():
        if str(plan.get("shoppex_slug") or "").lower() == normalized:
            return plan
    return None


def plan_by_shoppex_title(title: str) -> dict | None:
    normalized = str(title or "").strip().lower()
    if not normalized:
        return None
    for plan in all_plans():
        plan_title = str(plan.get("title") or "").strip().lower()
        if plan_title == normalized:
            return plan
        if plan_title and plan_title in normalized:
            return plan
        slug = str(plan.get("shoppex_slug") or "").replace("-", " ")
        if slug and slug in normalized:
            return plan
    return None


def plan_by_price_cents(amount_cents: int) -> dict | None:
    if amount_cents <= 0:
        return None
    matches = [plan for plan in all_plans() if int(plan.get("price_cents") or 0) == amount_cents]
    if len(matches) == 1:
        return matches[0]
    return None


def plan_by_shoppex_product_id(product_id: str) -> dict | None:
    normalized = str(product_id or "").strip()
    if not normalized:
        return None
    for plan in all_plans():
        configured = shoppex_product_id(plan["id"])
        if configured and configured == normalized:
            return plan
    return None


def pricing_payload() -> dict:
    store_url = shoppex_store_url()
    return {
        "personal": PERSONAL_PLANS,
        "enterprise": ENTERPRISE_PLANS,
        "shoppex_payments": SHOPPEX_PAYMENTS,
        "discord_ticket_payments": DISCORD_TICKET_PAYMENTS,
        "alt_payments": [*SHOPPEX_PAYMENTS, *DISCORD_TICKET_PAYMENTS],
        "stripe_enabled": bool(_stripe_secret()),
        "shoppex_enabled": bool(store_url),
        "shoppex_store_url": store_url,
        "shoppex_plans": [
            {
                "plan_id": plan["id"],
                "title": plan["title"],
                "price": plan["price"],
                "period": plan["period"],
                "slug": plan.get("shoppex_slug"),
                "url": shoppex_product_url(plan),
            }
            for plan in all_plans()
            if plan.get("shoppex")
        ],
    }


def _stripe_secret() -> str:
    import os

    return os.getenv("STRIPE_SECRET_KEY", "").strip()


def shoppex_store_url() -> str:
    import os

    return os.getenv("SHOPPEX_STORE_URL", "https://officialvirello.myshoppex.io").strip().rstrip("/")


def shoppex_product_url(plan: dict) -> str:
    store_url = shoppex_store_url()
    slug = str(plan.get("shoppex_slug") or "").strip()
    if not store_url or not slug:
        return ""
    return f"{store_url}/product/{slug}"


def shoppex_product_id(plan_id: str) -> str | None:
    import os

    key = f"SHOPPEX_PRODUCT_{plan_id.upper()}"
    value = os.getenv(key, "").strip()
    return value or None


def stripe_price_id(plan_id: str) -> str | None:
    import os

    key = f"STRIPE_PRICE_{plan_id.upper()}"
    value = os.getenv(key, "").strip()
    return value or None


def add_months(dt: datetime, months: int) -> datetime:
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(dt.day, last_day)
    return dt.replace(year=year, month=month, day=day, tzinfo=dt.tzinfo)


def license_expires_at_iso(plan_id: str, *, base: datetime | None = None) -> str | None:
    plan = plan_by_id(plan_id)
    if not plan:
        return None
    start = base or datetime.now(timezone.utc)
    expires = add_months(start, int(plan.get("months") or 1))
    return expires.isoformat().replace("+00:00", "Z")


def license_expires_at_from_ms(expires_at_ms: int | float | None) -> str | None:
    if expires_at_ms is None:
        return None
    try:
        value = float(expires_at_ms)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    seconds = value / 1000 if value > 1_000_000_000_000 else value
    expires = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return expires.isoformat().replace("+00:00", "Z")
