from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib import error as urlerror
from urllib import request as urlrequest

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN", "")
DISCORD_SYNC_CHANNEL_ID = os.getenv("DISCORD_SYNC_CHANNEL_ID") or os.getenv(
    "DISCORD_BACKUP_CHANNEL_ID", ""
)

DATA_DIR = Path(__file__).resolve().parent / "sync_data"

FILE_MAP = {
    "sessions": "virello-sessions.txt",
    "discord_users": "virello-discord-users.txt",
    "users": "virello-users.txt",
    "pending_registration_otps": "virello-pending-otps.txt",
    "meta": "virello-meta.txt",
}

TABLES = ("sessions", "discord_users", "users", "pending_registration_otps")

_connect: Callable = None  # type: ignore[assignment]
_db_execute: Callable = None  # type: ignore[assignment]
_using_postgres: Callable[[], bool] = None  # type: ignore[assignment]

_persist_timer: threading.Timer | None = None
_persist_lock = threading.Lock()
_last_sync_at: str | None = None


def configure(*, connect: Callable, db_execute: Callable, using_postgres: Callable[[], bool]) -> None:
    global _connect, _db_execute, _using_postgres
    _connect = connect
    _db_execute = db_execute
    _using_postgres = using_postgres
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def is_configured() -> bool:
    return bool(DISCORD_BOT_TOKEN and DISCORD_SYNC_CHANNEL_ID)


def storage_mode() -> str:
    explicit = os.getenv("STORAGE_MODE", "").strip().lower()
    if explicit == "discord":
        return "discord"
    if explicit == "postgres" and os.getenv("DATABASE_URL", "").strip():
        return "postgres"
    if is_configured():
        return "discord"
    if os.getenv("DATABASE_URL", "").strip():
        return "postgres"
    return "sqlite"


def _local_path(filename: str) -> Path:
    return DATA_DIR / filename


def _read_local_json(filename: str, fallback):
    path = _local_path(filename)
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _write_local_json(filename: str, data) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _local_path(filename).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _discord_request(method: str, api_path: str, *, body: bytes | None = None, headers: dict | None = None) -> dict | list | None:
    request_headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "User-Agent": "VirelloScannerDiscordSync/1.0",
    }
    if headers:
        request_headers.update(headers)
    req = urlrequest.Request(
        f"{DISCORD_API_BASE}{api_path}",
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urlrequest.urlopen(req, timeout=60) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else None
    except urlerror.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord API {error.code}: {detail}") from error


def _list_messages(limit: int = 100) -> list:
    result = _discord_request("GET", f"/channels/{DISCORD_SYNC_CHANNEL_ID}/messages?limit={limit}")
    return result if isinstance(result, list) else []


def _find_latest_attachment(filename: str) -> dict | None:
    latest = None
    for message in _list_messages():
        for attachment in message.get("attachments") or []:
            if attachment.get("filename") != filename:
                continue
            created_at = message.get("timestamp", "")
            if not latest or created_at > latest["created_at"]:
                latest = {"url": attachment["url"], "created_at": created_at}
    return latest


def _download_text(url: str) -> str:
    req = urlrequest.Request(url, headers={"User-Agent": "VirelloScannerDiscordSync/1.0"})
    with urlrequest.urlopen(req, timeout=120) as response:
        return response.read().decode("utf-8")


def _upload_text(filename: str, text: str, label: str) -> None:
    boundary = f"----VirelloSync{int(time.time() * 1000)}"
    payload = json.dumps(
        {"content": f"Virello Scanner data sync: {label} ({datetime.now(timezone.utc).isoformat()})"}
    )
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="payload_json"\r\n\r\n'
        f"{payload}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files[0]"; filename="{filename}"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
        f"{text}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    _discord_request(
        "POST",
        f"/channels/{DISCORD_SYNC_CHANNEL_ID}/messages",
        body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


def _export_table(conn, table: str) -> list:
    rows = _db_execute(conn, f"SELECT * FROM {table}").fetchall()
    return [dict(row) for row in rows]


def export_snapshot() -> dict:
    with _connect() as conn:
        return {
            "sessions": _export_table(conn, "sessions"),
            "discord_users": _export_table(conn, "discord_users"),
            "users": _export_table(conn, "users"),
            "pending_registration_otps": _export_table(conn, "pending_registration_otps"),
            "meta": {"last_sync_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")},
        }


def _import_table(conn, table: str, rows: list) -> None:
    if not rows:
        return
    if _using_postgres():
        conn.autocommit = True
    _db_execute(conn, f"DELETE FROM {table}")
    for row in rows:
        columns = list(row.keys())
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(columns)
        _db_execute(
            conn,
            f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
            tuple(row[col] for col in columns),
        )


def _import_snapshot(snapshot: dict) -> None:
    with _connect() as conn:
        if _using_postgres():
            conn.autocommit = True
        for table in TABLES:
            rows = snapshot.get(table)
            if isinstance(rows, list) and rows:
                _import_table(conn, table, rows)


def persist_all(snapshot: dict | None = None) -> None:
    global _last_sync_at
    if snapshot is None:
        snapshot = export_snapshot()
    for key, filename in FILE_MAP.items():
        payload = snapshot.get(key, {} if key == "meta" else [])
        _write_local_json(filename, payload)
        if is_configured():
            _upload_text(filename, json.dumps(payload, indent=2), key)
    _last_sync_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def schedule_persist() -> None:
    global _persist_timer

    def _run() -> None:
        with _persist_lock:
            try:
                persist_all()
            except Exception as error:
                print(f"Discord sync persist failed: {error}")

    if _persist_timer:
        _persist_timer.cancel()
    _persist_timer = threading.Timer(2.5, _run)
    _persist_timer.daemon = True
    _persist_timer.start()


def notify_db_changed() -> None:
    if storage_mode() == "discord" and is_configured():
        schedule_persist()


def load_key_from_discord(key: str):
    filename = FILE_MAP[key]
    attachment = _find_latest_attachment(filename)
    if not attachment:
        return None
    text = _download_text(attachment["url"])
    return json.loads(text)


def load_from_discord() -> bool:
    if not is_configured():
        return False
    loaded = False
    snapshot: dict = {}
    for key in FILE_MAP:
        try:
            remote = load_key_from_discord(key)
            if remote is not None and (key == "meta" or (isinstance(remote, list) and remote)):
                snapshot[key] = remote
                _write_local_json(FILE_MAP[key], remote)
                loaded = True
        except Exception as error:
            print(f"Discord sync load failed for {key}: {error}")
    if loaded and any(snapshot.get(table) for table in TABLES):
        _import_snapshot(snapshot)
        print("Discord sync: restored database from channel txt files.")
        return True
    return False


def initialize() -> None:
    if storage_mode() != "discord":
        return
    if not is_configured():
        print("Discord sync: STORAGE_MODE=discord but channel/token not configured.")
        return
    local_has_data = any(
        isinstance(_read_local_json(FILE_MAP[table], []), list) and _read_local_json(FILE_MAP[table], [])
        for table in TABLES
    )
    if load_from_discord():
        return
    if local_has_data:
        try:
            persist_all()
            print("Discord sync: uploaded local data to channel (first-time seed).")
        except Exception as error:
            print(f"Discord sync seed upload failed: {error}")
    else:
        print("Discord sync: no remote or local data yet — starting fresh.")


def get_status() -> dict:
    return {
        "mode": storage_mode(),
        "configured": is_configured(),
        "channel_id": DISCORD_SYNC_CHANNEL_ID or None,
        "last_sync_at": _last_sync_at,
    }
