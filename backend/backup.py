from __future__ import annotations

import gzip
import json
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib import error as urlerror
from urllib import request as urlrequest

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_BACKUP_CHANNEL_ID = os.getenv("DISCORD_BACKUP_CHANNEL_ID", "")
BACKUP_INTERVAL_DAYS = int(os.getenv("BACKUP_INTERVAL_DAYS", "29"))
BACKUP_FILENAME_PREFIX = "virello-db-backup-"
BACKUP_VERSION = 1
BACKUP_TABLES = ("sessions", "discord_users", "users", "pending_registration_otps")
SCHEDULER_CHECK_SECONDS = int(os.getenv("BACKUP_CHECK_INTERVAL_SECONDS", "3600"))

_connect: Callable = None  # type: ignore[assignment]
_db_execute: Callable = None  # type: ignore[assignment]
_using_postgres: Callable[[], bool] = None  # type: ignore[assignment]
_to_iso: Callable[[datetime], str] = None  # type: ignore[assignment]
_utc_now: Callable[[], datetime] = None  # type: ignore[assignment]

_backup_lock = threading.Lock()
_last_backup_at: str | None = None
_last_restore_at: str | None = None
_scheduler_started = False


def configure(
    *,
    connect: Callable,
    db_execute: Callable,
    using_postgres: Callable[[], bool],
    to_iso: Callable[[datetime], str],
    utc_now: Callable[[], datetime],
) -> None:
    global _connect, _db_execute, _using_postgres, _to_iso, _utc_now
    _connect = connect
    _db_execute = db_execute
    _using_postgres = using_postgres
    _to_iso = to_iso
    _utc_now = utc_now


def backup_is_configured() -> bool:
    return bool(DISCORD_BOT_TOKEN and DISCORD_BACKUP_CHANNEL_ID)


def backup_auto_restore_enabled() -> bool:
    configured = os.getenv("BACKUP_AUTO_RESTORE", "").strip().lower()
    if configured in {"0", "false", "no", "off"}:
        return False
    if configured in {"1", "true", "yes", "on"}:
        return True
    return backup_is_configured() and _using_postgres()


def backup_enabled() -> bool:
    configured = os.getenv("BACKUP_ENABLED", "true").strip().lower()
    return configured not in {"0", "false", "no", "off"}


def init_backup_meta() -> None:
    with _connect() as conn:
        if _using_postgres():
            conn.autocommit = True
        _db_execute(
            conn,
            """
            CREATE TABLE IF NOT EXISTS _app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """,
        )


