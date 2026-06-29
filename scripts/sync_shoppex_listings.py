#!/usr/bin/env python3
"""Create or update Shoppex listings from backend/pricing.py."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import shoppex_catalog  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Virello pricing plans to Shoppex products.")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without calling Shoppex.")
    parser.add_argument("--plan", help="Sync a single plan id, e.g. monthly.")
    args = parser.parse_args()

    if not args.dry_run and not shoppex_catalog.shoppex_api_configured():
        print("SHOPPEX_API_KEY is not set. Export it or pass --dry-run.", file=sys.stderr)
        return 1

    if args.plan:
        from pricing import plan_by_id

        plan = plan_by_id(args.plan)
        if plan is None:
            print(f"Unknown plan: {args.plan}", file=sys.stderr)
            return 1
        results = [shoppex_catalog.sync_plan(plan, dry_run=args.dry_run)]
    else:
        results = shoppex_catalog.sync_all_plans(dry_run=args.dry_run)

    print(json.dumps(results, indent=2))
    print()
    print("After sync:")
    print("1. In Shoppex, enable Bitcoin, Litecoin, USDT, Solana, and PayPal F&F on these products.")
    print("2. In Shoppex -> Settings -> Webhooks, add your Render backend URL:")
    print("   POST https://virello-secure.onrender.com/webhooks/shoppex")
    print("   Events: order:paid, subscription:created, subscription:cancelled")
    print("3. On Render, set SHOPPEX_WEBHOOK_SECRET from that endpoint.")
    print("4. On Cloudflare Pages, set VITE_SHOPPEX_STORE_URL=https://officialvirello.myshoppex.io")
    print("If Cloudflare Error 1010 appears, set SHOPPEX_USER_AGENT and retry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
