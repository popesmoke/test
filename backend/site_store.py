"""Site content persistence: changelog, alerts, settings."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from pricing import pricing_payload


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def init_site_tables(conn, db_execute, id_column: str) -> None:
    db_execute(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS site_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """,
    )
    db_execute(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS site_changelog (
            id {id_column},
            version TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            published_at TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT,
            is_published INTEGER NOT NULL DEFAULT 0
        )
        """,
    )
    db_execute(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS site_alerts (
            id {id_column},
            message TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            active INTEGER NOT NULL DEFAULT 1,
            starts_at TEXT,
            ends_at TEXT,
            dismissible INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            created_by TEXT
        )
        """,
    )
    db_execute(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS orders (
            id {id_column},
            stripe_session_id TEXT UNIQUE,
            discord_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'usd',
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            fulfilled_at TEXT
        )
        """,
    )


def get_setting(conn, db_execute, key: str, default: str = "") -> str:
    row = db_execute(conn, "SELECT value FROM site_settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return str(row["value"] or default)


def set_setting(conn, db_execute, key: str, value: str) -> None:
    db_execute(
        conn,
        """
        INSERT INTO site_settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def site_config(conn, db_execute, demo_fallback: str = "") -> dict:
    demo_url = get_setting(conn, db_execute, "demo_video_url", demo_fallback)
    return {
        "demo_video_url": demo_url,
        "stripe_enabled": pricing_payload()["stripe_enabled"],
    }


def list_changelog(conn, db_execute, *, published_only: bool) -> list[dict]:
    if published_only:
        rows = db_execute(
            conn,
            """
            SELECT id, version, title, body, published_at, created_at, created_by, is_published
            FROM site_changelog
            WHERE is_published = 1
            ORDER BY COALESCE(published_at, created_at) DESC
            """,
        ).fetchall()
    else:
        rows = db_execute(
            conn,
            """
            SELECT id, version, title, body, published_at, created_at, created_by, is_published
            FROM site_changelog
            ORDER BY id DESC
            """,
        ).fetchall()
    return [dict(row) for row in rows]


def create_changelog(conn, db_execute, payload: dict, created_by: str) -> dict:
    now = utc_now_iso()
    publish = bool(payload.get("is_published"))
    published_at = now if publish else None
    cursor = db_execute(
        conn,
        """
        INSERT INTO site_changelog (version, title, body, published_at, created_at, created_by, is_published)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(payload.get("version") or "").strip()[:32],
            str(payload.get("title") or "").strip()[:200],
            str(payload.get("body") or "").strip()[:12000],
            published_at,
            now,
            created_by,
            1 if publish else 0,
        ),
    )
    entry_id = cursor.lastrowid
    row = db_execute(conn, "SELECT * FROM site_changelog WHERE id = ?", (entry_id,)).fetchone()
    return dict(row)


def delete_changelog(conn, db_execute, entry_id: int) -> bool:
    cursor = db_execute(conn, "DELETE FROM site_changelog WHERE id = ?", (entry_id,))
    return cursor.rowcount > 0


def list_alerts(conn, db_execute, *, active_only: bool) -> list[dict]:
    now = utc_now_iso()
    if active_only:
        rows = db_execute(
            conn,
            """
            SELECT id, message, severity, active, starts_at, ends_at, dismissible, created_at, created_by
            FROM site_alerts
            WHERE active = 1
              AND (starts_at IS NULL OR starts_at <= ?)
              AND (ends_at IS NULL OR ends_at >= ?)
            ORDER BY id DESC
            """,
            (now, now),
        ).fetchall()
    else:
        rows = db_execute(
            conn,
            "SELECT id, message, severity, active, starts_at, ends_at, dismissible, created_at, created_by FROM site_alerts ORDER BY id DESC",
        ).fetchall()
    return [dict(row) for row in rows]


def create_alert(conn, db_execute, payload: dict, created_by: str) -> dict:
    now = utc_now_iso()
    cursor = db_execute(
        conn,
        """
        INSERT INTO site_alerts (message, severity, active, starts_at, ends_at, dismissible, created_at, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(payload.get("message") or "").strip()[:500],
            str(payload.get("severity") or "info").strip()[:16],
            1 if payload.get("active", True) else 0,
            payload.get("starts_at") or None,
            payload.get("ends_at") or None,
            1 if payload.get("dismissible", True) else 0,
            now,
            created_by,
        ),
    )
    alert_id = cursor.lastrowid
    row = db_execute(conn, "SELECT * FROM site_alerts WHERE id = ?", (alert_id,)).fetchone()
    return dict(row)


def update_alert(conn, db_execute, alert_id: int, payload: dict) -> dict | None:
    row = db_execute(conn, "SELECT * FROM site_alerts WHERE id = ?", (alert_id,)).fetchone()
    if row is None:
        return None
    db_execute(
        conn,
        """
        UPDATE site_alerts
        SET message = ?, severity = ?, active = ?, starts_at = ?, ends_at = ?, dismissible = ?
        WHERE id = ?
        """,
        (
            str(payload.get("message", row["message"]))[:500],
            str(payload.get("severity", row["severity"]))[:16],
            1 if payload.get("active", row["active"]) else 0,
            payload.get("starts_at", row["starts_at"]),
            payload.get("ends_at", row["ends_at"]),
            1 if payload.get("dismissible", row["dismissible"]) else 0,
            alert_id,
        ),
    )
    updated = db_execute(conn, "SELECT * FROM site_alerts WHERE id = ?", (alert_id,)).fetchone()
    return dict(updated)


def delete_alert(conn, db_execute, alert_id: int) -> bool:
    cursor = db_execute(conn, "DELETE FROM site_alerts WHERE id = ?", (alert_id,))
    return cursor.rowcount > 0


def record_order(conn, db_execute, *, stripe_session_id: str, discord_id: str, plan_id: str, amount_cents: int, status: str) -> None:
    db_execute(
        conn,
        """
        INSERT INTO orders (stripe_session_id, discord_id, plan_id, amount_cents, currency, status, created_at)
        VALUES (?, ?, ?, ?, 'usd', ?, ?)
        """,
        (stripe_session_id, discord_id, plan_id, amount_cents, status, utc_now_iso()),
    )


def fulfill_order(conn, db_execute, stripe_session_id: str) -> dict | None:
    row = db_execute(conn, "SELECT * FROM orders WHERE stripe_session_id = ?", (stripe_session_id,)).fetchone()
    if row is None:
        return None
    now = utc_now_iso()
    db_execute(
        conn,
        "UPDATE orders SET status = 'paid', fulfilled_at = ? WHERE stripe_session_id = ?",
        (now, stripe_session_id),
    )
    db_execute(
        conn,
        "UPDATE discord_users SET access_override = 1 WHERE discord_id = ?",
        (row["discord_id"],),
    )
    return dict(row)
