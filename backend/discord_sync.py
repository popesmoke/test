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
SNAPSHOT_FILENAME = "virello-scanner-backup.txt"
SNAPSHOT_VERSION = 1

TABLES = ("sessions", "discord_users", "users", "pending_registration_otps")

LEGACY_FILE_MAP = {
    "sessions": "virello-sessions.txt",
    "discord_users": "virello-discord-users.txt",
    "users": "virello-users.txt",
    "pending_registration_otps": "virello-pending-otps.txt",
    "meta": "virello-meta.txt",
}

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


def _local_snapshot_path() -> Path:
    return DATA_DIR / SNAPSHOT_FILENAME


def _read_json_file(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _pack_snapshot(snapshot: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "version": SNAPSHOT_VERSION,
        "exported_at": now,
        "sessions": snapshot.get("sessions", []),
        "discord_users": snapshot.get("discord_users", []),
        "users": snapshot.get("users", []),
        "pending_registration_otps": snapshot.get("pending_registration_otps", []),
        "meta": {
            **(snapshot.get("meta") or {}),
            "last_sync_at": now,
        },
    }


def _unpack_snapshot(data: dict | None) -> dict:
    if not isinstance(data, dict):
        return {table: [] for table in TABLES} | {"meta": {}}
    return {
        "sessions": data.get("sessions", []),
        "discord_users": data.get("discord_users", []),
        "users": data.get("users", []),
        "pending_registration_otps": data.get("pending_registration_otps", []),
        "meta": data.get("meta", {}),
    }


def _write_local_snapshot(packed: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _local_snapshot_path().write_text(json.dumps(packed, indent=2), encoding="utf-8")


def _read_local_snapshot() -> dict | None:
    raw = _read_json_file(_local_snapshot_path(), None)
    if raw is None:
        return None
    return _unpack_snapshot(raw)


def _has_data(snapshot: dict) -> bool:
    return any(isinstance(snapshot.get(table), list) and snapshot[table] for table in TABLES)


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


def _upload_snapshot(packed: dict) -> None:
    global _last_sync_at
    text = json.dumps(packed, indent=2)
    boundary = f"----VirelloSync{int(time.time() * 1000)}"
    payload = json.dumps(
        {"content": f"Virello Scanner backup ({packed.get('exported_at', 'unknown')})"}
    )
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="payload_json"\r\n\r\n'
        f"{payload}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files[0]"; filename="{SNAPSHOT_FILENAME}"\r\n'
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
    _last_sync_at = packed.get("meta", {}).get("last_sync_at") or packed.get("exported_at")


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
            "meta": {},
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
    if snapshot is None:
        snapshot = export_snapshot()
    packed = _pack_snapshot(snapshot)
    _write_local_snapshot(packed)
    if is_configured():
        _upload_snapshot(packed)


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


def _load_snapshot_from_discord() -> dict | None:
    attachment = _find_latest_attachment(SNAPSHOT_FILENAME)
    if not attachment:
        return None
    text = _download_text(attachment["url"])
    return _unpack_snapshot(json.loads(text))


def _load_legacy_from_discord() -> dict | None:
    snapshot: dict = {table: [] for table in TABLES} | {"meta": {}}
    loaded = False
    for key, filename in LEGACY_FILE_MAP.items():
        try:
            attachment = _find_latest_attachment(filename)
            if not attachment:
                continue
            text = _download_text(attachment["url"])
            remote = json.loads(text)
            if key == "meta" or (isinstance(remote, list) and remote):
                snapshot[key] = remote
                loaded = True
        except Exception as error:
            print(f"Discord legacy sync load failed for {key}: {error}")
    return snapshot if loaded else None


def load_from_discord() -> bool:
    if not is_configured():
        return False

    try:
        remote = _load_snapshot_from_discord()
        if remote and _has_data(remote):
            _write_local_snapshot(_pack_snapshot(remote))
            _import_snapshot(remote)
            print("Discord sync: restored from unified backup file.")
            return True
    except Exception as error:
        print(f"Discord unified backup load failed: {error}")

    try:
        legacy = _load_legacy_from_discord()
        if legacy and _has_data(legacy):
            persist_all(legacy)
            _import_snapshot(legacy)
            print("Discord sync: migrated legacy multi-file backup to unified file.")
            return True
    except Exception as error:
        print(f"Discord legacy backup load failed: {error}")

    return False


def initialize() -> None:
    if storage_mode() != "discord":
        return
    if not is_configured():
        print("Discord sync: STORAGE_MODE=discord but channel/token not configured.")
        return
    local = _read_local_snapshot()
    local_has_data = bool(local and _has_data(local))
    if load_from_discord():
        return
    if local_has_data:
        try:
            persist_all(local)
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
        "snapshot_file": SNAPSHOT_FILENAME,
        "last_sync_at": _last_sync_at,
    }
