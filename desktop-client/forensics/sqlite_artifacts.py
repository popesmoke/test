from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

CHEAT_SQLITE_KEYWORDS = re.compile(
    r"(?i)(inject|executor|bypass|internal|external|cheat|loader|exploit|"
    r"kernel\s*driver|dma|hypervisor|roblox|synapse|xeno|delta|krnl|"
    r"script\s*ware|potassium|seliware|solara|macsploit)",
)

EXECUTABLE_PATH_IN_TEXT = re.compile(r"[A-Za-z]:\\[^\x00\"'|<>]{6,260}\.(?:exe|dll|bat|cmd|ps1)", re.I)


def _safe_connect_ro(path: Path) -> sqlite3.Connection | None:
    try:
        uri = "file:" + quote(str(path.resolve()), safe="/\\:") + "?mode=ro"
        return sqlite3.connect(uri, uri=True, timeout=0.3)
    except sqlite3.Error:
        return None


def _wal_sidecar_status(path: Path) -> dict[str, Any]:
    wal = path.parent / (path.name + "-wal")
    shm = path.parent / (path.name + "-shm")
    out: dict[str, Any] = {"wal_present": wal.exists(), "shm_present": shm.exists()}
    try:
        if wal.exists():
            out["wal_size_bytes"] = wal.stat().st_size
    except OSError:
        pass
    return out


def _query_chrome_style_history(conn: sqlite3.Connection, limit: int = 40) -> tuple[list[dict], list[dict]]:
    urls: list[dict] = []
    downloads: list[dict] = []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT ?",
            (limit,),
        )
        for row in cur.fetchall():
            urls.append({"url": row[0], "title": row[1], "last_visit_time": row[2]})
    except sqlite3.Error:
        pass
    cur = conn.cursor()
    for sql in (
        "SELECT target_path, end_time FROM downloads ORDER BY end_time DESC LIMIT ?",
        "SELECT current_path, start_time FROM downloads ORDER BY start_time DESC LIMIT ?",
    ):
        try:
            cur.execute(sql, (limit,))
            for row in cur.fetchall():
                downloads.append({"path": row[0], "time": row[1], "query": sql[:60]})
            if downloads:
                break
        except sqlite3.Error:
            continue
    return urls, downloads


def collect_browser_sqlite_signals() -> dict[str, Any]:
    if os.name != "nt":
        return {"available": False, "reason": "non_windows", "hits": []}
    local = os.getenv("LOCALAPPDATA")
    if not local:
        return {"available": False, "reason": "no_localappdata", "hits": []}
    roots = [
        Path(local) / "Google" / "Chrome" / "User Data",
        Path(local) / "Microsoft" / "Edge" / "User Data",
        Path(local) / "BraveSoftware" / "Brave-Browser" / "User Data",
    ]
    hits: list[dict[str, Any]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for profile_dir in [root / "Default", root / "Profile 1"]:
            db = profile_dir / "History"
            if not db.is_file():
                continue
            side = _wal_sidecar_status(db)
            conn = _safe_connect_ro(db)
            if not conn:
                hits.append(
                    {
                        "browser_data_root": str(root),
                        "database": str(db),
                        "status": "open_failed",
                        "wal": side,
                    }
                )
                continue
            try:
                urls, downloads = _query_chrome_style_history(conn, limit=35)
            finally:
                conn.close()
            suspicious_urls = [u for u in urls if u.get("url") and CHEAT_SQLITE_KEYWORDS.search(str(u["url"]))]
            suspicious_dls = [d for d in downloads if d.get("path") and CHEAT_SQLITE_KEYWORDS.search(str(d["path"]))]
            exe_refs: list[str] = []
            for u in urls[:20]:
                if u.get("url"):
                    exe_refs.extend(EXECUTABLE_PATH_IN_TEXT.findall(str(u["url"])))
            hits.append(
                {
                    "browser_data_root": str(root),
                    "database": str(db),
                    "status": "ok",
                    "wal": side,
                    "recent_download_paths": [d.get("path") for d in downloads[:25] if d.get("path")],
                    "suspicious_url_hits": suspicious_urls[:20],
                    "suspicious_download_hits": suspicious_dls[:20],
                    "executable_paths_in_urls_sample": list(dict.fromkeys(exe_refs))[:30],
                }
            )
            if len(hits) >= 6:
                break
        if len(hits) >= 6:
            break
    return {"available": True, "hits": hits}


def collect_activity_cache_paths() -> dict[str, Any]:
    """Best-effort ActivityCache.db path listing (Windows 11 timeline DB)."""
    if os.name != "nt":
        return {"available": False, "paths": []}
    local = os.getenv("LOCALAPPDATA")
    if not local:
        return {"available": False, "paths": []}
    base = Path(local) / "ConnectedDevicesPlatform"
    dbs: list[dict[str, Any]] = []
    if base.is_dir():
        try:
            for p in base.rglob("ActivitiesCache.db"):
                try:
                    st = p.stat()
                    dbs.append(
                        {
                            "path": str(p),
                            "modified": st.st_mtime,
                            "wal": _wal_sidecar_status(p),
                        }
                    )
                except OSError:
                    continue
                if len(dbs) >= 4:
                    break
        except OSError:
            pass
    return {"available": True, "databases": dbs[:4]}


def probe_activity_cache_executables() -> list[str]:
    paths_out: list[str] = []
    info = collect_activity_cache_paths()
    for row in info.get("databases") or []:
        p = Path(row["path"])
        conn = _safe_connect_ro(p)
        if not conn:
            continue
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            for t in tables:
                if "Activity" not in t or not re.fullmatch(r"^[A-Za-z0-9_]+$", t):
                    continue
                try:
                    cur.execute(f"PRAGMA table_info({t})")
                    cols = [r[1] for r in cur.fetchall() if re.fullmatch(r"^[A-Za-z0-9_]+$", r[1])]
                    blob_cols = [c for c in cols if "payload" in c.lower() or "app" in c.lower() or "content" in c.lower()]
                    qcols = [c for c in cols if c.lower() in {"executable", "application", "appid", "activitytype"}]
                    sel = (qcols + blob_cols)[:6] or cols[:4]
                    if not sel:
                        continue
                    cur.execute(f"SELECT {','.join(sel)} FROM {t} ORDER BY rowid DESC LIMIT 40")
                    for r in cur.fetchall():
                        for cell in r:
                            if isinstance(cell, str):
                                paths_out.extend(EXECUTABLE_PATH_IN_TEXT.findall(cell))
                            elif isinstance(cell, (bytes, bytearray)):
                                try:
                                    text = bytes(cell).decode("utf-16-le", errors="ignore")
                                except Exception:
                                    text = str(cell)
                                paths_out.extend(EXECUTABLE_PATH_IN_TEXT.findall(text))
                except sqlite3.Error:
                    continue
        finally:
            conn.close()
    return list(dict.fromkeys(paths_out))[:40]
