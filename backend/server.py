from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import base64
import smtplib
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import backup
import discord_sync
import rate_limit

DB_PATH = Path(__file__).resolve().parent / "diagnostics.db"
DATABASE_URL = os.getenv("DATABASE_URL", "")
TOKEN_SECRET = os.getenv("API_TOKEN_SECRET", "local-dev-secret-change-me")
CHECKER_EMAIL = os.getenv("CHECKER_EMAIL", "checker@example.com")
CHECKER_PASSWORD = os.getenv("CHECKER_PASSWORD", "change-me")
PIN_TTL_MINUTES = int(os.getenv("PIN_TTL_MINUTES", "30"))
DEFAULT_FRONTEND_URL = "https://virello-secure.pages.dev"
LOCAL_FRONTEND_URL = "http://localhost:3000"
FRONTEND_URL = os.getenv("FRONTEND_URL", DEFAULT_FRONTEND_URL)


def build_cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", os.getenv("CORS_ORIGIN", ""))
    origins: list[str] = []
    seen: set[str] = set()
    for value in (LOCAL_FRONTEND_URL, DEFAULT_FRONTEND_URL, FRONTEND_URL, *configured.split(",")):
        origin = value.strip().rstrip("/")
        if origin and origin not in seen:
            seen.add(origin)
            origins.append(origin)
    return origins


