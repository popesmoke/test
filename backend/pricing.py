"""Public pricing catalog — synced with web dashboard and Discord bot."""

from __future__ import annotations

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
        "features": [
            "20 reviewer seats",
            "Full enterprise management",
            "Unlimited PIN generation",
            "Custom branding on reports",
            "Dedicated priority support",
        ],
    },
]

ALT_PAYMENT_METHODS = [
    {"id": "paypal", "label": "PayPal"},
    {"id": "greek_paysafe", "label": "Greek Paysafe"},
    {"id": "litecoin", "label": "Litecoin"},
    {"id": "ethereum", "label": "Ethereum"},
]


def all_plans() -> list[dict]:
    return [*PERSONAL_PLANS, *ENTERPRISE_PLANS]


def plan_by_id(plan_id: str) -> dict | None:
    for plan in all_plans():
        if plan["id"] == plan_id:
            return plan
    return None


def pricing_payload() -> dict:
    return {
        "personal": PERSONAL_PLANS,
        "enterprise": ENTERPRISE_PLANS,
        "alt_payments": ALT_PAYMENT_METHODS,
        "stripe_enabled": bool(_stripe_secret()),
    }


def _stripe_secret() -> str:
    import os

    return os.getenv("STRIPE_SECRET_KEY", "").strip()


def stripe_price_id(plan_id: str) -> str | None:
    import os

    key = f"STRIPE_PRICE_{plan_id.upper()}"
    value = os.getenv(key, "").strip()
    return value or None
