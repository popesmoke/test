from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR.parent / "diagnostics.db"
TOKEN_SECRET = os.getenv("API_TOKEN_SECRET", "local-dev-secret-change-me")
CHECKER_EMAIL = os.getenv("CHECKER_EMAIL", "checker@example.com")
CHECKER_PASSWORD = os.getenv("CHECKER_PASSWORD", "change-me")
PIN_TTL_MINUTES = int(os.getenv("PIN_TTL_MINUTES", "30"))

app = FastAPI(title="Secure Remote Diagnostic API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    token: str


class SessionCreateResponse(BaseModel):
    id: int
    pin: str
    status: str
    expires_at: str
    created_at: str


class SessionSummary(BaseModel):
    id: int
    pin: str
    status: str
    created_at: str
    expires_at: str
    completed_at: str | None = None


class ReportUpload(BaseModel):
    pin: str = Field(min_length=4, max_length=12)
    consent_version: str
    collected_categories: list[str]
    report: dict[str, Any]


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


@app.on_event("startup")
def startup() -> None:
    init_db()


def make_token(email: str) -> str:
    timestamp = str(int(utc_now().timestamp()))
    payload = f"{email}:{timestamp}"
    signature = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def require_checker(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    parts = token.split(":")
    if len(parts) != 3:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    email, timestamp, signature = parts
    payload = f"{email}:{timestamp}"
    expected = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    issued_at = datetime.fromtimestamp(int(timestamp), timezone.utc)
    if issued_at < utc_now() - timedelta(hours=8):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    return email


def row_to_summary(row: sqlite3.Row) -> SessionSummary:
    return SessionSummary(
        id=row["id"],
        pin=row["pin"],
        status=row["status"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        completed_at=row["completed_at"],
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    valid_email = hmac.compare_digest(payload.email, CHECKER_EMAIL)
    valid_password = hmac.compare_digest(payload.password, CHECKER_PASSWORD)
    if not valid_email or not valid_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(token=make_token(payload.email))


@app.post("/sessions", response_model=SessionCreateResponse)
def create_session(_: str = Depends(require_checker)) -> SessionCreateResponse:
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

    return SessionCreateResponse(
        id=row["id"],
        pin=row["pin"],
        status=row["status"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
    )


@app.get("/sessions", response_model=list[SessionSummary])
def list_sessions(_: str = Depends(require_checker)) -> list[SessionSummary]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM sessions ORDER BY id DESC").fetchall()
    return [row_to_summary(row) for row in rows]


@app.get("/sessions/{session_id}")
def get_session(session_id: int, _: str = Depends(require_checker)) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    result = dict(row)
    result["collected_categories"] = json.loads(result["collected_categories"] or "[]")
    result["report"] = json.loads(result.pop("report_json") or "{}")
    return result


@app.post("/reports")
def upload_report(payload: ReportUpload) -> dict[str, str]:
    now = utc_now()
    with connect() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE pin = ?", (payload.pin,)).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PIN not found")
        if row["status"] != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PIN already used or expired")
        expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
        if expires_at < now:
            conn.execute("UPDATE sessions SET status = ? WHERE id = ?", ("expired", row["id"]))
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="PIN expired")

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
                payload.consent_version,
                json.dumps(payload.collected_categories),
                json.dumps(payload.report),
                row["id"],
            ),
        )

    return {"status": "submitted"}
