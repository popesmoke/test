from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Callable

RunCommand = Callable[..., str]

_USN_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$lines = New-Object System.Collections.Generic.List[string]
foreach ($disk in Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3') {
  $d = $disk.DeviceID
  if (-not $d) { continue }
  try {
    fsutil usn readjournal $d csv 2>$null | Select-Object -First 220 | ForEach-Object {
      [void]$lines.Add(($d + '|' + $_.Line))
    }
  } catch {}
}
$lines | ConvertTo-Json -Compress
"""


def _parse_usn_line(prefixed: str) -> dict[str, Any] | None:
    if "|" not in prefixed:
        return None
    vol, line = prefixed.split("|", 1)
    line = line.strip()
    if not line:
        return None
    parts = line.split(",")
    if len(parts) < 8:
        return None
    reason_raw = parts[6].strip()
    name = ",".join(parts[7:]).strip()
    ts_raw = parts[5].strip()
    ts_iso: str | None = None
    for fmt in ("%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            dt = datetime.strptime(ts_raw, fmt).replace(tzinfo=timezone.utc)
            ts_iso = dt.isoformat()
            break
        except ValueError:
            continue
    reason_int = 0
    try:
        reason_int = int(reason_raw, 16)
    except ValueError:
        pass
    flags: list[str] = []
    if reason_int & 0x80000000:
        flags.append("USN_REASON_CLOSE")
    if reason_int & 0x00000100:
        flags.append("FILE_CREATE")
    if reason_int & 0x00000200:
        flags.append("FILE_DELETE")
    if reason_int & 0x00001000:
        flags.append("FILE_RENAME_OLD_NAME")
    if reason_int & 0x00002000:
        flags.append("FILE_RENAME_NEW_NAME")
    if reason_int & 0x00080000:
        flags.append("DATA_OVERWRITE")
    if reason_int & 0x00200000:
        flags.append("BASIC_INFO_CHANGE")
    if reason_int & 0x00000004:
        flags.append("STREAM_CHANGE")
    if re.match(r"^[A-Za-z]:\\", name) and name.count(":") >= 2:
        flags.append("alternate_data_stream_in_path")

    return {
        "volume": vol.strip(),
        "file_reference": parts[2].strip(),
        "parent_reference": parts[3].strip(),
        "usn": parts[4].strip(),
        "timestamp_raw": ts_raw,
        "timestamp_iso": ts_iso,
        "reason_int": reason_int,
        "reason_flags": flags,
        "name": name,
        "is_executable_name": bool(re.search(r"\.(exe|dll|sys|scr|com|bat|cmd|ps1|vbs|js)\Z", name, re.I)),
    }


def collect_usn_journal_sample(run_command: RunCommand) -> dict[str, Any]:
    raw = run_command(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _USN_SCRIPT],
        timeout=35,
        max_chars=200_000,
    )
    if raw.startswith("Unavailable:"):
        return {"available": False, "error": raw, "events": []}
    try:
        lines = json.loads(raw)
    except Exception:
        return {"available": True, "parse_error": True, "events": [], "raw_head": raw[:1500]}
    if not isinstance(lines, list):
        lines = [lines]
    events: list[dict[str, Any]] = []
    for item in lines:
        if not isinstance(item, str):
            continue
        parsed = _parse_usn_line(item)
        if parsed:
            events.append(parsed)
    return {"available": True, "events": events, "count": len(events)}
