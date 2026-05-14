from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .lnk_utils import lnk_targets


def _stat_dict(path: Path) -> dict[str, Any] | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return {
        "path": str(path),
        "name": path.name,
        "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
        "size_bytes": st.st_size,
    }


def collect_saved_files_viewer(
    max_lnk: int = 80,
    max_downloads: int = 60,
    max_extra_dirs: int = 40,
) -> dict[str, Any]:
    if os.name != "nt":
        return {"available": False, "reason": "non_windows", "records": []}
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_record(src: str, path: Path, extra: dict[str, Any] | None = None) -> None:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            return
        seen.add(key)
        st = _stat_dict(path) if path.is_file() else None
        rec: dict[str, Any] = {"artifact": src, "path": str(path)}
        if st:
            rec.update(st)
        if extra:
            rec.update(extra)
        records.append(rec)

    appdata = os.getenv("APPDATA")
    localappdata = os.getenv("LOCALAPPDATA")
    userprofile = os.getenv("USERPROFILE")

    recent_dir = Path(appdata) / "Microsoft" / "Windows" / "Recent" if appdata else None
    if recent_dir and recent_dir.is_dir():
        count = 0
        for p in sorted(recent_dir.glob("*.lnk"), key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True):
            if count >= max_lnk:
                break
            targets = lnk_targets(p)
            add_record(
                "explorer_recent_lnk",
                p,
                {"lnk_targets": targets, "is_download_context": any("Downloads" in t for t in targets)},
            )
            count += 1

    if userprofile:
        for sub in ("Downloads", "Desktop"):
            d = Path(userprofile) / sub
            if not d.is_dir():
                continue
            try:
                files = sorted(d.iterdir(), key=lambda x: x.stat().st_mtime if x.is_file() else 0, reverse=True)
            except OSError:
                continue
            for p in files:
                if not p.is_file():
                    continue
                if p.suffix.lower() in {".exe", ".dll", ".msi", ".zip", ".rar", ".7z"}:
                    add_record(f"user_{sub.lower()}", p)
                if len([r for r in records if r.get("artifact", "").startswith(f"user_{sub.lower()}")]) >= max_downloads:
                    break

    extra_roots: list[Path] = []
    if localappdata:
        extra_roots.extend(
            [
                Path(localappdata) / "Discord",
                Path(localappdata) / "Temp",
            ]
        )
    if userprofile:
        extra_roots.append(Path(userprofile) / "Downloads")

    for root in extra_roots:
        if not root.is_dir():
            continue
        label = "discord_related_path" if "discord" in str(root).lower() else "temp_extraction_or_drop"
        n = 0
        try:
            for p in root.rglob("*"):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in {".exe", ".zip", ".rar", ".7z"}:
                    continue
                add_record(label, p)
                n += 1
                if n >= max_extra_dirs:
                    break
        except OSError:
            continue

    jumplist_auto = Path(appdata) / "Microsoft" / "Windows" / "Recent" / "AutomaticDestinations" if appdata else None
    if jumplist_auto and jumplist_auto.is_dir():
        for p in sorted(jumplist_auto.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:25]:
            if p.is_file():
                add_record("jumplist_automatic_destinations", p, {"note": "binary_jump_list_container"})

    return {"available": True, "records": records[:200], "count": len(records[:200])}
