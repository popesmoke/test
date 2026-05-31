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

DB_PATH = Path(__file__).resolve().parent / "diagnostics.db"
DATABASE_URL = os.getenv("DATABASE_URL", "")
TOKEN_SECRET = os.getenv("API_TOKEN_SECRET", "local-dev-secret-change-me")
CHECKER_EMAIL = os.getenv("CHECKER_EMAIL", "checker@example.com")
CHECKER_PASSWORD = os.getenv("CHECKER_PASSWORD", "change-me")
PIN_TTL_MINUTES = int(os.getenv("PIN_TTL_MINUTES", "30"))
DEFAULT_FRONTEND_URL = "https://joyful-torte-157157.netlify.app"
LOCAL_FRONTEND_URL = "http://localhost:3000"
CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", os.getenv("CORS_ORIGIN", f"{LOCAL_FRONTEND_URL},{DEFAULT_FRONTEND_URL}")).split(",")
    if origin.strip()
]
FRONTEND_URL = os.getenv("FRONTEND_URL", DEFAULT_FRONTEND_URL)
DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1510615702103392327")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "https://test-v7a8.onrender.com/auth/discord/callback")
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


def ensure_column(conn, table: str, column: str, definition: str) -> None:
    try:
        db_execute(conn, f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except Exception:
        return


def init_db() -> None:
    with connect() as conn:
        id_column = "SERIAL PRIMARY KEY" if using_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
        conn.execute(
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
        conn.execute(
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
        conn.execute(
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
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_username_unique ON users (username) WHERE username <> ''")
        conn.execute(
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


def smtp_is_configured() -> bool:
    return bool(SMTP_HOST and SMTP_FROM)


def send_otp_email(email: str, username: str, otp: str) -> None:
    if not smtp_is_configured():
        raise RuntimeError("Email OTP is not configured.")
    message = EmailMessage()
    message["Subject"] = "Your DangerousCity verification code"
    message["From"] = SMTP_FROM
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                f"Hi {username},",
                "",
                f"Your DangerousCity verification code is: {otp}",
                "",
                f"This code expires in {OTP_TTL_MINUTES} minutes.",
            ]
        )
    )
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
        if SMTP_USE_TLS:
            smtp.starttls()
        if SMTP_USERNAME or SMTP_PASSWORD:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)


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
            "User-Agent": "DangerousCityDashboard/1.0",
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
            "User-Agent": "DangerousCityDashboard/1.0",
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
    parts = token.split(":")
    if len(parts) != 3:
        return None
    email, timestamp, signature = parts
    payload = f"{email}:{timestamp}"
    expected = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        issued_at = datetime.fromtimestamp(int(timestamp), timezone.utc)
    except ValueError:
        return None
    if issued_at < utc_now() - timedelta(hours=8):
        return None
    return email


def row_to_summary(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "pin": row["pin"],
        "status": row["status"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "completed_at": row["completed_at"],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DiagnosticBackend/0.1"

    def end_headers(self) -> None:
        request_origin = self.headers.get("Origin", "").rstrip("/")
        allowed_origin = request_origin if request_origin in CORS_ORIGINS else CORS_ORIGINS[0]
        self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        super().end_headers()

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

    def require_checker(self) -> bool:
        if validate_token(self.headers.get("Authorization")):
            return True
        self.send_json(HTTPStatus.UNAUTHORIZED, {"detail": "Missing or invalid bearer token"})
        return False

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        if path == "/health":
            self.send_json(HTTPStatus.OK, {"status": "ok"})
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
                member = discord_json_request(f"/users/@me/guilds/{DISCORD_GUILD_ID}/member", access_token)
                roles = [str(role) for role in member.get("roles", [])]
            except (KeyError, urlerror.URLError, TimeoutError, json.JSONDecodeError):
                self.redirect(add_query_params(return_to, {"discord_error": "discord_auth_failed"}))
                return
            if DISCORD_ACCESS_ROLE_ID not in roles:
                self.redirect(add_query_params(return_to, {"discord_error": "missing_access_role"}))
                return
            save_discord_user(user, roles)
            user_id = verify_discord_link_ticket(state_payload.get("link_ticket", ""))
            if not user_id or not save_user_discord_access(user_id, user, roles):
                self.redirect(add_query_params(return_to, {"discord_error": "missing_account_link"}))
                return
            token = make_token(f"user-{user_id}")
            self.redirect(add_query_params(return_to, {"token": token}))
            return

        if path == "/sessions":
            if not self.require_checker():
                return
            with connect() as conn:
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
                row = db_execute(conn, "SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Session not found"})
                return
            result = dict(row)
            result["collected_categories"] = json.loads(result["collected_categories"] or "[]")
            result["report"] = json.loads(result.pop("report_json") or "{}")
            self.send_json(HTTPStatus.OK, result)
            return

        self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        try:
            payload = self.read_json()
        except json.JSONDecodeError:
            self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid JSON"})
            return

        if path == "/auth/register/start":
            email = normalize_email(str(payload.get("email", "")))
            username = normalize_username(str(payload.get("username", "")))
            password = str(payload.get("password", ""))
            if "@" not in email or len(email) > 254:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Enter a valid email address."})
                return
            if not valid_username(username):
                self.send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"detail": "Username must be 3-24 characters using letters, numbers, hyphens, or underscores."},
                )
                return
            if len(password) < 6:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Password must be at least 6 characters."})
                return
            if not smtp_is_configured():
                self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"detail": "Email OTP is not configured yet."})
                return
            salt, password_hash = hash_password(password)
            otp = f"{secrets.randbelow(1_000_000):06d}"
            now = utc_now()
            expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)
            try:
                with connect() as conn:
                    existing = db_execute(
                        conn,
                        "SELECT id FROM users WHERE email = ? OR username = ?",
                        (email, username),
                    ).fetchone()
                    if existing is not None:
                        self.send_json(HTTPStatus.CONFLICT, {"detail": "Email or username is already registered."})
                        return
                    pending_username = db_execute(
                        conn,
                        "SELECT email FROM pending_registration_otps WHERE username = ? AND expires_at > ? AND email <> ?",
                        (username, to_iso(now), email),
                    ).fetchone()
                    if pending_username is not None:
                        self.send_json(HTTPStatus.CONFLICT, {"detail": "That username is already being registered."})
                        return
                    db_execute(
                        conn,
                        """
                        INSERT INTO pending_registration_otps
                            (email, username, password_salt, password_hash, otp_hash, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(email) DO UPDATE SET
                            username = excluded.username,
                            password_salt = excluded.password_salt,
                            password_hash = excluded.password_hash,
                            otp_hash = excluded.otp_hash,
                            created_at = excluded.created_at,
                            expires_at = excluded.expires_at
                        """,
                        (email, username, salt, password_hash, hash_otp(email, otp), to_iso(now), to_iso(expires_at)),
                    )
                send_otp_email(email, username, otp)
            except RuntimeError as error:
                self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"detail": str(error)})
                return
            except Exception:
                raise
            self.send_json(HTTPStatus.OK, {"status": "otp_sent"})
            return

        if path == "/auth/register/verify":
            email = normalize_email(str(payload.get("email", "")))
            otp = str(payload.get("otp", ""))
            return_to = query.get("return_to", [FRONTEND_URL])[0]
            if not allowed_return_to(return_to):
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid return URL"})
                return
            with connect() as conn:
                pending = db_execute(conn, "SELECT * FROM pending_registration_otps WHERE email = ?", (email,)).fetchone()
                if pending is None:
                    self.send_json(HTTPStatus.NOT_FOUND, {"detail": "No pending verification code for that email."})
                    return
                expires_at = datetime.fromisoformat(pending["expires_at"].replace("Z", "+00:00"))
                if expires_at < utc_now():
                    db_execute(conn, "DELETE FROM pending_registration_otps WHERE email = ?", (email,))
                    self.send_json(HTTPStatus.GONE, {"detail": "Verification code expired. Request a new code."})
                    return
                if not hmac.compare_digest(pending["otp_hash"], hash_otp(email, otp)):
                    self.send_json(HTTPStatus.UNAUTHORIZED, {"detail": "Invalid verification code."})
                    return
                try:
                    db_execute(
                        conn,
                        """
                        INSERT INTO users (email, username, password_salt, password_hash, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            pending["email"],
                            pending["username"],
                            pending["password_salt"],
                            pending["password_hash"],
                            to_iso(utc_now()),
                        ),
                    )
                except Exception as error:
                    if not is_unique_violation(error):
                        raise
                    self.send_json(HTTPStatus.CONFLICT, {"detail": "Email or username is already registered."})
                    return
                user_id = db_execute(conn, "SELECT id FROM users WHERE email = ?", (email,)).fetchone()["id"]
                db_execute(conn, "DELETE FROM pending_registration_otps WHERE email = ?", (email,))
            if not discord_is_configured():
                self.send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"detail": "Email verified, but Discord verification is not configured yet."},
                )
                return
            self.send_json(
                HTTPStatus.CREATED,
                {
                    "requires_discord": True,
                    "discord_url": create_discord_auth_url(return_to, make_discord_link_ticket(user_id)),
                },
            )
            return

        if path == "/auth/login":
            email = normalize_email(str(payload.get("email", "")))
            password = str(payload.get("password", ""))
            return_to = query.get("return_to", [FRONTEND_URL])[0]
            valid_email = hmac.compare_digest(email, CHECKER_EMAIL)
            valid_password = hmac.compare_digest(password, CHECKER_PASSWORD)
            if valid_email and valid_password:
                self.send_json(HTTPStatus.OK, {"token": make_token(email)})
                return
            if not allowed_return_to(return_to):
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid return URL"})
                return
            with connect() as conn:
                row = db_execute(conn, "SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row is None or not password_matches(password, row["password_salt"], row["password_hash"]):
                self.send_json(HTTPStatus.UNAUTHORIZED, {"detail": "Invalid credentials"})
                return
            if not discord_is_configured():
                self.send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"detail": "Discord verification is not configured yet."},
                )
                return
            self.send_json(
                HTTPStatus.OK,
                {
                    "requires_discord": True,
                    "discord_url": create_discord_auth_url(return_to, make_discord_link_ticket(row["id"])),
                },
            )
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
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"Diagnostic backend running at http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