def _meta_get(key: str) -> str | None:
    with _connect() as conn:
        row = _db_execute(conn, "SELECT value FROM _app_meta WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    return row["value"]


def _meta_set(key: str, value: str) -> None:
    with _connect() as conn:
        _db_execute(
            conn,
            """
            INSERT INTO _app_meta (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )


def database_has_data() -> bool:
    with _connect() as conn:
        for table in BACKUP_TABLES:
            row = _db_execute(conn, f"SELECT COUNT(*) AS count FROM {table}").fetchone()
            if int(row["count"]) > 0:
                return True
    return False


def export_database() -> dict:
    payload = {
        "version": BACKUP_VERSION,
        "exported_at": _to_iso(_utc_now()),
        "tables": {},
    }
    with _connect() as conn:
        for table in BACKUP_TABLES:
            rows = _db_execute(conn, f"SELECT * FROM {table}").fetchall()
            payload["tables"][table] = [dict(row) for row in rows]
    return payload


def _reset_sequences(conn) -> None:
    if not _using_postgres():
        return
    for table in ("sessions", "users"):
        _db_execute(
            conn,
            f"""
            SELECT setval(
                pg_get_serial_sequence('{table}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table}), 1),
                true
            )
            """,
        )


def restore_database(backup: dict) -> None:
    tables = backup.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Backup payload is missing table data.")

    with _connect() as conn:
        if _using_postgres():
            conn.autocommit = False
        for table in BACKUP_TABLES:
            _db_execute(conn, f"DELETE FROM {table}")
        for table in BACKUP_TABLES:
            rows = tables.get(table, [])
            if not rows:
                continue
            columns = list(rows[0].keys())
            placeholders = ", ".join(["?"] * len(columns))
            column_names = ", ".join(columns)
            for row in rows:
                _db_execute(
                    conn,
                    f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})",
                    tuple(row[column] for column in columns),
                )
        _reset_sequences(conn)
        if _using_postgres():
            conn.commit()


def _backup_filename(exported_at: str) -> str:
    safe_timestamp = exported_at.replace(":", "").replace("+00:00", "Z")
    return f"{BACKUP_FILENAME_PREFIX}{safe_timestamp}.json.gz"


def serialize_backup(payload: dict) -> bytes:
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return gzip.compress(encoded)


def deserialize_backup(content: bytes) -> dict:
    try:
        decoded = gzip.decompress(content)
    except OSError:
        decoded = content
    payload = json.loads(decoded.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Backup payload must be a JSON object.")
    return payload


def _discord_request(
    method: str,
    path: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> tuple[int, bytes]:
    request_headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "User-Agent": "VirelloScannerBackup/1.0",
    }
    if headers:
        request_headers.update(headers)
    request = urlrequest.Request(
        f"{DISCORD_API_BASE}{path}",
        data=data,
        headers=request_headers,
        method=method,
    )
    try:
        with urlrequest.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urlerror.HTTPError as error:
        return error.code, error.read()


def _discord_upload_backup(filename: str, content: bytes, exported_at: str) -> dict:
    boundary = f"----VirelloBackup{secrets.token_hex(16)}"
    message_payload = json.dumps(
        {
            "content": f"Virello Scanner database backup ({exported_at})",
        },
        separators=(",", ":"),
    ).encode("utf-8")

    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="payload_json"\r\n')
    body.extend(b"Content-Type: application/json\r\n\r\n")
    body.extend(message_payload)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        (
            f'Content-Disposition: form-data; name="files[0]"; filename="{filename}"\r\n'
            "Content-Type: application/gzip\r\n\r\n"
        ).encode()
    )
    body.extend(content)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())

    status, response_body = _discord_request(
        "POST",
        f"/channels/{DISCORD_BACKUP_CHANNEL_ID}/messages",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=120,
    )
    if status >= 400:
        detail = response_body.decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord backup upload failed ({status}): {detail}")
    return json.loads(response_body.decode("utf-8"))


def _discord_list_backup_messages(limit: int = 100) -> list[dict]:
    status, response_body = _discord_request(
        "GET",
        f"/channels/{DISCORD_BACKUP_CHANNEL_ID}/messages?limit={limit}",
    )
    if status >= 400:
        detail = response_body.decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord backup listing failed ({status}): {detail}")
    messages = json.loads(response_body.decode("utf-8"))
    if not isinstance(messages, list):
        return []
    return messages


def _download_url(url: str) -> bytes:
    request = urlrequest.Request(url, headers={"User-Agent": "VirelloScannerBackup/1.0"})
    with urlrequest.urlopen(request, timeout=120) as response:
        return response.read()


def _attachment_from_message(message: dict) -> dict | None:
    attachments = message.get("attachments") or []
    for attachment in attachments:
        filename = attachment.get("filename", "")
        if filename.startswith(BACKUP_FILENAME_PREFIX):
            return attachment
    return None


def _parse_backup_timestamp(message: dict, attachment: dict) -> datetime | None:
    filename = attachment.get("filename", "")
    if filename.startswith(BACKUP_FILENAME_PREFIX):
        raw = filename.removeprefix(BACKUP_FILENAME_PREFIX).removesuffix(".json.gz")
        try:
            if raw.endswith("Z"):
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    timestamp = message.get("timestamp")
    if isinstance(timestamp, str):
        try:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def find_latest_backup_message() -> tuple[dict, dict] | None:
    messages = _discord_list_backup_messages()
    latest: tuple[datetime, dict, dict] | None = None
    for message in messages:
        attachment = _attachment_from_message(message)
        if attachment is None:
            continue
        created_at = _parse_backup_timestamp(message, attachment)
        if created_at is None:
            continue
        if latest is None or created_at > latest[0]:
            latest = (created_at, message, attachment)
    if latest is None:
        return None
    return latest[1], latest[2]


def get_last_backup_at() -> str | None:
    global _last_backup_at
    if _last_backup_at:
        return _last_backup_at
    stored = _meta_get("last_backup_at")
    if stored:
        _last_backup_at = stored
        return stored
    if not backup_is_configured():
        return None
    try:
        latest = find_latest_backup_message()
    except (RuntimeError, urlerror.URLError, json.JSONDecodeError):
        return None
    if latest is None:
        return None
    message, _attachment = latest
    timestamp = message.get("timestamp")
    if isinstance(timestamp, str):
        _last_backup_at = timestamp
        return timestamp
    return None


def get_last_restore_at() -> str | None:
    return _last_restore_at or _meta_get("last_restore_at")


def backup_is_due() -> bool:
    last_backup_at = get_last_backup_at()
    if not last_backup_at:
        return True
    try:
        previous = datetime.fromisoformat(last_backup_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    return _utc_now() - previous >= timedelta(days=BACKUP_INTERVAL_DAYS)


def create_and_upload_backup() -> dict:
    if not backup_is_configured():
        raise RuntimeError("Discord backup is not configured.")
    with _backup_lock:
        payload = export_database()
        exported_at = payload["exported_at"]
        filename = _backup_filename(exported_at)
        content = serialize_backup(payload)
        message = _discord_upload_backup(filename, content, exported_at)
        global _last_backup_at
        _last_backup_at = exported_at
        _meta_set("last_backup_at", exported_at)
        print(f"Database backup uploaded to Discord ({filename}, {len(content)} bytes).", flush=True)
        return message


def download_latest_backup() -> dict | None:
    latest = find_latest_backup_message()
    if latest is None:
        return None
    _message, attachment = latest
    url = attachment.get("url")
    if not url:
        return None
    content = _download_url(url)
    return deserialize_backup(content)


def maybe_restore_from_backup() -> bool:
    global _last_restore_at
    if not backup_auto_restore_enabled() or not backup_is_configured():
        return False
    if database_has_data():
        return False
    try:
        backup = download_latest_backup()
    except (RuntimeError, urlerror.URLError, json.JSONDecodeError, ValueError) as error:
        print(f"Backup restore skipped: could not download backup ({error!r}).", flush=True)
        return False
    if backup is None:
        print("Backup restore skipped: no backup found in Discord channel.", flush=True)
        return False
    try:
        restore_database(backup)
    except (RuntimeError, ValueError) as error:
        print(f"Backup restore failed: {error!r}", flush=True)
        return False
    restored_at = _to_iso(_utc_now())
    _last_restore_at = restored_at
    _meta_set("last_restore_at", restored_at)
    exported_at = backup.get("exported_at", "unknown")
    print(f"Database restored from Discord backup exported at {exported_at}.", flush=True)
    return True


def maybe_run_scheduled_backup() -> bool:
    if not backup_enabled() or not backup_is_configured():
        return False
    if not backup_is_due():
        return False
    try:
        create_and_upload_backup()
    except (RuntimeError, urlerror.URLError, json.JSONDecodeError, ValueError) as error:
        print(f"Scheduled backup failed: {error!r}", flush=True)
        return False
    return True


def _scheduler_loop() -> None:
    while True:
        try:
            maybe_run_scheduled_backup()
        except Exception as error:
            print(f"Backup scheduler error: {error!r}", flush=True)
        time.sleep(SCHEDULER_CHECK_SECONDS)


def start_backup_scheduler() -> None:
    global _scheduler_started
    if _scheduler_started or not backup_enabled() or not backup_is_configured():
        return
    _scheduler_started = True
    thread = threading.Thread(target=_scheduler_loop, name="backup-scheduler", daemon=True)
    thread.start()
    print(
        f"Backup scheduler started (every {BACKUP_INTERVAL_DAYS} days, "
        f"checked every {SCHEDULER_CHECK_SECONDS // 3600 or 1} hour(s)).",
        flush=True,
    )


def check_database_connection() -> bool:
    try:
        with _connect() as conn:
            _db_execute(conn, "SELECT 1").fetchone()
        return True
    except Exception:
        return False


def get_health_status() -> tuple[int, dict]:
    database_connected = check_database_connection()
    status_code = 200 if database_connected else 503
    payload = {
        "status": "ok" if database_connected else "degraded",
        "service": "virello-scanner-backend",
        "timestamp": _to_iso(_utc_now()),
        "database": {
            "connected": database_connected,
            "engine": "postgresql" if _using_postgres() else "sqlite",
            "has_data": database_has_data() if database_connected else False,
        },
        "backup": {
            "enabled": backup_enabled(),
            "configured": backup_is_configured(),
            "auto_restore_enabled": backup_auto_restore_enabled(),
            "interval_days": BACKUP_INTERVAL_DAYS,
            "last_backup_at": get_last_backup_at(),
            "last_restore_at": get_last_restore_at(),
        },
    }
    return status_code, payload


def initialize_backup_system() -> None:
    init_backup_meta()
    if maybe_restore_from_backup():
        get_last_backup_at()
    if backup_enabled() and backup_is_configured():
        if backup_is_due() and database_has_data():
            maybe_run_scheduled_backup()
    start_backup_scheduler()
