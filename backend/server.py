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


def save_discord_user(user: dict, roles: list[str]) -> None:
    with connect() as conn:
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


def get_discord_profile(discord_id: str) -> dict | None:
    with connect() as conn:
        row = db_execute(conn, "SELECT * FROM discord_users WHERE discord_id = ?", (discord_id,)).fetchone()
    if row is None:
        return None
    roles = json.loads(row["roles_json"] or "[]")
    avatar = row["avatar"]
    avatar_url = None
    if avatar:
        avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar}.png?size=128"
    return {
        "discord_id": discord_id,
        "username": row["username"],
        "avatar_url": avatar_url,
        "has_access": DISCORD_ACCESS_ROLE_ID in roles,
    }


def subject_has_dashboard_access(subject: str) -> bool:
    if is_checker_subject(subject):
        return True
    discord_id = discord_id_from_subject(subject)
    if not discord_id:
        return False
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


def row_to_summary(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "pin": row["pin"],
        "status": effective_session_status(row),
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "completed_at": row["completed_at"],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "VirelloScannerBackend/0.1"

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
        if not path.startswith("/sessions/"):
            self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})
            return
        if not self.require_checker():
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

    def require_checker(self) -> bool:
        subject = self.require_auth_subject()
        if not subject:
            return False
        if not subject_has_dashboard_access(subject):
            self.send_json(
                HTTPStatus.FORBIDDEN,
                {"detail": "access_required", "has_access": False},
            )
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
            save_discord_user(user, roles)
            token = make_token(f"discord-{user['id']}")
            self.redirect(add_query_params(return_to, {"token": token}))
            return

        if path == "/sessions":
            if not self.require_checker():
                return
            with connect() as conn:
                expire_stale_pending_sessions(conn)
                rows = db_execute(conn, "SELECT * FROM sessions ORDER BY id DESC").fetchall()
            self.send_json(HTTPStatus.OK, [row_to_summary(row) for row in rows])
            return

        if path.startswith("/sessions/"):
            if not self.require_checker():
                return
            try:
                session_id = int(path.split("/")[-1])
            except ValueError:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid session id"})
                return
            with connect() as conn:
                expire_stale_pending_sessions(conn)
                row = db_execute(conn, "SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
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

        if path == "/sessions":
            if not self.require_checker():
                return
            pin = f"{secrets.randbelow(1_000_000):06d}"
            now = utc_now()
            expires_at = now + timedelta(minutes=PIN_TTL_MINUTES)
            with connect() as conn:
                db_execute(
                    conn,
                    """
                    INSERT INTO sessions (pin, status, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (pin, "pending", to_iso(now), to_iso(expires_at)),
                )
                row = db_execute(conn, "SELECT * FROM sessions WHERE pin = ?", (pin,)).fetchone()
            self.send_json(HTTPStatus.OK, row_to_summary(row))
            return

        if path == "/reports":
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
            self.send_json(HTTPStatus.OK, {"status": "submitted"})
            return

        self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})

    def log_message(self, format: str, *args: object) -> None:
        print("[%s] %s" % (self.log_date_time_string(), format % args))


def main() -> None:
    init_db()
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
