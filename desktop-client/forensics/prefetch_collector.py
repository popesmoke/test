from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def prefetch_exe_name_from_filename(pf_name: str) -> str | None:
    m = re.match(r"^(.+)-[0-9A-F]{8}\.pf\Z", pf_name, re.I)
    if not m:
        return None
    return m.group(1).upper()


def collect_prefetch_records(max_files: int = 100) -> dict[str, Any]:
    if os.name != "nt":
        return {"available": False, "reason": "non_windows", "items": []}
    folder = Path(os.getenv("SystemRoot", "C:\\Windows")) / "Prefetch"
    if not folder.is_dir():
        return {"available": False, "reason": "no_prefetch_dir", "items": []}
    items: list[dict[str, Any]] = []
    try:
        files = sorted(folder.glob("*.pf"), key=lambda p: p.stat().st_mtime, reverse=True)[:max_files]
    except OSError as exc:
        return {"available": False, "reason": str(exc), "items": []}
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        exe = prefetch_exe_name_from_filename(path.name)
        items.append(
            {
                "prefetch_file": str(path),
                "name": path.name,
                "executable_guess": exe,
                "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "size_bytes": stat.st_size,
            }
        )
    return {"available": True, "folder": str(folder), "items": items, "count": len(items)}
