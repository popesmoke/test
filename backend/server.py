from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from links import invite_url, scanner_download_url

DB_PATH = Path(__file__).resolve().parent / "diagnostics.db"
SCANNER_EXE_PATH = os.getenv("SCANNER_EXE_PATH", "")
TOKEN_SECRET = os.getenv("API_TOKEN_SECRET", "local-dev-secret-change-me")
CHECKER_EMAIL = os.getenv("CHECKER_EMAIL", "checker@example.com")
CHECKER_PASSWORD = os.getenv("CHECKER_PASSWORD", "change-me")
PIN_TTL_MINUTES = int(os.getenv("PIN_TTL_MINUTES", "30"))
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:3000")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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


def make_token(email: str) -> str:
    timestamp = str(int(utc_now().timestamp()))
    payload = f"{email}:{timestamp}"
    signature = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


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
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
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
            cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
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

    def send_redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.end_headers()

    def send_file(self, file_path: Path) -> None:
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", f'attachment; filename="{file_path.name}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def require_checker(self) -> bool:
        if validate_token(self.headers.get("Authorization")):
            return True
        self.send_json(HTTPStatus.UNAUTHORIZED, {"detail": "Missing or invalid bearer token"})
        return False

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/health":
            self.send_json(HTTPStatus.OK, {"status": "ok"})
            return

        if path == "/download/scanner":
            configured = os.getenv("SCANNER_DOWNLOAD_URL", "").strip()
            if configured:
                self.send_redirect(configured)
                return
            if SCANNER_EXE_PATH:
                exe = Path(SCANNER_EXE_PATH)
                if exe.is_file():
                    self.send_file(exe)
                    return
            self.send_json(
                HTTPStatus.NOT_FOUND,
                {"detail": "Scanner download is not configured. Set SCANNER_DOWNLOAD_URL or SCANNER_EXE_PATH."},
            )
            return

        if path == "/sessions":
            if not self.require_checker():
                return
            with connect() as conn:
                rows = conn.execute("SELECT * FROM sessions ORDER BY id DESC").fetchall()
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
                row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
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

        try:
            payload = self.read_json()
        except json.JSONDecodeError:
            self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid JSON"})
            return

        if path == "/auth/login":
            email = str(payload.get("email", ""))
            password = str(payload.get("password", ""))
            valid_email = hmac.compare_digest(email, CHECKER_EMAIL)
            valid_password = hmac.compare_digest(password, CHECKER_PASSWORD)
            if not valid_email or not valid_password:
                self.send_json(HTTPStatus.UNAUTHORIZED, {"detail": "Invalid credentials"})
                return
            self.send_json(HTTPStatus.OK, {"token": make_token(email)})
            return

        if path == "/sessions":
            if not self.require_checker():
                return
            pin = f"{secrets.randbelow(1_000_000):06d}"
            now = utc_now()
            expires_at = now + timedelta(minutes=PIN_TTL_MINUTES)
            with connect() as conn:
                conn.execute(
                    """
                    INSERT INTO sessions (pin, status, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (pin, "pending", to_iso(now), to_iso(expires_at)),
                )
                row = conn.execute("SELECT * FROM sessions WHERE pin = ?", (pin,)).fetchone()
            summary = row_to_summary(row)
            summary["download_url"] = scanner_download_url()
            summary["invite_url"] = invite_url(summary["pin"])
            self.send_json(HTTPStatus.OK, summary)
            return

        if path == "/reports":
            pin = str(payload.get("pin", ""))
            report = payload.get("report")
            if not pin or not isinstance(report, dict):
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "PIN and report are required"})
                return
            now = utc_now()
            with connect() as conn:
                row = conn.execute("SELECT * FROM sessions WHERE pin = ?", (pin,)).fetchone()
                if row is None:
                    self.send_json(HTTPStatus.NOT_FOUND, {"detail": "PIN not found"})
                    return
                if row["status"] != "pending":
                    self.send_json(HTTPStatus.CONFLICT, {"detail": "PIN already used or expired"})
                    return
                expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
                if expires_at < now:
                    conn.execute("UPDATE sessions SET status = ? WHERE id = ?", ("expired", row["id"]))
                    self.send_json(HTTPStatus.GONE, {"detail": "PIN expired"})
                    return
                conn.execute(
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
