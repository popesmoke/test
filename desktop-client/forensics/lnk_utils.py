from __future__ import annotations

import re
from pathlib import Path


def extract_paths_from_lnk_blob(data: bytes) -> list[str]:
    """Heuristic path extraction from shell link files without pywin32."""
    found: list[str] = []
    # UTF-16-LE sequences that look like Windows paths
    try:
        u = data.decode("utf-16-le", errors="ignore")
    except Exception:
        u = ""
    for m in re.finditer(r"[A-Za-z]:\\(?:[^<>:\"|?*\\\x00-\x1f]+\\)*[^<>:\"|?*\\\x00-\x1f]{1,240}", u):
        s = m.group(0).strip("\x00").strip()
        if len(s) > 4 and s not in found:
            found.append(s)
    # ASCII fallback
    for m in re.finditer(rb"([A-Za-z]:\\[^\x00\r\n\t]{4,240})", data):
        try:
            s = m.group(1).decode("ascii", errors="ignore")
        except Exception:
            continue
        if s not in found:
            found.append(s)
    return found[:12]


def lnk_targets(path: Path) -> list[str]:
    try:
        data = path.read_bytes()
    except OSError:
        return []
    return extract_paths_from_lnk_blob(data)