CORS_ORIGINS = build_cors_origins()
DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1510615702103392327")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "https://virello-secure.onrender.com/auth/discord/callback")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "1510614253508493373")
DISCORD_ACCESS_ROLE_ID = os.getenv("DISCORD_ACCESS_ROLE_ID", "1510614274299531334")
SUPER_ADMIN_DISCORD_IDS = frozenset(
    item.strip()
    for item in os.getenv("SUPER_ADMIN_DISCORD_IDS", "1262056594993315943").split(",")
    if item.strip()
)
DISCORD_AUTH_SCOPES = "identify guilds.members.read"
PASSWORD_HASH_ITERATIONS = 260_000
OTP_TTL_MINUTES = int(os.getenv("OTP_TTL_MINUTES", "10"))
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME)
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() != "false"
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "auto").strip().lower()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "onboarding@resend.dev")
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_FROM_EMAIL = os.getenv("BREVO_FROM_EMAIL", "")
BRAND_NAME = "Virello Scanner"
BREVO_FROM_NAME = os.getenv("BREVO_FROM_NAME", BRAND_NAME)
SHARING_FINGERPRINT_LIMIT = int(os.getenv("SHARING_FINGERPRINT_LIMIT", "3"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def using_postgres() -> bool:
    return bool(DATABASE_URL)


def connect():
    if using_postgres():
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def db_sql(sql: str) -> str:
    return sql.replace("?", "%s") if using_postgres() else sql


def db_execute(conn, sql: str, params: Sequence | None = None):
    return conn.execute(db_sql(sql), params or ())


def is_unique_violation(error: Exception) -> bool:
    return isinstance(error, sqlite3.IntegrityError) or error.__class__.__name__ == "UniqueViolation"


def column_exists(conn, table: str, column: str) -> bool:
    if using_postgres():
        row = db_execute(
            conn,
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ? AND column_name = ?
            """,
            (table, column),
        ).fetchone()
        return row is not None
    rows = db_execute(conn, f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def ensure_column(conn, table: str, column: str, definition: str) -> None:
    if column_exists(conn, table, column):
        return
    db_execute(conn, f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    with connect() as conn:
        if using_postgres():
            conn.autocommit = True
        id_column = "SERIAL PRIMARY KEY" if using_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
        db_execute(
            conn,
            f"""
            CREATE TABLE IF NOT EXISTS sessions (
                id {id_column},
                pin TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                completed_at TEXT,
                consent_version TEXT,
                collected_categories TEXT,
                report_json TEXT
            )
            """
        )
        for column, definition in (
            ("reviewer_verdict", "TEXT"),
            ("reviewer_note", "TEXT"),
            ("reviewed_at", "TEXT"),
            ("reviewed_by", "TEXT"),
            ("created_by", "TEXT"),
        ):
            ensure_column(conn, "sessions", column, definition)
        db_execute(
            conn,
            """
            CREATE TABLE IF NOT EXISTS discord_users (
                discord_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                avatar TEXT,
                roles_json TEXT NOT NULL,
                last_login_at TEXT NOT NULL
            )
            """
        )
        ensure_column(conn, "discord_users", "admin_banned", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "discord_users", "admin_notes", "TEXT")
        ensure_column(conn, "discord_users", "access_override", "INTEGER")
        ensure_column(conn, "discord_users", "owner_fingerprint", "TEXT")
        ensure_column(conn, "discord_users", "fingerprint_seen_json", "TEXT NOT NULL DEFAULT '[]'")
        ensure_column(conn, "discord_users", "sharing_locked", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "discord_users", "sharing_reason", "TEXT")
        db_execute(
            conn,
            f"""
            CREATE TABLE IF NOT EXISTS users (
                id {id_column},
                email TEXT NOT NULL UNIQUE,
                username TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                discord_id TEXT,
                discord_username TEXT,
                discord_roles_json TEXT NOT NULL DEFAULT '[]',
                discord_access_verified_at TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        ensure_column(conn, "users", "username", "TEXT NOT NULL DEFAULT ''")
        db_execute(
            conn,
            "CREATE UNIQUE INDEX IF NOT EXISTS users_username_unique ON users (username) WHERE username <> ''",
        )
        db_execute(
            conn,
            """
            CREATE TABLE IF NOT EXISTS pending_registration_otps (
                email TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                otp_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )


def make_token(email: str) -> str:
    timestamp = str(int(utc_now().timestamp()))
    payload = f"{email}:{timestamp}"
    signature = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_username(username: str) -> str:
    return username.strip()


def valid_username(username: str) -> bool:
    return 3 <= len(username) <= 24 and username.replace("_", "").replace("-", "").isalnum()


def hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS)
    return salt.hex(), digest.hex()


def password_matches(password: str, salt_hex: str, expected_hash: str) -> bool:
    _, actual_hash = hash_password(password, salt_hex)
    return hmac.compare_digest(actual_hash, expected_hash)


def hash_otp(email: str, otp: str) -> str:
    payload = f"{normalize_email(email)}:{otp.strip()}"
    return hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def brevo_is_configured() -> bool:
    return bool(BREVO_API_KEY and BREVO_FROM_EMAIL)


def smtp_is_configured() -> bool:
    return bool(SMTP_HOST and SMTP_FROM and SMTP_USERNAME and SMTP_PASSWORD)


def smtp_use_ssl() -> bool:
    configured = os.getenv("SMTP_USE_SSL", "").strip().lower()
    if configured in {"true", "1", "yes", "on"}:
        return True
    if configured in {"false", "0", "no", "off"}:
        return False
    return SMTP_PORT == 465


def selected_email_provider() -> str:
    if EMAIL_PROVIDER in {"smtp", "brevo", "resend"}:
        if EMAIL_PROVIDER == "smtp" and not smtp_is_configured():
            return ""
        if EMAIL_PROVIDER == "brevo" and not brevo_is_configured():
            return ""
        if EMAIL_PROVIDER == "resend" and not RESEND_API_KEY:
            return ""
        return EMAIL_PROVIDER
    if brevo_is_configured():
        return "brevo"
    if RESEND_API_KEY:
        return "resend"
    if smtp_is_configured():
        return "smtp"
    return ""


def email_is_configured() -> bool:
    return bool(selected_email_provider())


def otp_email_body(username: str, otp: str) -> str:
    return "\n".join(
        [
            f"Hi {username},",
            "",
            f"Your {BRAND_NAME} verification code is: {otp}",
            "",
            f"This code expires in {OTP_TTL_MINUTES} minutes.",
        ]
    )


def resend_error_detail(status: int, body: str) -> str:
    message = ""
    try:
        payload = json.loads(body)
        if isinstance(payload.get("message"), str):
            message = payload["message"]
        elif isinstance(payload.get("error"), dict) and isinstance(payload["error"].get("message"), str):
            message = payload["error"]["message"]
    except json.JSONDecodeError:
        message = body.strip()

    lowered = message.lower()
    if status == 403 or "verify a domain" in lowered or "only send testing emails" in lowered:
        return (
            "Resend test mode only allows sending to the email on your Resend account. "
            "Verify a domain at resend.com/domains, then set RESEND_FROM to something like "
            f"{BRAND_NAME} <noreply@yourdomain.com>."
        )
    if message:
        return message
    return "Email provider rejected the verification message."


def send_otp_email_via_brevo(email: str, username: str, otp: str) -> None:
    payload = json.dumps(
        {
            "sender": {"name": BREVO_FROM_NAME, "email": BREVO_FROM_EMAIL},
            "to": [{"email": email}],
            "subject": f"Your {BRAND_NAME} verification code",
            "textContent": otp_email_body(username, otp),
        }
    ).encode("utf-8")
    request = urlrequest.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={
            "api-key": BREVO_API_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(request, timeout=15) as response:
            if response.status >= 400:
                detail = response.read().decode("utf-8", errors="replace")
                raise RuntimeError(brevo_error_detail(response.status, detail))
    except urlerror.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(brevo_error_detail(error.code, detail)) from error
    except urlerror.URLError as error:
        raise RuntimeError("Could not reach the email provider.") from error


def brevo_error_detail(status: int, body: str) -> str:
    message = ""
    try:
        payload = json.loads(body)
        if isinstance(payload.get("message"), str):
            message = payload["message"]
        elif isinstance(payload.get("error"), str):
            message = payload["error"]
    except json.JSONDecodeError:
        message = body.strip()

    lowered = message.lower()
    if "sender" in lowered and ("not valid" in lowered or "verify" in lowered or "authenticated" in lowered):
        return (
            "Your Brevo sender email is not verified yet. In Brevo, go to Senders & IP, "
            "add BREVO_FROM_EMAIL, and click the verification link sent to that inbox."
        )
    if message:
        return message
    return "Email provider rejected the verification message."


def send_otp_email_via_resend(email: str, username: str, otp: str) -> None:
    payload = json.dumps(
        {
            "from": RESEND_FROM,
            "to": [email],
            "subject": f"Your {BRAND_NAME} verification code",
            "text": otp_email_body(username, otp),
        }
    ).encode("utf-8")
    request = urlrequest.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(request, timeout=15) as response:
            if response.status >= 400:
                detail = response.read().decode("utf-8", errors="replace")
                raise RuntimeError(resend_error_detail(response.status, detail))
    except urlerror.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(resend_error_detail(error.code, detail)) from error
    except urlerror.URLError as error:
        raise RuntimeError("Could not reach the email provider.") from error


def send_otp_email_via_smtp(email: str, username: str, otp: str) -> None:
    message = EmailMessage()
    message["Subject"] = f"Your {BRAND_NAME} verification code"
    message["From"] = SMTP_FROM
    message["To"] = email
    message.set_content(otp_email_body(username, otp))
    try:
        if smtp_use_ssl():
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
                smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
                smtp.send_message(message)
            return
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            if SMTP_USE_TLS:
                smtp.starttls()
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError as error:
        raise RuntimeError(
            "Email login failed. For Gmail, create an App Password at "
            "https://myaccount.google.com/apppasswords and use that instead of your normal password."
        ) from error
    except (TimeoutError, OSError, smtplib.SMTPException) as error:
        raise RuntimeError(
            "Could not send email through SMTP. Render often blocks outbound SMTP; "
            "use Brevo on Render, or run the backend locally with Gmail SMTP."
        ) from error


def send_otp_email(email: str, username: str, otp: str) -> None:
    provider = selected_email_provider()
    if not provider:
        raise RuntimeError("Email OTP is not configured.")
    if provider == "brevo":
        send_otp_email_via_brevo(email, username, otp)
        return
    if provider == "resend":
        send_otp_email_via_resend(email, username, otp)
        return
    send_otp_email_via_smtp(email, username, otp)


def discord_is_configured() -> bool:
    return all(
        [
            DISCORD_CLIENT_ID,
            DISCORD_CLIENT_SECRET,
            DISCORD_REDIRECT_URI,
            DISCORD_GUILD_ID,
            DISCORD_ACCESS_ROLE_ID,
        ]
    )


def add_query_params(url: str, params: dict[str, str]) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    for key, value in params.items():
        query[key] = [value]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def allowed_return_to(value: str) -> bool:
    allowed_origins = [FRONTEND_URL.rstrip("/"), *CORS_ORIGINS]
    return any(value.rstrip("/").startswith(origin) for origin in allowed_origins)


def signed_payload(payload: dict) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    signature = hmac.new(TOKEN_SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def verify_signed_payload(value: str, max_age: timedelta) -> dict | None:
    try:
        encoded, signature = value.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(TOKEN_SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(encoded.encode()).decode())
        created_at = datetime.fromtimestamp(int(payload["ts"]), timezone.utc)
    except (ValueError, KeyError, json.JSONDecodeError):
        return None
    if created_at < utc_now() - max_age:
        return None
    return payload


def make_discord_link_ticket(user_id: int) -> str:
    return signed_payload({"user_id": user_id, "ts": int(utc_now().timestamp())})


def verify_discord_link_ticket(ticket: str) -> int | None:
    payload = verify_signed_payload(ticket, timedelta(minutes=10))
    if not payload:
        return None
    try:
        return int(payload["user_id"])
    except (KeyError, ValueError):
        return None


def signed_state(return_to: str, link_ticket: str = "") -> str:
    payload = {
        "return_to": return_to,
        "nonce": secrets.token_urlsafe(12),
        "ts": int(utc_now().timestamp()),
    }
    if link_ticket:
        payload["link_ticket"] = link_ticket
    return signed_payload(payload)


def verify_state(state: str) -> dict | None:
    return verify_signed_payload(state, timedelta(minutes=10))


def discord_json_request(path: str, bearer_token: str) -> dict:
    req = urlrequest.Request(
        f"{DISCORD_API_BASE}{path}",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Accept": "application/json",
            "User-Agent": "VirelloScannerDashboard/1.0",
        },
    )
    with urlrequest.urlopen(req, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def exchange_discord_code(code: str) -> dict:
    body = urlencode(
        {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URI,
        }
    ).encode("utf-8")
    req = urlrequest.Request(
        f"{DISCORD_API_BASE}/oauth2/token",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "VirelloScannerDashboard/1.0",
        },
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def db_changed() -> None:
    discord_sync.notify_db_changed()


def save_discord_user(user: dict, roles: list[str], fingerprint: str | None = None, ip_address: str = "") -> None:
    with connect() as conn:
        existing = db_execute(
            conn,
            "SELECT owner_fingerprint, fingerprint_seen_json, sharing_locked, sharing_reason FROM discord_users WHERE discord_id = ?",
            (user["id"],),
        ).fetchone()
        owner_fingerprint = existing["owner_fingerprint"] if existing else None
        sharing_locked = bool(existing["sharing_locked"]) if existing else False
        sharing_reason = existing["sharing_reason"] if existing else None
        fingerprints = []
        if existing and existing["fingerprint_seen_json"]:
            try:
                fingerprints = json.loads(existing["fingerprint_seen_json"])
            except json.JSONDecodeError:
                fingerprints = []
        fingerprints = [str(item) for item in fingerprints if item]

        if fingerprint:
            if not owner_fingerprint:
                owner_fingerprint = fingerprint
            if fingerprint not in fingerprints:
                fingerprints.append(fingerprint)
            if (
                owner_fingerprint
                and fingerprint != owner_fingerprint
                and not is_super_admin_discord_id(user["id"])
                and len(fingerprints) >= SHARING_FINGERPRINT_LIMIT
            ):
                sharing_locked = True
                sharing_reason = (
                    f"Account locked: {len(fingerprints)} device fingerprints detected from multiple devices."
                )

        db_execute(
            conn,
            """
            INSERT INTO discord_users (discord_id, username, avatar, roles_json, last_login_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET
                username = excluded.username,
                avatar = excluded.avatar,
                roles_json = excluded.roles_json,
                last_login_at = excluded.last_login_at
            """,
            (
                user["id"],
                user.get("global_name") or user.get("username") or user["id"],
                user.get("avatar"),
                json.dumps(roles),
                to_iso(utc_now()),
            ),
        )
        db_execute(
            conn,
            """
            UPDATE discord_users
            SET owner_fingerprint = ?,
                fingerprint_seen_json = ?,
                sharing_locked = ?,
                sharing_reason = ?,
                admin_notes = COALESCE(admin_notes, ?)
            WHERE discord_id = ?
            """,
            (
                owner_fingerprint,
                json.dumps(fingerprints[:20]),
                1 if sharing_locked else 0,
                sharing_reason,
                f"Owner IP: {ip_address}" if ip_address else None,
                user["id"],
            ),
        )
    db_changed()


def save_user_discord_access(user_id: int, user: dict, roles: list[str]) -> bool:
    with connect() as conn:
        cursor = db_execute(
            conn,
            """
            UPDATE users
            SET discord_id = ?,
                discord_username = ?,
                discord_roles_json = ?,
                discord_access_verified_at = ?
            WHERE id = ?
            """,
            (
                user["id"],
                user.get("global_name") or user.get("username") or user["id"],
                json.dumps(roles),
                to_iso(utc_now()),
                user_id,
            ),
        )
        return cursor.rowcount > 0


def create_discord_auth_url(return_to: str, link_ticket: str = "") -> str:
    return "https://discord.com/oauth2/authorize?" + urlencode(
        {
            "client_id": DISCORD_CLIENT_ID,
            "redirect_uri": DISCORD_REDIRECT_URI,
            "response_type": "code",
            "scope": DISCORD_AUTH_SCOPES,
            "state": signed_state(return_to, link_ticket),
        }
    )


def validate_token(auth_header: str | None) -> str | None:
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.removeprefix("Bearer ").strip()
    parts = token.rsplit(":", 2)
    if len(parts) != 3:
        return None
    subject, timestamp, signature = parts
    payload = f"{subject}:{timestamp}"
    expected = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        issued_at = datetime.fromtimestamp(int(timestamp), timezone.utc)
    except ValueError:
        return None
    if issued_at < utc_now() - timedelta(hours=8):
        return None
    return subject


def is_checker_subject(subject: str) -> bool:
    return hmac.compare_digest(subject, CHECKER_EMAIL)


def discord_id_from_subject(subject: str) -> str | None:
    for prefix in ("discord-", "discord:"):
        if subject.startswith(prefix):
            return subject[len(prefix) :]
    return None


def is_super_admin_discord_id(discord_id: str) -> bool:
    return discord_id in SUPER_ADMIN_DISCORD_IDS


def get_discord_profile(discord_id: str) -> dict | None:
    with connect() as conn:
        row = db_execute(conn, "SELECT * FROM discord_users WHERE discord_id = ?", (discord_id,)).fetchone()
    if row is None:
        return None
    roles = json.loads(row["roles_json"] or "[]")
    keys = row.keys()
    admin_banned = bool(row["admin_banned"]) if "admin_banned" in keys else False
    access_override = row["access_override"] if "access_override" in keys else None
    has_role_access = DISCORD_ACCESS_ROLE_ID in roles
    sharing_locked = bool(row["sharing_locked"]) if "sharing_locked" in keys else False
    sharing_reason = row["sharing_reason"] if "sharing_reason" in keys else None
    if access_override == 0:
        has_access = False
    elif access_override == 1:
        has_access = True
    else:
        has_access = has_role_access
    if admin_banned:
        has_access = False
    if sharing_locked and not is_super_admin_discord_id(discord_id):
        has_access = False
    if is_super_admin_discord_id(discord_id):
        has_access = True
    avatar = row["avatar"]
    avatar_url = None
    if avatar:
        avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar}.png?size=128"
    return {
        "discord_id": discord_id,
        "username": row["username"],
        "avatar_url": avatar_url,
        "has_access": has_access,
        "admin_banned": admin_banned,
        "admin_notes": row["admin_notes"] if "admin_notes" in keys else None,
        "access_override": access_override,
        "sharing_locked": sharing_locked,
        "sharing_reason": sharing_reason,
        "is_super_admin": is_super_admin_discord_id(discord_id),
    }


def subject_has_dashboard_access(subject: str) -> bool:
    if is_checker_subject(subject):
        return True
    discord_id = discord_id_from_subject(subject)
    if not discord_id:
        return False
    if is_super_admin_discord_id(discord_id):
        return True
    profile = get_discord_profile(discord_id)
    return bool(profile and profile["has_access"])


def fetch_discord_member(access_token: str) -> list[str]:
    try:
        member = discord_json_request(f"/users/@me/guilds/{DISCORD_GUILD_ID}/member", access_token)
    except urlerror.HTTPError as error:
        if error.code == 404:
            return []
        raise
    return [str(role) for role in member.get("roles", [])]


def expire_stale_pending_sessions(conn) -> None:
    db_execute(
        conn,
        "UPDATE sessions SET status = ? WHERE status = ? AND expires_at < ?",
        ("expired", "pending", to_iso(utc_now())),
    )
    if using_postgres():
        conn.commit()


def effective_session_status(row: sqlite3.Row) -> str:
    status = row["status"]
    if status != "pending":
        return status
    try:
        expires_at = datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00"))
    except ValueError:
        return status
    if expires_at < utc_now():
        return "expired"
    return status


def fetch_roblox_profiles(user_ids: list[str]) -> list[dict]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_id in user_ids:
        user_id = str(raw_id or "").strip()
        if not user_id or not user_id.isdigit() or user_id in seen:
            continue
        seen.add(user_id)
        normalized.append(user_id)
    if not normalized:
        return []

    profiles: dict[str, dict] = {
        user_id: {"user_id": user_id, "username": None, "headshot_url": None}
        for user_id in normalized
    }

    def post_json(url: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        request = urlrequest.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "VirelloScanner/1.0"},
            method="POST",
        )
        with urlrequest.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_json(url: str) -> dict:
        request = urlrequest.Request(url, headers={"User-Agent": "VirelloScanner/1.0"})
        with urlrequest.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        user_payload = post_json(
            "https://users.roblox.com/v1/users",
            {"userIds": [int(user_id) for user_id in normalized], "excludeBannedUsers": False},
        )
        for row in user_payload.get("data") or []:
            user_id = str(row.get("id") or "").strip()
            username = str(row.get("name") or "").strip()
            if user_id in profiles and username:
                profiles[user_id]["username"] = username
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError, TypeError, ValueError):
        pass

    try:
        thumb_payload = get_json(
            "https://thumbnails.roblox.com/v1/users/avatar-headshot?"
            + urlencode(
                {
                    "userIds": ",".join(normalized),
                    "size": "150x150",
                    "format": "Png",
                    "isCircular": "false",
                }
            )
        )
        for row in thumb_payload.get("data") or []:
            user_id = str(row.get("targetId") or "").strip()
            image_url = str(row.get("imageUrl") or "").strip()
            if user_id in profiles and image_url and row.get("state") == "Completed":
                profiles[user_id]["headshot_url"] = image_url
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError, TypeError, ValueError):
        pass

    return [profiles[user_id] for user_id in normalized]


def fetch_discord_profiles(user_ids: list[str]) -> list[dict]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_id in user_ids:
        user_id = str(raw_id or "").strip()
        if not user_id or not user_id.isdigit() or user_id in seen:
            continue
        seen.add(user_id)
        normalized.append(user_id)
    if not normalized:
        return []

    bot_token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN", "")
    profiles: dict[str, dict] = {
        user_id: {
            "user_id": user_id,
            "display_name": None,
            "avatar_hash": None,
            "avatar_url": None,
        }
        for user_id in normalized
    }
    if not bot_token:
        return [profiles[user_id] for user_id in normalized]

    for user_id in normalized:
        try:
            request = urlrequest.Request(
                f"{DISCORD_API_BASE}/users/{user_id}",
                headers={
                    "Authorization": f"Bot {bot_token}",
                    "Accept": "application/json",
                    "User-Agent": "VirelloScannerDashboard/1.0",
                },
            )
            with urlrequest.urlopen(request, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
            display_name = str(data.get("global_name") or data.get("username") or "").strip() or None
            avatar_hash = str(data.get("avatar") or "").strip() or None
            avatar_url = None
            if avatar_hash:
                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=128"
            profiles[user_id] = {
                "user_id": user_id,
                "display_name": display_name,
                "avatar_hash": avatar_hash,
                "avatar_url": avatar_url,
            }
        except (urlerror.URLError, TimeoutError, json.JSONDecodeError, TypeError, ValueError):
            continue

    return [profiles[user_id] for user_id in normalized]


def is_super_admin_subject(subject: str) -> bool:
    if is_checker_subject(subject):
        return True
    discord_id = discord_id_from_subject(subject)
    return bool(discord_id and is_super_admin_discord_id(discord_id))


def session_accessible_by(row, subject: str) -> bool:
    if is_super_admin_subject(subject):
        return True
    keys = row.keys() if hasattr(row, "keys") else ()
    created_by = row["created_by"] if "created_by" in keys else None
    if not created_by:
        return False
    return created_by == subject


def row_to_summary(row: sqlite3.Row) -> dict:
    keys = row.keys()
    return {
        "id": row["id"],
        "pin": row["pin"],
        "status": effective_session_status(row),
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "completed_at": row["completed_at"],
        "reviewer_verdict": row["reviewer_verdict"] if "reviewer_verdict" in keys else None,
        "reviewer_note": row["reviewer_note"] if "reviewer_note" in keys else None,
        "reviewed_at": row["reviewed_at"] if "reviewed_at" in keys else None,
        "reviewed_by": row["reviewed_by"] if "reviewed_by" in keys else None,
        "created_by": row["created_by"] if "created_by" in keys else None,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "VirelloScannerBackend/0.1"

    def client_key(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if forwarded:
            return forwarded
        return str(self.client_address[0] if self.client_address else "unknown")

    def request_fingerprint(self) -> str:
        user_agent = self.headers.get("User-Agent", "")
        accept_lang = self.headers.get("Accept-Language", "")
        sec_platform = self.headers.get("Sec-CH-UA-Platform", "")
        ip = self.client_key()
        digest_input = f"{user_agent}|{accept_lang}|{sec_platform}|{ip}"
        return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

    def enforce_subject_owner(self, subject: str) -> bool:
        discord_id = discord_id_from_subject(subject)
        if not discord_id or is_super_admin_discord_id(discord_id):
            return True
        with connect() as conn:
            row = db_execute(
                conn,
                "SELECT owner_fingerprint, sharing_locked, sharing_reason FROM discord_users WHERE discord_id = ?",
                (discord_id,),
            ).fetchone()
            if row is None:
                return True
            if row["sharing_locked"]:
                self.send_json(
                    HTTPStatus.FORBIDDEN,
                    {"detail": "account_sharing_locked", "message": row["sharing_reason"] or "Account is locked."},
                )
                return False
            owner = row["owner_fingerprint"] or ""
            if not owner:
                db_execute(
                    conn,
                    "UPDATE discord_users SET owner_fingerprint = ?, fingerprint_seen_json = ? WHERE discord_id = ?",
                    (self.request_fingerprint(), json.dumps([self.request_fingerprint()]), discord_id),
                )
                db_changed()
                return True
            if owner != self.request_fingerprint():
                db_execute(
                    conn,
                    "UPDATE discord_users SET sharing_locked = 1, sharing_reason = ? WHERE discord_id = ?",
                    ("Account sharing detected from a different device fingerprint.", discord_id),
                )
                db_changed()
                self.send_json(
                    HTTPStatus.FORBIDDEN,
                    {
                        "detail": "account_sharing_locked",
                        "message": "Account sharing detected. Access has been locked for security.",
                    },
                )
                return False
        return True

    def end_headers(self) -> None:
        request_origin = self.headers.get("Origin", "").rstrip("/")
        allowed_origin = request_origin if request_origin in CORS_ORIGINS else CORS_ORIGINS[0]
        self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        super().end_headers()

    def do_POST(self) -> None:
        try:
            self.handle_post()
        except Exception as error:
            print(f"Unhandled POST error: {error!r}", flush=True)
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"detail": "Internal server error"})

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path.startswith("/admin/sessions/"):
            if not self.require_super_admin():
                return
            try:
                session_id = int(path.split("/")[-1])
            except ValueError:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid session id"})
                return
            with connect() as conn:
                cursor = db_execute(conn, "DELETE FROM sessions WHERE id = ?", (session_id,))
                deleted = cursor.rowcount
            if deleted == 0:
                self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Session not found"})
                return
            db_changed()
            self.send_json(HTTPStatus.OK, {"status": "deleted"})
            return

        if not path.startswith("/sessions/"):
            self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})
            return
        subject = self.require_checker()
        if not subject:
            return
        try:
            session_id = int(path.split("/")[-1])
        except ValueError:
            self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid session id"})
            return
        with connect() as conn:
            row = db_execute(conn, "SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Session not found"})
                return
            if not session_accessible_by(row, subject):
                self.send_json(HTTPStatus.FORBIDDEN, {"detail": "Session not found"})
                return
            cursor = db_execute(conn, "DELETE FROM sessions WHERE id = ?", (session_id,))
            deleted = cursor.rowcount
        if deleted == 0:
            self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Session not found"})
            return
        db_changed()
        self.send_json(HTTPStatus.OK, {"status": "deleted"})

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_json(self, status: HTTPStatus, payload: dict | list) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.end_headers()

    def require_auth_subject(self) -> str | None:
        subject = validate_token(self.headers.get("Authorization"))
        if subject:
            return subject
        self.send_json(HTTPStatus.UNAUTHORIZED, {"detail": "Missing or invalid bearer token"})
        return None

    def require_checker(self) -> str | None:
        subject = self.require_auth_subject()
        if not subject:
            return None
        if not self.enforce_subject_owner(subject):
            return None
        if not subject_has_dashboard_access(subject):
            self.send_json(
                HTTPStatus.FORBIDDEN,
                {"detail": "access_required", "has_access": False},
            )
            return None
        return subject

    def require_super_admin(self) -> bool:
        subject = self.require_auth_subject()
        if not subject:
            return False
        discord_id = discord_id_from_subject(subject)
        if not discord_id or not is_super_admin_discord_id(discord_id):
            self.send_json(HTTPStatus.FORBIDDEN, {"detail": "super_admin_required"})
            return False
        return True

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        if path == "/health":
            status_code, payload = backup.get_health_status()
            self.send_json(HTTPStatus(status_code), payload)
            return

        if path == "/auth/me":
            subject = validate_token(self.headers.get("Authorization"))
            if not subject:
                self.send_json(HTTPStatus.UNAUTHORIZED, {"detail": "Missing or invalid bearer token"})
                return
            if is_checker_subject(subject):
                self.send_json(
                    HTTPStatus.OK,
                    {
                        "username": "Reviewer",
                        "has_access": True,
                        "is_checker": True,
                        "is_super_admin": False,
                        "avatar_url": None,
                    },
                )
                return
            discord_id = discord_id_from_subject(subject)
            if not discord_id:
                self.send_json(HTTPStatus.UNAUTHORIZED, {"detail": "Missing or invalid bearer token"})
                return
            profile = get_discord_profile(discord_id)
            if profile is None:
                self.send_json(HTTPStatus.UNAUTHORIZED, {"detail": "Missing or invalid bearer token"})
                return
            self.send_json(HTTPStatus.OK, {**profile, "is_checker": False})
            return

        if path == "/auth/discord/start":
            if not discord_is_configured():
                self.send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"detail": "Discord login is not configured on this backend."},
                )
                return
            return_to = query.get("return_to", [FRONTEND_URL])[0]
            if not allowed_return_to(return_to):
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid return URL"})
                return
            self.send_json(HTTPStatus.OK, {"url": create_discord_auth_url(return_to, query.get("link_ticket", [""])[0])})
            return

        if path == "/auth/discord/callback":
            state_payload = verify_state(query.get("state", [""])[0])
            return_to = (state_payload or {}).get("return_to") or FRONTEND_URL
            if not state_payload or not allowed_return_to(return_to):
                self.redirect(add_query_params(FRONTEND_URL, {"discord_error": "invalid_state"}))
                return
            code = query.get("code", [""])[0]
            if not code:
                self.redirect(add_query_params(return_to, {"discord_error": "missing_code"}))
                return
            try:
                token_data = exchange_discord_code(code)
                access_token = token_data["access_token"]
                user = discord_json_request("/users/@me", access_token)
                roles = fetch_discord_member(access_token)
            except (KeyError, urlerror.URLError, urlerror.HTTPError, TimeoutError, json.JSONDecodeError):
                self.redirect(add_query_params(return_to, {"discord_error": "discord_auth_failed"}))
                return
            save_discord_user(user, roles, self.request_fingerprint(), self.client_key())
            profile = get_discord_profile(user["id"])
            if profile and profile.get("sharing_locked"):
                self.redirect(add_query_params(return_to, {"discord_error": "account_sharing_locked"}))
                return
            token = make_token(f"discord-{user['id']}")
            self.redirect(add_query_params(return_to, {"token": token}))
            return

        if path == "/admin/stats":
            if not self.require_super_admin():
                return
            with connect() as conn:
                expire_stale_pending_sessions(conn)
                rows = db_execute(conn, "SELECT status, completed_at, created_by, reviewer_verdict FROM sessions").fetchall()
                user_rows = db_execute(conn, "SELECT discord_id, admin_banned, access_override, roles_json FROM discord_users").fetchall()
            counts: dict[str, int] = {}
            verdict_counts: dict[str, int] = {}
            for row in rows:
                status = row["status"]
                counts[status] = counts.get(status, 0) + 1
                verdict = row["reviewer_verdict"] if "reviewer_verdict" in row.keys() else None
                if verdict:
                    verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
            banned_users = sum(1 for row in user_rows if row["admin_banned"])
            forced_access = sum(1 for row in user_rows if row["access_override"] == 1)
            recent = sorted(
                [dict(row) for row in rows if row["status"] == "completed" and row["completed_at"]],
                key=lambda item: item["completed_at"] or "",
                reverse=True,
            )[:10]
            self.send_json(
                HTTPStatus.OK,
                {
                    "total_sessions": len(rows),
                    "by_status": counts,
                    "by_verdict": verdict_counts,
                    "discord_users": len(user_rows),
                    "banned_users": banned_users,
                    "forced_access_users": forced_access,
                    "recent_completions": recent,
                    "storage": discord_sync.get_status(),
                },
            )
            return

        if path == "/admin/health":
            if not self.require_super_admin():
                return
            sync_status = discord_sync.get_status()
            if sync_status["mode"] == "discord":
                payload = {
                    "status": "ok" if sync_status["configured"] else "degraded",
                    "storage": sync_status,
                }
            else:
                status_code, payload = backup.get_health_status()
                payload = {**payload, "storage": sync_status}
            self.send_json(HTTPStatus.OK, payload)
            return

        if path == "/admin/sessions":
            if not self.require_super_admin():
                return
            status_filter = (query.get("status") or [""])[0].strip()
            search = (query.get("q") or [""])[0].strip().lower()
            try:
                limit = min(int((query.get("limit") or ["200"])[0]), 500)
            except ValueError:
                limit = 200
            with connect() as conn:
                expire_stale_pending_sessions(conn)
                rows = db_execute(
                    conn,
                    "SELECT id, pin, status, created_at, expires_at, completed_at, reviewer_verdict, reviewer_note, reviewed_at, reviewed_by, created_by FROM sessions ORDER BY id DESC",
                ).fetchall()
            items = []
            for row in rows:
                summary = row_to_summary(row)
                if status_filter and summary["status"] != status_filter:
                    continue
                if search:
                    haystack = " ".join(
                        str(summary.get(key) or "")
                        for key in ("pin", "reviewer_verdict", "reviewer_note", "created_by")
                    ).lower()
                    if search not in haystack:
                        continue
                items.append(summary)
                if len(items) >= limit:
                    break
            self.send_json(HTTPStatus.OK, items)
            return

        if path.startswith("/admin/sessions/"):
            if not self.require_super_admin():
                return
            try:
                session_id = int(path.split("/")[-1])
            except ValueError:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid session id"})
                return
            with connect() as conn:
                row = db_execute(conn, "SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Session not found"})
                return
            result = dict(row)
            result["status"] = effective_session_status(row)
            result["collected_categories"] = json.loads(result.get("collected_categories") or "[]")
            result["report"] = json.loads(result.pop("report_json") or "{}")
            self.send_json(HTTPStatus.OK, result)
            return

        if path == "/admin/users":
            if not self.require_super_admin():
                return
            with connect() as conn:
                rows = db_execute(
                    conn,
                    "SELECT discord_id, username, roles_json, last_login_at, admin_banned, admin_notes, access_override FROM discord_users ORDER BY last_login_at DESC LIMIT 500",
                ).fetchall()
            users = []
            for row in rows:
                roles = json.loads(row["roles_json"] or "[]")
                access_override = row["access_override"]
                has_role = DISCORD_ACCESS_ROLE_ID in roles
                if access_override == 0:
                    has_access = False
                elif access_override == 1:
                    has_access = True
                else:
                    has_access = has_role
                if row["admin_banned"]:
                    has_access = False
                users.append(
                    {
                        "discord_id": row["discord_id"],
                        "username": row["username"],
                        "last_login_at": row["last_login_at"],
                        "has_access": has_access,
                        "has_role_access": has_role,
                        "admin_banned": bool(row["admin_banned"]),
                        "admin_notes": row["admin_notes"],
                        "access_override": access_override,
                    }
                )
            self.send_json(HTTPStatus.OK, users)
            return

        if path == "/sessions":
            subject = self.require_checker()
            if not subject:
                return
            with connect() as conn:
                expire_stale_pending_sessions(conn)
                if is_super_admin_subject(subject):
                    rows = db_execute(conn, "SELECT * FROM sessions ORDER BY id DESC").fetchall()
                else:
                    rows = db_execute(
                        conn,
                        "SELECT * FROM sessions WHERE created_by = ? ORDER BY id DESC",
                        (subject,),
                    ).fetchall()
            self.send_json(HTTPStatus.OK, [row_to_summary(row) for row in rows])
            return

        if path.startswith("/sessions/"):
            subject = self.require_checker()
            if not subject:
                return
            try:
                session_id = int(path.split("/")[-1])
            except ValueError:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid session id"})
                return
            with connect() as conn:
                expire_stale_pending_sessions(conn)
                row = db_execute(conn, "SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None or not session_accessible_by(row, subject):
                self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Session not found"})
                return
            result = dict(row)
            result["status"] = effective_session_status(row)
            result["collected_categories"] = json.loads(result["collected_categories"] or "[]")
            result["report"] = json.loads(result.pop("report_json") or "{}")
            self.send_json(HTTPStatus.OK, result)
            return

        self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})

    def handle_post(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        try:
            payload = self.read_json()
        except json.JSONDecodeError:
            self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid JSON"})
            return

        parts = [part for part in path.split("/") if part]

        if len(parts) == 4 and parts[0] == "admin" and parts[1] == "sessions" and parts[3] == "review":
            if not self.require_super_admin():
                return
            try:
                session_id = int(parts[2])
            except ValueError:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid session id"})
                return
            verdict = str(payload.get("verdict") or "").strip().lower()
            note = str(payload.get("note") or "").strip()
            allowed_verdicts = {"", "cleared", "suspicious", "ban", "follow-up"}
            if verdict not in allowed_verdicts:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid verdict"})
                return
            subject = self.require_auth_subject()
            with connect() as conn:
                row = db_execute(conn, "SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
                if row is None:
                    self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Session not found"})
                    return
                db_execute(
                    conn,
                    """
                    UPDATE sessions
                    SET reviewer_verdict = ?, reviewer_note = ?, reviewed_at = ?, reviewed_by = ?
                    WHERE id = ?
                    """,
                    (
                        verdict or None,
                        note[:4000] if note else None,
                        to_iso(utc_now()),
                        subject,
                        session_id,
                    ),
                )
                row = db_execute(conn, "SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            db_changed()
            self.send_json(HTTPStatus.OK, row_to_summary(row))
            return

        if path == "/admin/sessions/purge":
            if not self.require_super_admin():
                return
            status = str(payload.get("status") or "expired").strip()
            with connect() as conn:
                cursor = db_execute(conn, "DELETE FROM sessions WHERE status = ?", (status,))
                deleted = cursor.rowcount
            db_changed()
            self.send_json(HTTPStatus.OK, {"status": "purged", "deleted": deleted})
            return

        if path == "/admin/backup":
            if not self.require_super_admin():
                return
            try:
                if discord_sync.storage_mode() == "discord":
                    discord_sync.persist_all()
                else:
                    backup.create_and_upload_backup()
                self.send_json(
                    HTTPStatus.OK,
                    {
                        "status": "backed_up",
                        "file": discord_sync.SNAPSHOT_FILENAME,
                        "storage": discord_sync.get_status(),
                    },
                )
            except Exception as error:
                self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"detail": str(error)})
            return

        if len(parts) == 3 and parts[0] == "admin" and parts[1] == "users":
            if not self.require_super_admin():
                return
            discord_id = parts[2]
            admin_banned = payload.get("admin_banned")
            admin_notes = payload.get("admin_notes")
            access_override = payload.get("access_override")
            with connect() as conn:
                row = db_execute(conn, "SELECT * FROM discord_users WHERE discord_id = ?", (discord_id,)).fetchone()
                if row is None:
                    self.send_json(HTTPStatus.NOT_FOUND, {"detail": "User not found"})
                    return
                updates = []
                params: list = []
                if admin_banned is not None:
                    updates.append("admin_banned = ?")
                    params.append(1 if admin_banned else 0)
                if admin_notes is not None:
                    updates.append("admin_notes = ?")
                    params.append(str(admin_notes)[:2000] or None)
                if "access_override" in payload:
                    if access_override is None or access_override == "":
                        updates.append("access_override = ?")
                        params.append(None)
                    else:
                        updates.append("access_override = ?")
                        params.append(int(access_override))
                if not updates:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "No fields to update"})
                    return
                params.append(discord_id)
                db_execute(
                    conn,
                    f"UPDATE discord_users SET {', '.join(updates)} WHERE discord_id = ?",
                    tuple(params),
                )
                row = db_execute(conn, "SELECT * FROM discord_users WHERE discord_id = ?", (discord_id,)).fetchone()
            db_changed()
            roles = json.loads(row["roles_json"] or "[]")
            self.send_json(
                HTTPStatus.OK,
                {
                    "discord_id": row["discord_id"],
                    "username": row["username"],
                    "admin_banned": bool(row["admin_banned"]),
                    "admin_notes": row["admin_notes"],
                    "access_override": row["access_override"],
                    "has_access": DISCORD_ACCESS_ROLE_ID in roles and not row["admin_banned"],
                },
            )
            return

        if len(parts) == 3 and parts[0] == "sessions" and parts[2] == "review":
            subject = self.require_checker()
            if not subject:
                return
            try:
                session_id = int(parts[1])
            except ValueError:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid session id"})
                return
            verdict = str(payload.get("verdict") or "").strip().lower()
            note = str(payload.get("note") or "").strip()
            allowed_verdicts = {"", "cleared", "suspicious", "ban", "follow-up"}
            if verdict not in allowed_verdicts:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid verdict"})
                return
            with connect() as conn:
                row = db_execute(conn, "SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
                if row is None or not session_accessible_by(row, subject):
                    self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Session not found"})
                    return
                cursor = db_execute(
                    conn,
                    """
                    UPDATE sessions
                    SET reviewer_verdict = ?, reviewer_note = ?, reviewed_at = ?, reviewed_by = ?
                    WHERE id = ?
                    """,
                    (
                        verdict or None,
                        note[:4000] if note else None,
                        to_iso(utc_now()),
                        subject,
                        session_id,
                    ),
                )
                if cursor.rowcount == 0:
                    self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Session not found"})
                    return
                row = db_execute(conn, "SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            db_changed()
            self.send_json(HTTPStatus.OK, row_to_summary(row))
            return

        if path == "/roblox/profiles":
            if not self.require_checker():
                return
            user_ids = payload.get("user_ids") or []
            if not isinstance(user_ids, list):
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "user_ids must be a list"})
                return
            profiles = fetch_roblox_profiles([str(item) for item in user_ids])
            self.send_json(HTTPStatus.OK, {"profiles": profiles})
            return

        if path == "/discord/profiles":
            if not self.require_checker():
                return
            user_ids = payload.get("user_ids") or []
            if not isinstance(user_ids, list):
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "user_ids must be a list"})
                return
            profiles = fetch_discord_profiles([str(item) for item in user_ids])
            self.send_json(HTTPStatus.OK, {"profiles": profiles})
            return

        if path == "/sessions":
            subject = self.require_checker()
            if not subject:
                return
            if not rate_limit.allow_pin_creation(self.client_key()):
                self.send_json(HTTPStatus.TOO_MANY_REQUESTS, {"detail": "PIN creation rate limit exceeded"})
                return
            pin = f"{secrets.randbelow(1_000_000):06d}"
            now = utc_now()
            expires_at = now + timedelta(minutes=PIN_TTL_MINUTES)
            with connect() as conn:
                db_execute(
                    conn,
                    """
                    INSERT INTO sessions (pin, status, created_at, expires_at, created_by)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (pin, "pending", to_iso(now), to_iso(expires_at), subject),
                )
                row = db_execute(conn, "SELECT * FROM sessions WHERE pin = ?", (pin,)).fetchone()
            db_changed()
            self.send_json(HTTPStatus.OK, row_to_summary(row))
            return

        if path == "/reports":
            if not rate_limit.allow_report_upload(self.client_key()):
                self.send_json(HTTPStatus.TOO_MANY_REQUESTS, {"detail": "Report upload rate limit exceeded"})
                return
            pin = str(payload.get("pin", ""))
            report = payload.get("report")
            if not pin or not isinstance(report, dict):
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "PIN and report are required"})
                return
            now = utc_now()
            with connect() as conn:
                row = db_execute(conn, "SELECT * FROM sessions WHERE pin = ?", (pin,)).fetchone()
                if row is None:
                    self.send_json(HTTPStatus.NOT_FOUND, {"detail": "PIN not found"})
                    return
                if row["status"] != "pending":
                    self.send_json(HTTPStatus.CONFLICT, {"detail": "PIN already used or expired"})
                    return
                expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
                if expires_at < now:
                    db_execute(conn, "UPDATE sessions SET status = ? WHERE id = ?", ("expired", row["id"]))
                    self.send_json(HTTPStatus.GONE, {"detail": "PIN expired"})
                    return
                db_execute(
                    conn,
                    """
                    UPDATE sessions
                    SET status = ?, completed_at = ?, consent_version = ?,
                        collected_categories = ?, report_json = ?
                    WHERE id = ?
                    """,
                    (
                        "completed",
                        to_iso(now),
                        payload.get("consent_version", ""),
                        json.dumps(payload.get("collected_categories", [])),
                        json.dumps(report),
                        row["id"],
                    ),
                )
            db_changed()
            self.send_json(HTTPStatus.OK, {"status": "submitted"})
            return

        self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})

    def log_message(self, format: str, *args: object) -> None:
        print("[%s] %s" % (self.log_date_time_string(), format % args))


def main() -> None:
    discord_sync.configure(connect=connect, db_execute=db_execute, using_postgres=using_postgres)
    init_db()
    if discord_sync.storage_mode() == "discord":
        discord_sync.initialize()
        print(f"Storage mode: Discord txt sync (channel {os.getenv('DISCORD_SYNC_CHANNEL_ID', '')})")
    else:
        backup.configure(
            connect=connect,
            db_execute=db_execute,
            using_postgres=using_postgres,
            to_iso=to_iso,
            utc_now=utc_now,
        )
        backup.initialize_backup_system()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"Virello Scanner backend running at http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
